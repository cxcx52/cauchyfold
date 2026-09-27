#!/usr/bin/env python3
"""Run the pinned official SIS estimator on coefficient-expanded role inputs."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback

PIN = "53da5982597709ba0fdf94ea37a84d822310fd84"
ROOT = Path(__file__).resolve().parent


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value))
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def check_upstream(path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args],
                                       text=True).strip()
    if git("rev-parse", "HEAD") != PIN:
        raise ValueError("estimator commit mismatch")
    if git("status", "--porcelain"):
        raise ValueError("estimator working tree is not clean")


def worker(upstream, input_path, result_path):
    job = json.loads(input_path.read_text(encoding="utf-8"))
    record = dict(job=job, input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
                  estimator_commit=PIN)
    start = time.perf_counter()
    try:
        check_upstream(upstream)
        import sage.all as sa
        import sage.version
        sys.path.insert(0, str(upstream))
        from estimator import SIS
        from estimator.reduction import MATZOV
        role = job["instance"]
        params = SIS.Parameters(n=sa.ZZ(role["n"]), m=sa.ZZ(role["m"]),
                                q=sa.ZZ(role["q"]),
                                length_bound=sa.ZZ(role["beta"]),
                                norm=2, tag=job["job_id"])
        print("SIS parameters:", params, flush=True)
        print("MATZOV model:", job["model"], flush=True)
        costs = SIS.estimate(params, red_cost_model=MATZOV(nn=job["model"]),
                             jobs=1, catch_exceptions=False, quiet=True)
        attacks = []
        for name, cost in costs.items():
            print(name, repr(cost), flush=True)
            rop = cost.get("rop", sa.oo)
            finite = bool(rop != sa.oo and rop > 0)
            exponent = float(sa.log(rop, 2)) if finite else None
            finite = finite and math.isfinite(exponent)
            block = int(cost["beta"]) if "beta" in cost else None
            flag = ("EXTRAPOLATED_ABOVE_1024" if block is not None and block > 1024
                    else "WITHIN_DOCUMENTED_UPPER_RANGE" if block is not None
                    else "UNKNOWN_BLOCK_SIZE")
            attacks.append(dict(attack=str(name), finite=finite,
                                fields={str(k): str(v) for k, v in cost.items()},
                                log2_rop=exponent if finite else None,
                                block_size=block, documented_range_flag=flag,
                                documented_range_source="estimator/reduction.py:MATZOV"))
        finite_attacks = [a for a in attacks if a["finite"]]
        best = min(finite_attacks, key=lambda a: a["log2_rop"]) if finite_attacks else None
        record.update(status="DONE" if best else "UNKNOWN_NONFINITE",
                      attacks=attacks, best=best, sage_version=sage.version.version)
    except Exception:
        record.update(status="FAILED", error=traceback.format_exc())
        traceback.print_exc()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    record.update(wall_seconds=time.perf_counter()-start,
                  cpu_seconds=usage.ru_utime+usage.ru_stime,
                  peak_rss_kib=usage.ru_maxrss)
    write(result_path, record)
    return 0 if record["status"] == "DONE" else 1


def aggregate(output, jobs, inputs_hash, environment):
    results = []
    role_results = []
    counts = {"DONE": 0, "FAILED": 0, "UNKNOWN_NONFINITE": 0, "PENDING": 0}
    for job in jobs:
        path = output/"raw"/(job["job_id"]+".json")
        if not path.exists():
            counts["PENDING"] += 1
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        counts[result["status"]] += 1
        relative = path.relative_to(ROOT).as_posix()
        reported = [dict(attack=a["attack"],
                         reported_block_size=int(a["fields"]["beta"]) if "beta" in a["fields"] else None,
                         raw_rop=a["fields"].get("rop"),
                         finite=a["finite"]) for a in result.get("attacks", [])]
        results.append(dict(job_id=job["job_id"], instance=job["instance"],
                            model=job["model"], aliases=job["aliases"],
                            status=result["status"], best=result.get("best"),
                            reported_attacks=reported,
                            raw_output=relative,
                            raw_output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            wall_seconds=result["wall_seconds"],
                            cpu_seconds=result["cpu_seconds"],
                            peak_rss_kib=result["peak_rss_kib"]))
        for alias in job["aliases"]:
            role_results.append(dict(**alias, model=job["model"],
                                     instance=job["instance"], status=result["status"],
                                     best=result.get("best"), reported_attacks=reported,
                                     raw_output=relative))
    weakest = {}
    for arity in sorted({a["arity"] for j in jobs for a in j["aliases"]}):
        weakest[str(arity)] = {}
        for model in ("classical", "quantum"):
            rows = [r for r in role_results if r["arity"] == arity and r["model"] == model
                    and r["status"] == "DONE"]
            expected = sum(a["arity"] == arity for j in jobs if j["model"] == model
                           for a in j["aliases"])
            best = min(rows, key=lambda r: r["best"]["log2_rop"]) if rows else None
            weakest[str(arity)][model] = dict(
                complete=len(rows) == expected, completed_roles=len(rows),
                expected_roles=expected, weakest=best,
                all_runs_finished=sum(r["arity"] == arity and r["model"] == model for r in role_results) == expected,
                all_finite=len(rows) == expected,
                selection_scope="among completed finite outputs",
                unresolved_roles=[r["matrix_id"] for r in role_results
                                  if r["arity"] == arity and r["model"] == model and r["status"] != "DONE"])
    summary = dict(estimator_commit=PIN, input_sha256=inputs_hash,
                   scope="heuristic coefficient-expanded SIS attack-cost estimates",
                   full_computational_security_certified=False,
                   counts=counts, unique_jobs=len(jobs), environment=environment,
                   results=results, role_results=role_results, weakest_by_arity=weakest)
    write(output/"results.json", summary)
    write(output/"status.json", dict(counts=counts, input_sha256=inputs_hash,
                                    unique_jobs=len(jobs), pid=os.getpid(),
                                    status="COMPLETE" if not counts["PENDING"] else "RUNNING"))
    lines = ["# Official SIS estimates", "",
             "Coefficient-expanded Euclidean SIS; pinned official lattice-estimator "
             + PIN + ". Classical and quantum costs use MATZOV. These are heuristic "
             "attack-cost estimates, not full-protocol computational-security bits.", "",
             "Weakest roles below are selected **among completed finite outputs**. "
             "Official +Infinity outputs are retained as UNKNOWN_NONFINITE; they receive no "
             "security-bit assignment and are excluded from this ranking.", "",
             "| Arity | Model | Weakest finite role | log2(rop) | Block size | Range |",
             "|---:|---|---|---:|---:|---|"]
    for arity, models in weakest.items():
        for model, item in models.items():
            r = item["weakest"]
            if r:
                b = r["best"]
                lines.append(f"| {arity} | {model} | {r['matrix_id']} | "
                             f"{b['log2_rop']:.6f} | {b['block_size']} | "
                             f"{b['documented_range_flag']} |")
    lines += ["", "| Arity | Role | Model | n | m | Radius | log2(rop) | Block size | Range |",
              "|---:|---|---|---:|---:|---:|---:|---:|---|"]
    for r in sorted(role_results, key=lambda x: (x["arity"], x["matrix_id"], x["model"])):
        b = r["best"]
        e = f"{b['log2_rop']:.6f}" if b else r["status"]
        reported = r["reported_attacks"]
        reported_block = reported[0]["reported_block_size"] if reported else ""
        lines.append(f"| {r['arity']} | {r['matrix_id']} | {r['model']} | "
                     f"{r['instance']['n']} | {r['instance']['m']} | "
                     f"{r['instance']['beta']} | {e} | "
                     f"{b['block_size'] if b else reported_block} | "
                     f"{b['documented_range_flag'] if b else 'No finite modeled cost'} |")
    (output/"results.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    return summary


def run(args):
    check_upstream(args.upstream)
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    assert data["pin"] == PIN
    inputs_hash = hashlib.sha256(args.inputs.read_bytes()).hexdigest()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    old_status = output/"status.json"
    if old_status.exists():
        assert json.loads(old_status.read_text())["input_sha256"] == inputs_hash, "input changed"
    mapping = {}
    for role in data["roles"]:
        instance = dict(n=role["d"]*role["rows"], m=role["d"]*role["columns"],
                        q=role["q"], beta=role["beta"], norm=2)
        for model in ("classical", "quantum"):
            key = digest(dict(instance=instance, model=model, estimator_commit=PIN))
            job_id = key[:24]
            job = mapping.setdefault(key, dict(job_id=job_id, instance=instance,
                                               model=model, aliases=[]))
            job["aliases"].append({k: role[k] for k in
                                   ("arity", "matrix_id", "q", "d", "rows", "columns", "beta")})
    jobs = sorted(mapping.values(), key=lambda j: j["job_id"])
    for job in jobs:
        job["aliases"].sort(key=lambda r: (r["arity"], r["matrix_id"]))
        write(output/"inputs"/(job["job_id"]+".json"), job)
    import sage.version
    environment = dict(python=platform.python_version(), sage=sage.version.version,
                       platform=platform.system(), workers=args.workers,
                       upstream_unmodified=True)
    write(output/"jobs.json", dict(estimator_commit=PIN, input_sha256=inputs_hash, jobs=jobs))
    (output/"run.pid").write_text(str(os.getpid())+"\n", encoding="utf-8")
    def launch(job):
        raw = output/"raw"/(job["job_id"]+".json")
        if raw.exists():
            old = json.loads(raw.read_text(encoding="utf-8"))
            assert old["input_sha256"] == digest(job)
            return job["job_id"], old["status"]
        raw.parent.mkdir(parents=True, exist_ok=True)
        with raw.with_suffix(".stdout.log").open("wb") as stdout, \
             raw.with_suffix(".stderr.log").open("wb") as stderr:
            process = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                      "--upstream", str(args.upstream),
                                      "--worker", str(output/"inputs"/(job["job_id"]+".json")),
                                      "--result", str(raw)], stdout=stdout, stderr=stderr)
        if not raw.exists():
            write(raw, dict(job=job, input_sha256=digest(job), estimator_commit=PIN,
                            status="FAILED", error=f"worker exited {process.returncode}",
                            wall_seconds=0, cpu_seconds=0, peak_rss_kib=0))
        return job["job_id"], json.loads(raw.read_text())["status"]
    aggregate(output, jobs, inputs_hash, environment)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(launch, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            print(*future.result(), flush=True)
            summary = aggregate(output, jobs, inputs_hash, environment)
            print(json.dumps(summary["counts"], sort_keys=True), flush=True)
    manifest = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in ("manifest.json", "run.pid"):
            manifest[path.relative_to(output).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(output/"manifest.json", manifest)
    return 0 if summary["counts"]["DONE"] == len(jobs) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, default=ROOT/"artifacts"/"estimator-inputs.json")
    parser.add_argument("--output", type=Path, default=ROOT/"estimator")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if not 1 <= args.workers <= 2:
        raise ValueError("worker limit must be one or two")
    sys.exit(worker(args.upstream, args.worker, args.result) if args.worker else run(args))
