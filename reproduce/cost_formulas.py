"""Exact, deterministic CFdagger v2 Profile-I cost formulas.

No protocol execution, timing, security estimator, or random sampling occurs here.
Unknown front-compiler quantities remain None with explicit symbolic formulas.
Counts refer to the declared arithmetic algorithms, not optimized implementation
counts.  Big-O bounds and exact loop counts have different fields.
"""

from math import comb
import json
from pathlib import Path


def _ceildiv(x, y):
    return (x + y - 1) // y


def _find(obj, name):
    if isinstance(obj, dict):
        if name in obj and isinstance(obj[name], int) and not isinstance(obj[name], bool):
            return obj[name]
        for value in obj.values():
            result = _find(value, name)
            if result is not None:
                return result
    return None


def _matvec(rows, cols):
    """Full dense ring matvec, dot initialized from its first product."""
    return {"Rq_multiplications": rows * cols,
            "Rq_additions": rows * max(0, cols - 1)}


def _tree_counts(k):
    """Padded schoolbook numerator tree and monic remainder tree counters.

    A numerator node with children of size t computes N_L D_R+N_R D_L.
    Every multiply accumulator starts at zero and counts that addition.
    Remainder nodes cancel the monic leading coefficient without arithmetic;
    each lower coefficient update counts one multiply and one subtraction.
    """
    assert k >= 2 and k & (k - 1) == 0
    nm = na = rm = ra = 0
    t = 1
    while t < k:
        nodes = k // (2 * t)
        nm += nodes * 2 * t * (t + 1)
        na += nodes * (2 * t * (t + 1) + 2 * t)
        edges = k // t
        rm += edges * t * t
        ra += edges * t * t
        t *= 2
    return {"numerator_tree_multiplications": nm,
            "numerator_tree_additions": na,
            "remainder_tree_multiplications": rm,
            "remainder_tree_additions": ra}


