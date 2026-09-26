#!/usr/bin/env python3
"""Pinned official SIS estimates for the CF-dagger v2 Profile I node registry.

Run under Sage Python. Upstream is imported without modifications. No protocol
benchmark, frozen-run reuse, parameter search, or rank adjustment is performed.
"""
import argparse
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:
    resource = None
import subprocess
import sys
import time
import traceback

PIN = "53da5982597709ba0fdf94ea37a84d822310fd84"
HERE = Path(os.environ.get("CFDAGGER_RUN_DIR", Path(__file__).resolve().parents[1] / "build"))
UPSTREAM = Path(os.environ.get("CFDAGGER_ESTIMATOR_PATH", Path(__file__).resolve().parents[1] / "vendor" / "lattice-estimator"))

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))

def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + str(UPSTREAM), "-c", "core.filemode=false", "-c", "core.autocrlf=true", "-C", str(UPSTREAM), *args], text=True).strip()

def candidate_inputs():
    return json.loads((HERE / "backend_inputs.json").read_text(encoding="utf-8"))

FRONTEND_IDS = ("frontend_state", "frontend_carrier", "frontend_auxiliary")

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_exclusive(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(data)

def normalize_input(actual, role_id=None):
    assert actual["estimator_commit"] == PIN, "Stale estimator commit"
    assert actual["status"] == "READY", "Compiler input not ready"
    assert actual["norm_model"] == "coefficient_l2", "Only coefficient_l2 is supported here"
    for field in ("q", "d", "rows", "columns", "beta"):
        assert isinstance(actual[field], int) and actual[field] > 0, (actual["matrix_id"], field)
    expected = {"n": actual["d"]*actual["rows"], "m": actual["d"]*actual["columns"], "norm": 2, "length_bound": actual["beta"]}
    assert actual["expanded_sis"] == expected, "Inconsistent coefficient expansion"
    return {"role_id": role_id or actual["matrix_id"], "matrix_id": actual["matrix_id"],
            "q": actual["q"], "ring_degree": actual["d"], "rows": actual["rows"], "columns": actual["columns"],
            "coefficient_rows_n": expected["n"], "coefficient_columns_m": expected["m"],
            "norm": "coefficient_l2", "beta": actual["beta"]}

def collect_inputs():
    """Validate preserved backend config; discover only the three registered front matrices."""
    config = read_json(HERE / "candidate_backend_inputs.json")
    assert config == candidate_inputs(), "Stale backend candidate config; do not overwrite existing evidence"
    jobs, front = [], []
    for index, role in enumerate(config["roles"]):
        path = HERE / "estimator_inputs" / (role["matrix_id"] + ".json")
        actual = read_json(path)
        assert normalize_input(actual, role["role_id"]) == role, (role["matrix_id"], "stale backend parameters")
        jobs.append({"role": role, "prefix": f"{index:02d}_{role['role_id'].replace('/', '_')}", "input_path": path})
    for matrix_id in FRONTEND_IDS:
        path = HERE / "estimator_inputs" / (matrix_id + ".json")
        actual = read_json(path) if path.exists() else {"status": "INPUT_FILE_NOT_PRESENT"}
        assert actual.get("matrix_id", matrix_id) == matrix_id
        item = {"matrix_id": matrix_id, "input_status": actual["status"]}
        if actual["status"] == "READY":
            compiler = read_json(HERE / "compiler_manifest.json")
            registry = read_json(HERE / "node_registry.json")
            assert compiler["status"] == "COMPLETE", "READY frontend input requires a COMPLETE compiler manifest"
            assert registry["numerical_instantiation_complete"] is True
            assert registry["independent_matrix_count"] == 20
            registered = next(r for r in registry["roles"] if r["matrix_id"] == matrix_id)
            for field in ("q", "d", "rows", "columns", "norm_model"):
                assert actual[field] == registered[field], (matrix_id, "registry/input mismatch", field)
            assert actual["beta"] == registered["kernel_radius_beta"]
            role = normalize_input(actual)
            jobs.append({"role": role, "prefix": matrix_id, "input_path": path})
            item["status"] = "READY_NOT_ESTIMATED"
        else:
            assert not list((HERE / "estimator_raw").glob(matrix_id + "_*.json")), "Recorded frontend estimates exist but compiler input became unresolved"
            item["status"] = actual["status"]
            item["estimates"] = None
            item["reason"] = "Actual compiler dimensions are unavailable; no capacity is substituted."
        front.append(item)
    return jobs, front

def raw_attempts(job, model):
    prefix = job["prefix"] + "_" + model
    base = HERE / "estimator_raw" / (prefix + ".json")
    paths = ([base] if base.exists() else []) + sorted((HERE / "estimator_raw").glob(prefix + ".attempt*.json"))
    records = []
    for path in paths:
        record = read_json(path)
        assert record["role"] == job["role"], (job["role"]["matrix_id"], "stale raw parameters")
        assert record["model"] == model and record["estimator_commit"] == PIN, "Stale raw model/commit"
        if "generated_input_sha256" in record:
            assert record["generated_input_sha256"] == hashlib.sha256(job["input_path"].read_bytes()).hexdigest(), "Generated input bytes changed after this estimator record"
        records.append((path, record))
    return records

def selected_attempt(job, model):
    attempts = raw_attempts(job, model)
    finite = [(p,r) for p,r in attempts if r["status"] == "DONE_FINITE"]
    return finite[0] if finite else (attempts[-1] if attempts else (None, {"role": job["role"], "model": model, "status": "NOT_RUN"}))

def next_output(job, model, resume):
    attempts = raw_attempts(job, model)
    if attempts and not resume:
        raise FileExistsError("Existing raw evidence; use --resume. Nothing was overwritten.")
    if any(r["status"] == "DONE_FINITE" for _,r in attempts):
        return None
    prefix = job["prefix"] + "_" + model
    if not attempts:
        return HERE / "estimator_raw" / (prefix + ".json")
    number = 1
    while (HERE / "estimator_raw" / f"{prefix}.attempt{number:03d}.json").exists():
        number += 1
    return HERE / "estimator_raw" / f"{prefix}.attempt{number:03d}.json"

def run_job(job, model_name, resume=False):
    role = job["role"]
    dest = next_output(job, model_name, resume)
    if dest is None:
        print(json.dumps({"matrix_id": role["matrix_id"], "model": model_name, "status": "SKIPPED_MATCHING_FINITE"}), flush=True)
        return selected_attempt(job, model_name)[1]
    result = {"role": role, "model": model_name, "estimator_commit": PIN,
              "estimator_api": "SIS.estimate", "norm": 2,
              "scope": "Generic coefficient-expanded q-ary SIS lattice attack heuristic; module-specific attacks and complete computational reduction not certified.",
              "memory": None, "success_probability": None,
              "unreported_metrics_reason": "Official Euclidean SIS branch does not report memory or success probability; neither is inferred from infinity-norm mode."}
    started = time.perf_counter()
    cpu_start = time.process_time()
    captured = io.StringIO()
    try:
        assert git("rev-parse", "HEAD") == PIN
        assert not git("status", "--porcelain"), "Estimator upstream has modifications"
        sys.path.insert(0, str(UPSTREAM))
        from sage.all import ZZ, RR, log, oo
        from estimator import SIS
        from estimator.reduction import MATZOV
        model = MATZOV(nn=model_name)
        params = SIS.Parameters(n=ZZ(role["coefficient_rows_n"]), q=ZZ(role["q"]),
                                m=ZZ(role["coefficient_columns_m"]), length_bound=ZZ(role["beta"]),
                                norm=2, tag=role["matrix_id"])
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            costs = SIS.estimate(params, red_cost_model=model, jobs=1, catch_exceptions=False, quiet=True)
        attacks = []
        for attack, cost in costs.items():
            finite = "rop" in cost and cost["rop"] != oo and math.isfinite(float(log(cost["rop"], 2)))
            attacks.append({"attack": attack, "raw_repr": repr(cost),
                            "raw_fields": {str(k): str(v) for k, v in cost.items()},
                            "status": "DONE_FINITE" if finite else "UNKNOWN_NONFINITE",
                            "rop": str(cost.get("rop")),
                            "log2_rop": float(log(cost["rop"], 2)) if finite else None,
                            "blocksize": int(cost["beta"]) if finite else None,
                            "attack_lattice_dimension": int(cost["d"]) if finite else None,
                            "delta": str(cost.get("delta"))})
        result["attacks"] = attacks
        finite_attacks = [a for a in attacks if a["status"] == "DONE_FINITE"]
        result["status"] = "DONE_FINITE" if len(finite_attacks) == len(attacks) and attacks else "UNKNOWN_NONFINITE_OR_EMPTY"
        result["lowest_reported_attack"] = min(finite_attacks, key=lambda a: a["log2_rop"]) if finite_attacks else None
        result["screening_vs_128"] = ("BELOW_TARGET" if result["lowest_reported_attack"]["log2_rop"] < 128 else "NO_BELOW_TARGET_COST_IN_THIS_MODEL") if finite_attacks else "UNKNOWN"
        result["large_norm_attack_applicable"] = role["beta"] > role["q"]
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
    result["wall_seconds"] = time.perf_counter() - started
    result["cpu_seconds"] = time.process_time() - cpu_start
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result["stdout_stderr"] = captured.getvalue()
    result["generated_input_sha256"] = hashlib.sha256(job["input_path"].read_bytes()).hexdigest()
    write_exclusive(dest, result)
    print(json.dumps({"file": dest.name, "status": result["status"], "log2_rop": (result.get("lowest_reported_attack") or {}).get("log2_rop")}), flush=True)
    return result

def summarize():
    jobs, front_records = collect_inputs()
    roles = [job["role"] for job in jobs]
    registry_agreement = []
    for job in jobs:
        registry_agreement.append({"matrix_id": job["role"]["matrix_id"], "status": "MATCH", "input_sha256": hashlib.sha256(job["input_path"].read_bytes()).hexdigest()})
    records = []
    raw_input_checks = []
    for job in jobs:
        role = job["role"]
        for model in ("classical", "quantum"):
            path, record = selected_attempt(job, model)
            records.append(record)
            for attempt_path, attempt in raw_attempts(job, model):
                raw_input_checks.append({"matrix_id": role["matrix_id"], "model": model,
                                         "raw_path": "estimator_raw/" + attempt_path.name,
                                         "raw_sha256": hashlib.sha256(attempt_path.read_bytes()).hexdigest(),
                                         "status": "MATCH"})
    for frontend in front_records:
        if frontend["input_status"] == "READY":
            selected = [r for r in records if r["role"]["matrix_id"] == frontend["matrix_id"]]
            frontend["estimates"] = selected
            frontend["status"] = "DONE_FINITE" if len(selected)==2 and all(r["status"]=="DONE_FINITE" for r in selected) else "READY_ESTIMATION_PENDING"
    unresolved_fronts = [f["matrix_id"] for f in front_records if f["input_status"] != "READY"]
    front_status = ("UNRESOLVED_COMPILER_DIMENSIONS" if unresolved_fronts else ("DONE_FINITE" if all(f["status"]=="DONE_FINITE" for f in front_records) else "READY_ESTIMATION_PENDING"))
    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
        attack = record.get("lowest_reported_attack") or {}
        record["MATZOV_fit_extrapolation_beyond_beta_1024"] = (attack.get("blocksize", 0) > 1024) if attack else None
        record["documented_range_status"] = ("EXTRAPOLATED_ABOVE_1024" if attack["blocksize"] > 1024 else "WITHIN_DOCUMENTED_FIT_RANGE") if attack else "NO_FINITE_ESTIMATE"
    def weakest_for(selected):
        result = {}
        for model in ("classical", "quantum"):
            finite = [r for r in selected if r["model"] == model and r["status"] == "DONE_FINITE"]
            weak = min(finite, key=lambda r:r["lowest_reported_attack"]["log2_rop"]) if finite else None
            result[model] = ({"matrix_id": weak["role"]["matrix_id"], "role_id": weak["role"]["role_id"], **weak["lowest_reported_attack"]} if weak else None)
        return result
    backend_records = [r for r in records if r["role"]["matrix_id"].startswith("backend_")]
    weakest = weakest_for(backend_records)
    env_path = HERE / "estimator_environment.json"
    environment = json.loads(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}
    write_json(HERE / "estimator_input_checks.json", {
        "status": "PASS" if all(x["status"]=="MATCH" for x in raw_input_checks) else "UNRESOLVED",
        "check_scope": "Exact input identity only; not a cryptographic security certificate.",
        "independent_backend_matrices": len(backend_records)//2, "ready_frontend_matrices": len(roles)-len(backend_records)//2, "raw_records_checked": len(raw_input_checks),
        "checked_fields": ["matrix_id", "q", "d", "rows", "columns", "norm_model", "beta", "expanded_sis.n", "expanded_sis.m", "expanded_sis.norm", "expanded_sis.length_bound"],
        "registry_inputs": registry_agreement, "raw_results": raw_input_checks,
        "frontend_matrix_count": len(FRONTEND_IDS), "frontend_status": front_status})
    all_done = not unresolved_fronts and all(r["status"]=="DONE_FINITE" for r in records)
    backend_done = all(r["status"]=="DONE_FINITE" for r in backend_records)
    overall = "ALL_REGISTERED_MATRICES_ESTIMATED" if all_done else ("BACKEND_ESTIMATED_FRONTEND_UNRESOLVED" if backend_done and unresolved_fronts else "ESTIMATION_PARTIAL")
    obj = {"status": overall, "profile": "Profile I", "k": 16,
           "estimator_commit": PIN, "upstream_unmodified_at_execution": environment.get("upstream_clean"),
           "backend_matrix_count": 17, "independent_matrix_count": 20, "ready_matrix_count": len(roles), "cost_model_count_per_matrix": 2,
           "generated_registry_input_agreement": registry_agreement,
           "task_counts": counts, "weakest_among_completed_backend_outputs": weakest,
           "weakest_among_all_completed_outputs": weakest_for(records),
           "weakest_full_node": weakest_for(records) if all_done else None,
           "weakest_full_node_status": "ALL_20_MATRICES_FINITE" if all_done else "NOT_ESTABLISHED",
           "frontend_status": front_status,
           "unresolved_frontend_matrix_ids": unresolved_fronts,
           "frontend_records": front_records,
           "best_known_attack_cost_scope": "Minimum among attacks returned by this pinned official estimator under each declared MATZOV model; not an exhaustive claim about all Module-SIS attacks.",
           "security_estimate_scope": "Heuristic generic lattice attack log2 work estimate, not proven security bits or end-to-end node certification.",
           "models": {"classical": "MATZOV(nn=classical): list_decoding-classical", "quantum": "MATZOV(nn=quantum): list_decoding-dw (depth-times-width convention)"},
           "model_calibration_warning": "Pinned reduction.py states MATZOV fitted data cover block size up to 1024. Results above 1024 are finite official-model extrapolations, explicitly flagged; not a calibrated cryptanalytic guarantee.",
           "coefficient_expansion": "n=d*rows; m=d*columns; length_bound=beta; norm=2; no l_infinity conversion",
           "estimator_branch_note": "Pinned official SIS.estimate selects attacks using actual radius. Euclidean shape formula belongs to official estimator and is not replaced by a custom design proxy.",
           "records": records}
    write_json(HERE / "estimator_results.json", obj)
    rows = ["# Official lattice-estimator results: CF† v2 Profile I, k=16", "", f"Selected task counts: `{counts}`. Front-end status: `{front_status}`.", "",
            f"Pinned upstream commit: `{PIN}`. No upstream or protocol parameter modifications.", "",
            "The two cost models are official `MATZOV(nn='classical')` and `MATZOV(nn='quantum')`; the latter uses the depth-times-width nearest-neighbor convention. Coefficient expansion is `n=64*rows`, `m=64*columns`, coefficient l2 bound `beta`. All runs use `SIS.estimate`, not its rough interface.", "",
            "These are generic q-ary lattice attack estimates on coefficient-expanded Module-SIS dimensions. The estimator does not certify module-specific attack coverage or the full reduction advantage. The reported minimum is among the attacks implemented and returned at this commit. Values below are log2(rop), not a security proof.", "",
            "| Matrix | Rows | Columns | Coefficient l2 radius | Coefficient SIS (n,m) | Classical log2(rop) | Quantum log2(rop) | BKZ block size | Fit range |", "|---|---:|---:|---:|---|---:|---:|---:|---|"]
    for index, role in enumerate(roles):
        pair = records[2*index:2*index+2]
        vals = [f"{r['lowest_reported_attack']['log2_rop']:.6f}" if r.get("status")=="DONE_FINITE" else r["status"] for r in pair]
        block = (pair[0].get("lowest_reported_attack") or {}).get("blocksize", "UNKNOWN")
        fit = pair[0]["documented_range_status"]
        rows.append(f"| {role['matrix_id']} | {role['rows']} | {role['columns']} | {role['beta']} | ({role['coefficient_rows_n']}, {role['coefficient_columns_m']}) | {vals[0]} | {vals[1]} | {block} | {fit} |")
    rows += ["", "Memory and attack success probability are **not reported** by the official Euclidean SIS branch. They are stored as null with an explicit reason; no infinity-norm success probability or proxy memory estimate is substituted.", "",
             "The MATZOV source states that its fitted data cover block size up to 1024. Outputs using larger block sizes are **model extrapolations**, marked in JSON. Finite output alone is not a calibrated security certificate.", "",
             "The front-end independent matrices `A_st`, `A_H`, and `A_aux` are evaluated only after their generated inputs become READY. Current readiness and results are in the JSON frontend_records. The shared state matrix is counted once. Unresolved matrices cannot be covered by the backend minimum.", "",
             "Raw results, errors, stdout/stderr, model configuration, wall/CPU time, and process peak RSS are in `estimator_raw/`. Time/RSS here measure estimator execution only, never protocol performance.", ""]
    for model, weak in weakest.items():
        rows.append(f"Weakest {model} **among completed backend outputs**: `{weak['matrix_id']}` at {weak['log2_rop']:.6f} log2(rop)." if weak else f"Weakest {model}: UNKNOWN.")
    rows.append("")
    if all_done:
        for model, weak in obj["weakest_full_node"].items():
            rows.append(f"Weakest {model} **across all 20 independently sampled node matrices**: `{weak['matrix_id']}` at {weak['log2_rop']:.6f} log2(rop), block size {weak['blocksize']}.")
    else:
        rows.append("A weakest full-node estimate is not yet established: every registered matrix must first have finite output in both models.")
    (HERE / "estimator_results.md").write_bytes(("\n".join(rows) + "\n").encode("utf-8"))
    return obj

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", type=int)
    ap.add_argument("--matrix-id")
    ap.add_argument("--model", choices=("classical", "quantum"))
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--include-ready-frontends", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--plan-only", action="store_true", help="Validate inputs and show pending tasks; never import Sage or execute estimates")
    args = ap.parse_args()
    if args.summary_only:
        summarize()
        return
    jobs, front = collect_inputs()
    permitted = [j for j in jobs if args.include_ready_frontends or j["role"]["matrix_id"].startswith("backend_")]
    if args.job is not None or args.matrix_id:
        if not args.model:
            ap.error("--model is required for an individual task")
        selected = permitted[args.job] if args.job is not None else next((j for j in permitted if j["role"]["matrix_id"]==args.matrix_id), None)
        if selected is None:
            ap.error("Matrix is unresolved or requires --include-ready-frontends")
        if args.plan_only:
            print(json.dumps({"matrix_id": selected["role"]["matrix_id"], "output": str(next_output(selected, args.model, args.resume))}))
        else:
            run_job(selected, args.model, args.resume)
        return
    pending = []
    for job in permitted:
        for model in ("classical", "quantum"):
            destination = next_output(job, model, args.resume)
            if destination is not None:
                pending.append((job, model, destination))
    if args.plan_only:
        print(json.dumps({"ready_matrices": len(jobs), "selected_matrices": len(permitted), "pending_tasks": [{"matrix_id": j["role"]["matrix_id"], "model": m, "output": str(d)} for j,m,d in pending], "frontend_readiness": front}, sort_keys=True))
        return
    if pending:
        assert git("rev-parse", "HEAD") == PIN
        assert not git("status", "--porcelain")
        import sage.version
        import scipy, numpy
        environment = {"python": sys.version, "sage": sage.version.version,
                   "platform": platform.platform(), "executable": sys.executable,
                   "numpy": numpy.__version__, "scipy": scipy.__version__, "estimator_commit": PIN,
                   "upstream_path": str(UPSTREAM), "upstream_clean": True, "wall_timeout_seconds_per_task": 3600,
                   "commands": [sys.executable + " " + " ".join(sys.argv)],
                   "models": ["MATZOV(nn=classical)", "MATZOV(nn=quantum)"]}
        environment_bytes = json.dumps(environment, sort_keys=True, ensure_ascii=False).encode("utf-8")
        env_path = HERE / "estimator_execution_environments" / (hashlib.sha256(environment_bytes).hexdigest() + ".json")
        if not env_path.exists():
            write_exclusive(env_path, environment)
        for job, model, destination in pending:
            command = [sys.executable, str(Path(__file__).resolve()), "--matrix-id", job["role"]["matrix_id"], "--model", model]
            if args.include_ready_frontends:
                command.append("--include-ready-frontends")
            if args.resume:
                command.append("--resume")
            try:
                subprocess.run(command, check=True, timeout=3600)
            except subprocess.TimeoutExpired:
                write_exclusive(destination, {"role": job["role"], "model": model, "estimator_commit": PIN, "status": "UNKNOWN_TIMEOUT", "timeout_seconds": 3600})
    summary = summarize()
    print(json.dumps(summary["task_counts"]), flush=True)

if __name__ == "__main__":
    main()