def carrier_counts(k, compiler):
    n = _find(compiler, "semantic_dimension_n")
    y = _find(compiler, "residual_dimension_y")
    r = _find(compiler, "bilinear_image_dimension_r")
    c = _tree_counts(k)
    nm, na = c["numerator_tree_multiplications"], c["numerator_tree_additions"]
    rm, ra = c["remainder_tree_multiplications"], c["remainder_tree_additions"]
    pair_count = k + comb(k, 2)
    pair_coeffs = k * k + comb(k, 2) * (k - 1)
    # Multipoint: numerator N/M; derivative M'; evaluate N/M/M'; s;
    # rational correction; scale interpolation samples; numerator interpolate.
    mp_nm, mp_na = nm + rm + k, na + ra + k
    mp_ym = 2 * nm + (k - 1) + 2 * rm + 5 * k
    mp_ya = 2 * na + 2 * ra + 3 * k
    # Pole-residue: N; N'; evaluate padded N'; form the regular part v_i;
    # residues; reconstruct from simple poles with another numerator tree.
    pr_nm, pr_na = nm + (k - 1) + rm + 2 * k, na + ra + 2 * k
    def eval_linear(a, x, b=0, z=0):
        return None if x is None or z is None else a * x + b * z
    tree_setup_products = 0
    t = 1
    while t < k:
        tree_setup_products += (k // (2 * t)) * (t + 1) ** 2
        t *= 2
    horner_setup = k * ((k - 1) + (k - 2) + (k - 1) + k + (k - 1))
    derivative_setup = k + (k - 1) + k
    return {
        "scope": "Exact online loop counts for specified reference polynomial algorithms; public scalar polynomial constants are precomputed separately.",
        "dimensions": {"n": n, "y": y, "r": r},
        "algorithm_model": {
            "polynomial_multiply": "dense schoolbook; zero-initialized accumulators; no sparsity shortcuts",
            "polynomial_remainder": "monic schoolbook division; fixed padded degrees; leading cancellation free",
            "source_scales": "all lambda_i=1",
            "polynomial_constants": "in Fq because poles and interpolation nodes are in Fq",
            "scalar_multiply_unit": "K_by_Fq multiplication = extension_degree base-field multiplications",
            "basis_map": "J:Y_B->K^r; one application counted separately from B or Q",
            "unresolved_evaluation_costs": ["arithmetic circuit for Q", "arithmetic circuit for B", "basis-coordinate map J"]},
        "structural_tree_counts_per_coordinate": c,
        "streaming_pair_reference": {
            "bilinear_map_evaluations": pair_count,
            "basis_map_evaluations": pair_count,
            "K_by_Fq_multiplications_formula": f"{pair_coeffs}*r",
            "K_by_Fq_multiplications": None if r is None else pair_coeffs * r,
            "K_additions_formula": f"{pair_coeffs}*r",
            "K_additions": None if r is None else pair_coeffs * r,
            "scope": "Stream each mixed B term through J and accumulate its public P_i or P_ij coefficients; no pair table is stored."},
        "multipoint": {
            "quadratic_map_evaluations_if_source_values_cached": k,
            "quadratic_map_evaluations_if_source_values_uncached": 2 * k + 1,
            "basis_map_evaluations": k,
            "K_by_Fq_multiplications_formula": f"{mp_nm}*n+{mp_ym}*y",
            "K_by_Fq_multiplications": eval_linear(mp_nm, n, mp_ym, y),
            "K_additions_formula": f"{mp_na}*n+{mp_ya}*y",
            "K_additions": eval_linear(mp_na, n, mp_ya, y),
            "online_inversions": 0,
            "basis_maps_applied_after": "interpolating the ambient-Y carrier coefficients"},
        "pole_residue": {
            "bilinear_map_evaluations": k,
            "basis_map_evaluations": k,
            "K_by_Fq_multiplications_formula": f"{pr_nm}*n+{nm}*r",
            "K_by_Fq_multiplications": eval_linear(pr_nm, n, nm, r),
            "K_additions_formula": f"{pr_na}*n+{na}*r",
            "K_additions": eval_linear(pr_na, n, na, r),
            "online_inversions": 0,
            "basis_maps_applied_after": "computing the k bilinear residues, before reconstructing coefficients"},
        "precomputation": {
            "scope": "One-time public constants; excluded from the online counts and must not be described as free end-to-end work.",
            "constant_set": ["pole product tree", "interpolation-node product tree", "D',D''", "D'(xi_i)^-1", "D''(xi_i)/(2D'(xi_i))", "D(tau_i),D'(tau_i),D(tau_i)^-1,D(tau_i)^-2", "interpolation derivative reciprocals", "P_i and P_ij for the streaming reference"],
            "joint_fast_algorithm_constant_builder": {
                "Fq_multiplications": 2 * tree_setup_products + derivative_setup + horner_setup + 3 * k,
                "Fq_additions_or_subtractions": 2 * tree_setup_products + horner_setup + 2 * k,
                "Fq_inversions": 3 * k,
                "model": "Build both scalar product trees schoolbook; formal derivatives including multiply-by-one; Horner evaluations; individual inverses; inverse-two is the public integer(q+1)/2. This prepares constants shared by both fast algorithms once, not once per witness."},
            "streaming_reference_extra_constants": {
                "Fq_multiplications": k * (k - 1) * k + comb(k, 2) * (k - 2) * (k - 1),
                "Fq_additions": k * (k - 1) * k + comb(k, 2) * (k - 2) * (k - 1),
                "model": "Independently multiply the k-1 or k-2 selected linear factors for every P_i/P_ij, starting with polynomial1; no shared-factor optimization."},
            "basis_dependent_setup": "J construction and Q/B circuit compilation require the compiler manifest; they are not claimed in these scalar constants."},
        "asymptotic_fast_carrier": "O((n+y)*M(k)*log(k+1)+k*C_Q) for multipoint; O((n+r)*M(k)*log(k+1)+k*(C_B+C_J)) for pole-residue under the declared basis-map costs.",
        "contribution_scope": "Only construction algorithms and their costs. Carrier representation and minimum width belong to the Resource companion paper."
    }


def build_costs(params, layers, registry, compiler):
    f, b, front = params["field"], params["backend"], params["front_end"]
    k, d, e = params["cauchy"]["arity"], f["ring_degree"], f["extension_degree"]
    fqbytes = params["serialization"]["field_coefficient_bytes"]
    a, at, ah, ap = b["main_rank"], b["auxiliary_B_rank"], b["auxiliary_D_rank"], b["pivot_rank"]
    m, tau, digits = b["projection_rows"], b["tau"], b["digit_count"]
    rp, rc = b["projection_retry_cap"], b["response_retry_cap"]
    ell = _find(compiler, "sumcheck_rounds")
    p0 = _find(compiler, "fixed_zero_coordinates_count")
    ast, acar, aaux = front["state_commitment_rank"], front["carrier_commitment_rank"], front["auxiliary_commitment_rank"]
    frontnew = fqbytes * d * (ast + acar + aaux)
    incomingfresh = k * ast * d * fqbytes
    incomingacc = ast * d * fqbytes
    wire_layers, operation_layers = [], []
    sum_payload = sum_proj = sum_short = sum_alpha_known = 0
    for i, layer in enumerate(layers):
        s, n, N = layer["blocks"], layer["block_length_ring"], layer["padded_source_coefficients"]
        terminal = layer["terminal"]
        if i == 0:
            # k+2 shared-A_st state records, one carrier and one auxiliary.
            base_rows = ((k + 2) * ast + acar + aaux) * d + 3 * e + 1 + layer["padding"]
            rel_rows = None if p0 is None else base_rows + p0
            rowformula = f"{base_rows}+P0"
        else:
            base_rows = d * (at + ah + a + tau) + tau + layer["padding"]
            rel_rows = base_rows
            rowformula = str(base_rows)
        projbytes = _ceildiv(2 * m * N, 8)
        shortbytes = _ceildiv(3 * s * d, 8)
        alpha_known = fqbytes * tau * (base_rows + m)
        alphabytes = None if rel_rows is None else fqbytes * tau * (rel_rows + m)
        alphaformula = f"{alpha_known}+{fqbytes*tau}*P0" if i == 0 else str(alpha_known)
        pbytes = fqbytes * m
        if terminal:
            tbytes = fqbytes * (s - 1) * a * d
            pivotbytes = fqbytes * ap * d
            hcoeff = tau * (d * s * (s + 1) // 2 - 1)
            hbytes, zbytes = fqbytes * hcoeff, fqbytes * d * n
            messages = [
                {"name": "t_1,...,t_(s-1)", "bytes": tbytes, "fixed_before": "projection"},
                {"name": "pivot_digest", "bytes": pivotbytes, "fixed_before": "projection"},
                {"name": "selected_p", "bytes": pbytes, "fixed_before": "aggregation"},
                {"name": "symmetric_h_except_ct_h00", "bytes": hbytes, "fixed_before": "short_challenge"},
                {"name": "raw_canonical_z", "bytes": zbytes, "fixed_before": "terminal_verification"}]
            payload = tbytes + pivotbytes + pbytes + hbytes + zbytes
        else:
            messages = [
                {"name": "u1", "bytes": fqbytes * at * d, "fixed_before": "projection"},
                {"name": "selected_p", "bytes": pbytes, "fixed_before": "aggregation"},
                {"name": "u2", "bytes": fqbytes * ah * d, "fixed_before": "short_challenge"}]
            payload = fqbytes * d * (at + ah) + pbytes
        wire_layers.append({
            "level": i, "terminal": terminal, "prover_messages": messages,
            "fixed_prover_payload_bytes": payload,
            "accepted_attempt_tag_bytes_formula": f"P_{i}+C_{i}",
            "accepted_prover_bytes_no_retry": payload + 2,
            "accepted_prover_bytes_max_attempts": payload + rp + rc,
            "source_relation_rows": rel_rows, "source_relation_rows_formula": rowformula,
            "projection_matrix_bytes_per_attempt": projbytes,
            "projection_trits_per_attempt": m * N,
            "aggregation_bytes_once": alphabytes, "aggregation_bytes_once_formula": alphaformula,
            "short_challenge_bytes_per_attempt": shortbytes,
            "verifier_bytes_formula": f"{projbytes}*P_{i}+({alphaformula})+{shortbytes}*C_{i}",
            "verifier_bytes_no_retry": None if alphabytes is None else projbytes + alphabytes + shortbytes,
            "verifier_bytes_max_attempts": None if alphabytes is None else rp * projbytes + alphabytes + rc * shortbytes})
        sum_payload += payload
        sum_proj += projbytes
        sum_short += shortbytes
        sum_alpha_known += alpha_known
        h_pairs = s * (s + 1) // 2
        ops = {
            "level": i, "terminal": terminal,
            "t_Aw_all_source_blocks_once": _matvec(a * s, n),
            "symmetric_h_once": {
                "Rq_multiplications": tau * s * s * n,
                "Rq_additions": tau * (s * s * (n - 1) + s * (s - 1) // 2),
                "Fq_multiplications_by_inverse_two": tau * s * (s - 1) // 2 * d,
                "algorithm": "Diagonal uses one dot product; each off-diagonal uses two dots, one ring addition, and coefficientwise division by 2."},
            "projection_per_attempt": {
                "trits_generated_by_verifier": m * N,
                "independent_random_bits_consumed_exactly": 2 * m * N,
                "prover_trits_inspected": m * N,
                "prover_integer_additions_or_subtractions_exact": "number of nonzero trits, with zero-initialized accumulators",
                "prover_integer_additions_or_subtractions_expectation": m * N // 2,
                "centered_mod_q_reductions": m,
                "integer_squares_for_norm": m,
                "integer_additions_for_norm": m - 1},
            "response_per_attempt": {
                "bounded_coefficient_times_Fq_coefficient_multiplications": s * n * d * d,
                "Fq_additions_or_subtractions": n * (s * d * d - d),
                "centered_mod_q_reductions": n * d,
                "integer_squares_for_norm": n * d,
                "integer_additions_for_norm": n * d - 1,
                "short_coefficients_sampled": s * d,
                "terminal_c0_sampling": "Exact uniform box conditioned on the nonzero ring element; sampling trial count is variable." if terminal else "independent uniform five-symbol coefficients"},
            "public_aggregation_once_each_party": {
                "source_relation_transpose_calls": tau,
                "projection_part_trits_inspected": tau * m * N,
                "projection_part_Fq_additions_or_subtractions_exact": "tau times number of nonzero selected projection trits",
                "projection_part_Fq_additions_or_subtractions_expectation": tau * m * N // 2,
                "combine_source_and_projection_Fq_additions": tau * N,
                "constant_term_adjoint_packing_Fq_negations": tau * (N // d) * (d - 1),
                "rhs_Fq_multiplications": None if rel_rows is None else tau * (rel_rows + m),
                "rhs_Fq_multiplications_formula": f"{tau}*(({rowformula})+{m})",
                "rhs_Fq_additions": None if rel_rows is None else tau * (rel_rows + m - 1),
                "source_relation_transpose_cost": "level 0 requires compiler sparse operators; later levels use the preceding child relation decomposition below"},
            "verifier_selected_projection_norm_once": {
                "integer_squares": m, "integer_additions": m - 1,
                "integer_bound_comparisons": 1},
        }
        if terminal:
            lp = 0
            while b["pivot_radix"] ** lp < f["q"]:
                lp += 1
            ops["pivot_commitment_once"] = _matvec(ap, a * lp)
            ops["terminal_verifier"] = {
                "A_z": _matvec(a, n),
                "subtract_nonpivot_t": {"bounded_ring_multiplications": a * (s - 1), "Rq_additions_or_subtractions": a * (s - 1)},
                "invert_c0": {"Rq_unit_inversions": 1, "Rq_multiplications": a},
                "pivot_digest_check": _matvec(ap, a * lp),
                "pivot_digit_extraction_integer_steps": a * d * lp,
                "phi_challenge_combination": {"bounded_ring_multiplications": tau * s * n, "Rq_additions": tau * n * (s - 1)},
                "principal_lhs": _matvec(tau, n),
                "cached_challenge_products": {"bounded_by_bounded_ring_multiplications": h_pairs, "coefficient_multiplications_by_two": d * s * (s - 1) // 2},
                "principal_rhs": _matvec(tau, h_pairs),
                "reconstruct_omitted_constants_Fq_additions_or_subtractions": tau * (s - 1),
                "response_norm_integer_squares": d * n,
                "response_norm_integer_additions": d * n - 1,
                "principal_ring_equality_coefficients_compared": tau * d,
                "pivot_digest_coefficients_compared": ap * d,
                "scope": "Excludes public aggregation, counted above; checks occur only after the accepted terminal response."}
        else:
            Lt, Lh = layer["Lt_ring"], layer["Lh_ring"]
            ops["u1_commitment_once"] = _matvec(at, Lt)
            ops["u2_commitment_once"] = _matvec(ah, Lh)
            ops["digit_decomposition_integer_steps"] = (a * s + tau * h_pairs) * d * digits
            ops["accepted_response_split_integer_steps"] = d * n
            ops["child_relation_operator_decomposition"] = {
                "B_t": _matvec(at, Lt), "D_h": _matvec(ah, Lh), "A_z": _matvec(a, n),
                "recompose_z": {"Fq_multiplications_by_radix": d * n, "Fq_additions": d * n},
                "recompose_t_h": {"Fq_multiplications_by_radix_powers": d * (digits - 1) * (a * s + tau * h_pairs), "Fq_additions": d * (digits - 1) * (a * s + tau * h_pairs)},
                "t_challenge_rhs": {"bounded_ring_multiplications": a * s, "Rq_additions": a * (s - 1)},
                "principal_lhs": _matvec(tau, n), "principal_rhs": _matvec(tau, h_pairs),
                "constant_diagonal_sums_Fq_additions": tau * (s - 1),
                "rowblock_subtractions_Fq": d * (a + tau),
                "public_preprocessing_per_selected_challenge": {"phi_combination_bounded_ring_multiplications": tau * s * n, "phi_combination_Rq_additions": tau * n * (s - 1), "challenge_products_bounded_by_bounded_ring_multiplications": h_pairs, "offdiagonal_weight_multiplications_by_two": d * s * (s - 1) // 2},
                "transpose_implementation": "Reverse the declared linear circuit. Every forward constant multiplication gives one transpose multiplication in the same coefficient algebra; each forward addition gives two accumulations if the transpose accumulators start at zero. Coordinate copies, ct selection, and padding are counted as copies/zero checks, not multiplications.",
                "status": "Exact primitive decomposition; no dense Fq matrix is instantiated and no wall-time inference is made."}
            fq_scalar = d * n + d * (digits - 1) * (a * s + tau * h_pairs)
            rq_mul = at * Lt + ah * Lh + a * n + tau * n + tau * h_pairs
            rq_bounded = a * s
            rq_add = (at * (Lt - 1) + ah * (Lh - 1) + a * (n - 1)
                      + tau * (n - 1) + tau * (h_pairs - 1) + a * (s - 1))
            fq_add = fq_scalar + tau * (s - 1) + d * (a + tau)
            next_pad = layers[i + 1]["padding"]
            ops["child_relation_exact_linear_circuit_counts"] = {
                "fixed_general_Rq_multiplications": rq_mul,
                "fixed_bounded_Rq_multiplications": rq_bounded,
                "Fq_multiplications_by_radix_powers": fq_scalar,
                "Rq_additions": rq_add,
                "Fq_additions_or_subtractions": fq_add,
                "constant_term_coordinate_copies": tau * s,
                "next_block_padding_coordinate_copies": next_pad,
                "transpose_same_typed_multiplication_counts": True,
                "transpose_Fq_accumulations_zero_initialized": (
                    d * (rq_mul + rq_bounded + 2 * rq_add)
                    + fq_scalar + 2 * fq_add + tau * s + next_pad),
                "transpose_model": "Reverse the declared linear circuit with zero-initialized adjoints: one accumulation after each fixed multiplication, two after each addition/subtraction, one for each coordinate copy. Ring adjoint constants are coefficient-involuted public constants; sign/permutation preprocessing is separate. This is an exact reference implementation count, not a claim of minimal arithmetic."}
        operation_layers.append(ops)
    nlevels = len(layers)
    backend_no = sum_payload + 2 * nlevels
    backend_max = sum_payload + (rp + rc) * nlevels
    field_intercept, field_slope = 3 * e * fqbytes, 4 * e * fqbytes
    full_no_intercept = backend_no + frontnew + field_intercept
    full_max_intercept = backend_max + frontnew + field_intercept
    v_no_intercept = sum_proj + sum_short + sum_alpha_known + e * fqbytes
    v_max_intercept = rp * sum_proj + rc * sum_short + sum_alpha_known + e * fqbytes
    v_ell_slope, v_p0_slope = 2 * e * fqbytes, fqbytes * tau
    comm = {
        "status": "EXACT_PARAMETERIZED_LEDGER_COMPILER_FIELDS_UNRESOLVED" if ell is None or p0 is None else "EXACT_ACCEPTED_TRANSCRIPT_LEDGER",
        "protocol": "CFdagger v2 Profile I, k=16; section-19 terminal; raw terminal coefficients",
        "scope": "Accepted interactive transcripts; attempted malformed messages reject and do not buy retries. Failed sessions stop early and have no fixed full length.",
        "serialization": {
            "Fq": "six-byte little-endian integer in [0,q); reject other values",
            "K": "four canonical Fq coefficients in basis [1,u,u^2,u^3]",
            "Rq": "64 canonical Fq coefficients, increasing powers of X",
            "projection_trit": "2-bit LSB-first code:00=0,01=+1,10=-1,11 invalid. Sample two independent fair bits and take their difference, then encode; symbol probabilities1/2,1/4,1/4.",
            "short_challenge": "3-bit LSB-first code maps0..4 to -2..2;5..7 invalid; terminal first ring element must be nonzero",
            "retry_framing": "One byte after each projection or short-challenge attempt:00=payload-free RETRY;01=ACCEPT. ACCEPT projection is followed by p; ACCEPT nonterminal response enters child, ACCEPT terminal response is followed by z.",
            "bit_padding": "Each message separately byte-aligned; all unused high bits zero",
            "sumcheck": "Four K coefficients per degree-at-most-three round; no erasure",
            "parameter_id": "Already public; not resent inside a fold. If transported, its actual bytes are a separate application envelope.",
            "raw_terminal": "Exactly d*n_T canonical Fq coefficients; no Rice/arithmetic codec."},
        "compiler_variables": {"ell_sumcheck_rounds": ell, "P0_total_fixed_zero_coordinates_within_handoff_capacity": p0,
            "missing_definitions": ["actual compiler sumcheck_rounds", "actual compiler fixed_zero_coordinates_count"] if ell is None or p0 is None else []},
        "incoming_commitments": {"fresh_count": k, "fresh_bytes": incomingfresh, "accumulator_count": 1, "accumulator_bytes": incomingacc, "total_input_commitment_bytes": incomingfresh + incomingacc, "scope": "Listed independently from fold messages; whether already held or transported is explicit below."},
        "front_end_commitments": {"carrier_bytes": acar * d * fqbytes, "folded_output_bytes": ast * d * fqbytes, "field_auxiliary_bytes": aaux * d * fqbytes, "total_bytes": frontnew},
        "field_messages": {"P_to_V_bytes_formula": f"{field_slope}*ell+{field_intercept}", "P_to_V_bytes": None if ell is None else field_slope * ell + field_intercept, "V_to_P_bytes_formula": f"{v_ell_slope}*ell", "V_to_P_bytes": None if ell is None else v_ell_slope * ell, "Cauchy_challenge_V_to_P_bytes": e * fqbytes},
        "layers": wire_layers,
        "backend_P_to_V": {"fixed_payload_bytes": sum_payload, "no_retry_bytes": backend_no, "maximum_attempts_bytes": backend_max, "actual_bytes_formula": f"{sum_payload}+sum_i(P_i+C_i)", "reference_v2_conservative_upper_bytes": 305658, "reference_difference_explanation": "v2 used2+RP+RC bytes per layer as an upper allowance. The selected exact one-tag-per-attempt grammar needs at mostRP+RC,12 fewer bytes across six layers; no protocol object is erased."},
        "fold_P_to_V": {"no_retry_formula": f"{full_no_intercept}+{field_slope}*ell", "no_retry_bytes": None if ell is None else full_no_intercept + field_slope * ell, "maximum_attempts_formula": f"{full_max_intercept}+{field_slope}*ell", "maximum_attempts_bytes": None if ell is None else full_max_intercept + field_slope * ell, "actual_formula": f"{sum_payload+frontnew+field_intercept}+{field_slope}*ell+sum_i(P_i+C_i)", "fresh_input_commitments_included": False, "accumulator_commitment_included": False},
        "fold_V_to_P": {"no_retry_formula": f"{v_no_intercept}+{v_ell_slope}*ell+{v_p0_slope}*P0", "no_retry_bytes": None if ell is None or p0 is None else v_no_intercept + v_ell_slope * ell + v_p0_slope * p0, "maximum_attempts_formula": f"{v_max_intercept}+{v_ell_slope}*ell+{v_p0_slope}*P0", "maximum_attempts_bytes": None if ell is None or p0 is None else v_max_intercept + v_ell_slope * ell + v_p0_slope * p0, "projection_bytes_per_one_attempt_each_layer": sum_proj, "short_challenge_bytes_per_one_attempt_each_layer": sum_short, "aggregation_known_constant_bytes": sum_alpha_known},
        "interactive_total": {"no_retry_formula": f"{full_no_intercept+v_no_intercept}+{field_slope+v_ell_slope}*ell+{v_p0_slope}*P0", "maximum_attempts_formula": f"{full_max_intercept+v_max_intercept}+{field_slope+v_ell_slope}*ell+{v_p0_slope}*P0", "transport_fresh_commitments_add_bytes": incomingfresh, "transport_accumulator_also_add_bytes": incomingacc, "application_public_inputs": "Not numerically defined without actual application/compiler; include separately if transmitted."},
        "attempts": {"P_i": f"projection attempts in1..{rp}", "C_i": f"short-challenge attempts in1..{rc}", "statistics": "The worst-case and no-retry ledgers are exact lengths at those attempt counts, not expected communication."},
        "sampling_coins_vs_wire": "Wire lengths are for sampled values. Uniform Fq/K/five-symbol sampling can use exact rejection sampling, whose consumed random-bit count is variable. The projection sampler alone consumes exactly two fair bits per trit before canonical two-bit encoding. No fixed seed substitutes for independent randomness.",
        "unresolved": ["ell from actual R1CS compiler", "P0 from exact fixed-coordinate list", "application public-input transport if included in the enclosing network protocol"]
    }
    n = _find(compiler, "semantic_dimension_n")
    y = _find(compiler, "residual_dimension_y")
    r = _find(compiler, "bilinear_image_dimension_r")
    ca = _find(compiler, "auxiliary_commitment_columns")
    if ca is None:
        ca = _find(compiler, "auxiliary_ring_columns")
    opst = None if n is None or y is None else _matvec(ast, 3 * (n + y))
    oph = None if r is None else _matvec(acar, 3 * k * r)
    opa = None if ca is None else _matvec(aaux, ca)
    op = {
        "status": "EXACT_PRIMITIVE_COUNTS_AND_COMPILER_PARAMETERIZED_COUNTS",
        "not_wall_clock": True,
        "units": {"Rq_multiplication_schoolbook": {"Fq_multiplications": d * d, "Fq_additions_or_subtractions": d * (d - 1)}, "Rq_addition": {"Fq_additions": d}, "bounded_ring_multiplication_schoolbook": {"bounded_scalar_times_Fq_multiplications": d * d, "Fq_additions_or_subtractions": d * (d - 1)}, "K_addition": {"Fq_additions": e}, "K_by_Fq_multiplication": {"Fq_multiplications": e}, "note": "Units are retained separately. Ring inversions, integer division/squares, general K multiplication, and Q/B/J calls are not assigned fictitious equivalent costs."},
        "carrier": carrier_counts(k, compiler),
        "front_commitments": {"incoming_fresh_commitments": {"count": k, "one_dense_matvec": opst, "columns_formula": "3*(n+y)", "included_in_fold_prover_work": False}, "accumulator_commitment": {"count": 1, "one_dense_matvec": opst, "included_in_fold_prover_work": False}, "new_folded_output": opst, "new_carrier": oph, "new_auxiliary": opa, "formulas": {"state_Rq_mult": f"{ast}*3*(n+y)", "carrier_Rq_mult": f"{acar}*3*{k}*r", "auxiliary_Rq_mult": f"{aaux}*b_aux"}, "bit_optimized_alternative": "Actual openings are bit vectors. A coefficient-streamed implementation can replace coefficient products by selected additions; the count then depends on actual bits. Dense ring counts here are a deterministic reference, not an assertion this is the implementation."},
        "field_front_end": {
            "sumcheck_rounds": ell,
            "R1CS_apply_A_B_C": "Requires compiler sparse matrices or arithmetic-operation manifest; dimensions/caps alone do not determine nonzero counts.",
            "terminal_transposes": "Three K-valued transpose applications to eq_tau; exact sparse operation counts require compiler output.",
            "sumcheck_polynomial_coefficients_transmitted": None if ell is None else 4 * ell,
            "prover_eq_table_construction": {"K_multiplications_formula": "2^ell-1", "K_subtractions_formula": "2^ell-1", "algorithm": "At each branching entryx compute xr and x-xr; no repeated full product for each Boolean point."},
            "prover_sumcheck_table_rounds": {"K_multiplications_formula": "14*(2^ell-1)", "K_additions_or_subtractions_formula": "17*(2^ell-1)", "K_multiplications": None if ell is None else 14 * ((1 << ell) - 1), "K_additions_or_subtractions": None if ell is None else 17 * ((1 << ell) - 1), "algorithm": "For each pair of entries in four tables(E,A,B,C), form four linear differences; expand E*(A*B-C) using10 multiplications,9 adds/subtracts; accumulate4 coefficients into zero-initialized g; fold4 tables at the challenge using4 multiplications and4 additions. Cache differences within the round. Across rounds there are2^ell-1 such pairs."},
            "sumcheck_verifier_per_round": {"K_additions_for_g0_plus_g1": 4, "K_multiplications_for_Horner_evaluation": 3, "K_additions_for_Horner_evaluation": 3, "K_equalities": 1},
            "sumcheck_verifier_final": {"formula": "eq(r,tau)*(tA*tB-tC)", "K_multiplications": None if ell is None else 3 * ell + 1, "K_additions_or_subtractions": None if ell is None else 3 * ell + 1, "algorithm": "For ell>=1 each eq factor is(1-r)*(1-t)+r*t:2 multiplications,3 adds/subtracts. Multiply ell factors with ell-1 multiplications. Then tA*tB-tC and final multiplication add2 multiplications and1 subtraction.", "K_equality": 1},
            "verifier_eq_tau_table_for_transposes": {"K_multiplications_formula": "2^ell-1", "K_subtractions_formula": "2^ell-1"},
            "public_Cauchy_weights": {"K_subtractions": k, "K_multiplications": 3 * (k - 1), "K_inversions": 1, "algorithm": "Batch-invert k nonzero c-xi differences; prefix product also gives D(c). Scales are1."},
            "honest_prover_asymptotic": "O(W_F+M_c)", "unresolved": ["actual Q circuit", "actual R1CS sparse matrices", "constraint padding and sumcheck tables", "field gate/comparator manifest"]},
        "lattice_layers": operation_layers,
        "verifier_scope": "Public aggregation/transposes per layer plus terminal checks and field checks; explicit independent projection generation and reading are fully counted. No succinct-verifier claim.",
        "whole_protocol_asymptotic": {"prover": "O_tilde_lambda(W_F+C_H+N^(1+eta)) for the fixed-depth schedule theorem hypotheses", "verifier": "O_tilde_lambda(W_F+N)", "fold_P_to_V": "O_tilde_lambda(N^((1-eta)^(L+1))+1)", "Profile_I_V_to_P": "O_tilde_lambda(N)", "concrete_scope": "The selected six-layer integer schedule is checked directly; the theorem exponent is not an exact operation count."},
        "unresolved": ["actual semantic dimensions n,y,r and basis map", "Q/B arithmetic circuits", "actual auxiliary commitment columns", "actual R1CS operation manifest and sumcheck round count"]
    }
    if compiler.get("status") == "COMPLETE":
        _complete_costs(params, layers, registry, compiler, comm, op)
    return comm, op


def _complete_costs(params, layers, registry, compiler, comm, op):
    """Resolve counts from the actual deterministic compiler, never from a cap.

    Arithmetic counts below specify literal reference loops, including stored
    zero coefficients.  This makes the declared counts independent of c.  The
    compiler also exports actual nonzero counts for its reference c separately.
    """
    derivation_path = Path(__file__).resolve().parent / "compiler_artifacts/operation_derivation.json"
    cd = json.loads(derivation_path.read_bytes())
    assert cd["semantic_Q"] == {"K_add": 32, "K_mul": 36}
    assert cd["semantic_B"] == {"K_add": 68, "K_mul": 72}
    dims = compiler["resolved_dimensions"]
    n, y, r = (dims[x] for x in ("semantic_dimension_n", "residual_dimension_y", "bilinear_image_dimension_r"))
    ell = dims["sumcheck_rounds"]
    mc = 1 << ell
    handoff = compiler["handoff"]
    capacity = handoff["capacity_coefficients"]
    d = params["field"]["ring_degree"]
    tau = params["backend"]["tau"]
    comm["measurement_status"] = "syntax-level exact communication, not measured serialized proof files"
    comm["interactive_total"]["no_retry_bytes"] = comm["fold_P_to_V"]["no_retry_bytes"] + comm["fold_V_to_P"]["no_retry_bytes"]
    comm["interactive_total"]["maximum_attempts_bytes"] = comm["fold_P_to_V"]["maximum_attempts_bytes"] + comm["fold_V_to_P"]["maximum_attempts_bytes"]
    comm["interactive_total"]["application_public_inputs"] = "The public instance, parameter identifier and CRS are prior public inputs; their application envelope is outside this fold syntax. Source public coordinates are bound by the compiled constraints."
    comm["unresolved"] = []
    op["status"] = "COMPLETE_CONCRETE_TYPED_REFERENCE_OPERATION_COUNTS"
    op["unresolved"] = []
    op["compiler_operation_manifest"] = {
        "source": "compiler_artifacts/operation_derivation.json",
        "compiler_counts": compiler["operation_counts"],
        "derivation": cd,
        "interpretation": "Compilation, witness construction and online arithmetic are separated. Integer/bit work is not added to field or ring arithmetic."
    }
    ca = op["carrier"]
    ca["algorithm_model"]["unresolved_evaluation_costs"] = []
    ca["algorithm_model"]["semantic_Q"] = {"K_multiplications": 36, "K_additions_or_subtractions": 32}
    ca["algorithm_model"]["semantic_B"] = {"K_multiplications": 72, "K_additions_or_subtractions": 68}
    ca["algorithm_model"]["basis_map"] = "U and J are identity maps on K^4; each application copies 4 K coordinates, with no field multiplication or addition."
    ca["asymptotic_fast_carrier"] = "Multipoint ambient-Y construction: O((n+y)*M(k)*log(k+1)+k*C_Q), followed by k image-basis conversions of cost C_J each. Pole-residue: O((n+r)*M(k)*log(k+1)+k*(C_B+C_J)). Here J=I_4 contributes only coordinate copies."
    ca["precomputation"]["basis_dependent_setup"] = "The compiler exports U=J=I_4 explicitly; generating the two 4-by-4 identity artifacts needs 32 integer entries. Q/B sparse monomials are given in relation_spec.json and the relation artifact."
    for name, qcalls, bcalls in (("streaming_pair_reference", 0, 136), ("multipoint", 16, 0), ("pole_residue", 0, 16)):
        row = ca[name]
        row["map_arithmetic"] = {
            "Q_evaluations": qcalls,
            "B_evaluations": bcalls,
            "K_multiplications": 36 * qcalls + 72 * bcalls,
            "K_additions_or_subtractions": 32 * qcalls + 68 * bcalls,
            "J_applications": row["basis_map_evaluations"],
            "J_K_coordinate_copies": r * row["basis_map_evaluations"],
            "J_field_additions": 0,
            "J_field_multiplications": 0,
        }
        row["online_typed_totals"] = {
            "K_by_Fq_multiplications": row["K_by_Fq_multiplications"],
            "K_multiplications": 36 * qcalls + 72 * bcalls,
            "K_additions_or_subtractions": row["K_additions"] + 32 * qcalls + 68 * bcalls,
            "J_applications": row["basis_map_evaluations"],
            "J_K_coordinate_copies": r * row["basis_map_evaluations"],
        }
    ca["multipoint"]["uncached_source_values_additional_arithmetic"] = {
        "Q_evaluations": 17,
        "K_multiplications": 612,
        "K_additions_or_subtractions": 544,
        "scope": "Added only if the 17 honest source Q-values are not already available."
    }
    assert (n, y, r) == (69, 4, 4), "The concrete Q/B loop expansion is relation-specific."
    ff = op["field_front_end"]
    ff["unresolved"] = []
    ff["compiler_constraint_count_unpadded"] = compiler["r1cs"]["constraint_count_unpadded"]
    ff["compiler_constraint_count_padded"] = mc
    ff["compiler_constraint_padding_zero_rows"] = mc - compiler["r1cs"]["constraint_count_unpadded"]
    ff["constraint_and_encoding_construction"] = cd
    sparse = cd["matrix_summary"]
    applications, transposes = {}, {}
    for name in ("A", "B", "C"):
        sm = sparse[name]
        entries = sm["stored_entries"]
        applications[name] = {
            "K_by_Fq_multiplications": entries,
            "K_additions": entries - sm["nonempty_rows"],
            "stored_entries_read": entries,
            "reference_actual_nonzero_entries": sm["actual_nonzero_entries"],
            "output_K_coordinate_writes": mc,
            "algorithm": "One K-by-Fq product for every stored CSR entry; initialize each nonempty dot product with its first product, then add remaining products. Empty and padded rows are written as zero. Boolean input coefficients are not skipped."
        }
        transposes[name] = {
            "K_multiplications": entries,
            "K_additions": entries - sm["nonempty_columns"],
            "stored_entries_read": entries,
            "output_K_coordinate_writes": capacity,
            "algorithm": "Multiply each stored coefficient by the corresponding K equality-table entry and accumulate into its column. Initialize each reached column from its first product. Unreached columns are zero."
        }
    ff["R1CS_apply_A_B_C"] = applications
    ff["terminal_transposes"] = {
        "per_party_once": transposes,
        "scope": "The three public transpose vectors are computed once by each party and used by the initial lattice relation. They are not recomputed for each projection retry."
    }
    ff["prover_eq_table_construction"].update(K_multiplications=mc-1, K_subtractions=mc-1)
    ff["verifier_eq_tau_table_for_transposes"].update(K_multiplications=mc-1, K_subtractions=mc-1)
    ff["sumcheck_verifier_all_rounds"] = {
        "K_multiplications": 3 * ell,
        "K_additions_or_subtractions": 7 * ell,
        "K_equalities": ell
    }
    ff["prover_sumcheck_table_rounds"]["algorithm"] = "For each pair in the four tables, form four linear differences. Expanding E*(A*B-C) then uses 10 products and 5 further additions/subtractions. Add four polynomial coefficients to zero-initialized accumulators, then fold four tables using 4 products and 4 additions. Thus each pair costs 14 K products and 17 K additions/subtractions. Across all rounds there are M_c-1 pairs."
    ff["final_prover_evaluations"] = {
        "K_coordinate_reads": 3,
        "additional_K_multiplications": 0,
        "additional_K_additions": 0,
        "reason": "t_A,t_B,t_C are the three final values already produced by the counted table-folding loops."
    }
    ff["canonical_encoding_and_helpers"] = cd["encoding"]
    ff["constraint_categories"] = cd["constraints_by_category"]
    ff["compiler_generation"] = cd["compiler_generation"]
    ff["public_coefficients"] = cd["public_coefficients"]
    ff["public_Cauchy_weights"] = {
        "status": "INCLUDED_IN_PUBLIC_COEFFICIENT_PREPARATION_NOT_AN_ADDITIONAL_COST",
        "source": "compiler_artifacts/operation_derivation.json#/public_coefficients",
        "batch_weight_subroutine_K_multiplications": 48,
        "scope": "The actual literal compiler uses 16 prefix products and 32 backward products. Its complete challenge-data recipe also prepares squares, carrier powers and folded public coordinates; count that recipe once."
    }
    ff["semantic_witness_construction"] = cd["witness_construction"]
    # L0 consists of all commitment equations, the twelve scalar field rows,
    # one constant coordinate and every reserved/first-layer padding zero.
    front = {x["matrix_id"]: x for x in registry["roles"] if x["matrix_id"].startswith("frontend_")}
    source_specs = [(front["frontend_state"], 18), (front["frontend_carrier"], 1), (front["frontend_auxiliary"], 1)]
    ring_products = sum(x["rows"] * x["columns"] * uses for x, uses in source_specs)
    forward_ring_adds = sum(x["rows"] * (x["columns"] - 1) * uses for x, uses in source_specs)
    transpose_ring_adds = sum(x["columns"] * (x["rows"] - 1) * uses for x, uses in source_specs)
    committed_coeffs = sum(x["columns"] * d * uses for x, uses in source_specs)
    fixed_copies = 1 + handoff["fixed_zero_coordinates_count"] + layers[0]["padding"]
    initial = {
        "input_coefficients_after_backend_padding": layers[0]["padded_source_coefficients"],
        "rows_after_backend_padding": handoff["linear_rows_after_backend_padding"],
        "Apply_reference": {
            "commitment_Rq_multiplications": ring_products,
            "commitment_Rq_additions": forward_ring_adds,
            "field_rows_K_by_Fq_multiplications": 3 * capacity,
            "field_rows_K_additions": 3 * (capacity - 1),
            "field_output_base_coefficient_copies": 12,
            "constant_and_zero_coordinate_copies": fixed_copies
        },
        "TransposeApply_reference_per_call": {
            "commitment_Rq_multiplications": ring_products,
            "commitment_Rq_additions": transpose_ring_adds,
            "field_rows_Fq_multiplications": 12 * capacity,
            "Fq_accumulations_zero_initialized": committed_coeffs + 12 * capacity + fixed_copies,
            "output_Fq_zero_initializations": layers[0]["padded_source_coefficients"],
            "model": "Compute the 20 transposed ring maps into local buffers and add them to a zero-initialized coefficient output. Add all twelve scalar field rows with a full fixed-length loop, then add constant/padding row contributions. Stored zeros are not skipped."
        },
        "public_transpose_calls_each_party": tau,
        "field_row_materialization_K_to_Fq_coordinate_copies_once_each_party": 12 * capacity,
        "scope": "Field transpose-vector construction is counted separately in field_front_end. The source-row operator uses those vectors; it introduces no extra commitment key. Apply is a reference operator cost, not an extra mandatory prover call."
    }
    op["initial_relation_operator"] = initial
    op["lattice_layers"][0]["public_aggregation_once_each_party"]["source_relation_transpose_cost"] = initial["TransposeApply_reference_per_call"]
    for row in op["lattice_layers"][1:]:
        previous = op["lattice_layers"][row["level"] - 1]
        row["public_aggregation_once_each_party"]["source_relation_transpose_cost"] = {
            "source_level": previous["level"],
            "counts": previous["child_relation_exact_linear_circuit_counts"],
            "applications": tau,
            "scope": "Use the previous child relation's fixed linear circuit and its explicitly counted reverse circuit."
        }
