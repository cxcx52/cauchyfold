"""Exact parameter accounting for the unchanged CauchyFold message grammar."""
from pathlib import Path
from fractions import Fraction as F
from math import isqrt, log2
from functools import lru_cache
import json
import sys
import hashlib
import layout
from norm_bounds import compiler_s0_formula, exact_max_digit_energy

sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent
Q = 2**48 - 59
D = 64
M = 5**64
PROJ = 384
SIGMA2 = F(38400, 4121)
TOP = 82
MU = 128
RP = RC = 160
PIN = '53da5982597709ba0fdf94ea37a84d822310fd84'

def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8'))

def frac(x):
    x = F(x)
    return {'numerator': str(x.numerator), 'denominator': str(x.denominator)}

def cd(a, b):
    return (a+b-1)//b

def cl2(n):
    return (n-1).bit_length()

def csqrt(x):
    x = F(x)
    n = isqrt(x.numerator // x.denominator)
    return n + int(n*n*x.denominator < x.numerator)

def ceil_surd(a, b, denominator):
    n = cd(a+isqrt(b), denominator)
    if denominator*n < a or (denominator*n-a)**2 < b:
        n += 1
    assert denominator*n >= a and (denominator*n-a)**2 >= b
    assert denominator*(n-1) < a or (denominator*(n-1)-a)**2 < b
    return n

@lru_cache(None)
def energy(radix):
    return exact_max_digit_energy((Q-1)//2, radix)[0]

def rice(n, T):
    by, a, bits = layout.rice(n, T)
    return {'n': n, 'T': T, 'parameter': a, 'bits': bits, 'bytes': by}

@lru_cache(None)
def seed(N, S):
    R = 2*PROJ*N
    T = PROJ*S
    w = cl2((R+1)*4*Q*(T+2))
    old_b = 6*w+2*cl2(R)+450+cl2(cl2(R))+3
    old_h = cl2(cd(R, old_b))
    seed_bits_upper = old_b+old_h*(3*old_b-1)
    choices = []
    for h in range(1, cl2(R)+1):
        c = 2**h-1
        b = max(6*w+450-2+cl2(27*h*c*c), cd(R, 2**h))
        if b+h*(3*b-1) > seed_bits_upper:
            continue
        if h != cl2(cd(R, b)):
            continue
        delta = F(2, 3*c*2**150)
        error = c*delta + F(2**(6*w)*h, 2**b)/delta**2
        assert error <= F(1, 2**150)
        bits = b+h*(3*b-1)
        choices.append((bits, b, h, delta, error))
    bits, b, h, delta, error = min(choices)
    assert F(1, 2*(T+1)) > error
    return {'N': N, 'S': S, 'R': R, 'T': T, 'w': w, 'b': b, 'h': h,
            'bits': bits, 'bytes': cd(bits, 8), 'delta': frac(delta), 'error': frac(error),
            'prefix_hashes': cd(R, b)-1,
            'choice': 'minimum seed bits over admissible integer depths using the exact transport bound'}

def bounds(raw, S, s, rho, a):
    n = cd(raw, 64*s)
    N = 64*n
    ell = cd(48, rho.bit_length()-1)
    b = rho//2
    G = 256*S-1
    bt = ell*a*s
    bh = ell*3*s*(s+1)//2
    E = energy(rho)
    Et = 64*a*s*E
    Eh = 64*3*s*(s+1)//2*E
    S1 = N*b*b + ceil_surd(G+N*b*b, 4*b*b*G*N, rho*rho) + Et+Eh
    raw1 = 128*n+64*(bt+bh)
    ba = csqrt(27*TOP**2*(1+rho*rho)*SIGMA2*S1)
    bx = csqrt(4*SIGMA2*S1)
    return dict(next_raw=raw1, next_S=S1, beta_A=ba, beta_aux=bx,
                digits=ell, bt_columns=bt, bh_columns=bh, digit_energy=E, E_t=Et, E_h=Eh)

def build(k, path=None, ranks=None):
    baseline = json.loads((ROOT/'schedules'/f'arity-{k}.json').read_text(encoding='utf-8'))
    large = k == 1024
    if path is None:
        path = baseline['path']
    if ranks is None:
        ranks_path = ROOT/'parameters.json'
        ranks = json.loads(ranks_path.read_text(encoding='utf-8'))
    a = ranks['main']
    af = ranks['frontend']
    ax = ranks['auxiliary']
    ap = ranks['pivot']
    f = layout.front(k, split_aux=not large, rank=af)
    f['initial_linear_rows']=(k+3+len(f['auxiliary_chunks']))*af*D+13
    f['wrapper_p_bytes']=(2+len(f['auxiliary_chunks']))*af*384+96*f['field_rounds']+72
    P = f['wrapper_p_bytes']
    V = f['wrapper_v_bytes']
    raw = f['capacity']
    S = compiler_s0_formula(k)
    initial_S = S
    lr = f['initial_linear_rows']
    roles = []
    layers = []
    def reg(name, rows, cols, beta, formula):
        assert rows > 0 and cols > 0 and 0 < beta < Q
        roles.append({'matrix_id': name, 'q': Q, 'd': D, 'rows': rows, 'columns': cols,
                      'beta': beta, 'norm': 'coefficient_l2', 'beta_formula': formula,
                      'expanded_sis': {'n': D*rows, 'm': D*cols, 'norm': 2, 'length_bound': beta},
                      'estimator_commit': PIN})
    bf = csqrt(4*SIGMA2*S)
    reg('A_st', af, 219, bf, 'ceil(2*sqrt(sigma_squared*S0))')
    reg('A_H', af, 12*k, bf, 'ceil(2*sqrt(sigma_squared*S0))')
    for j, cols in enumerate(f['auxiliary_chunks']):
        reg('A_aux' if len(f['auxiliary_chunks']) == 1 else f'A_aux{j}', af, cols, bf,
            'ceil(2*sqrt(sigma_squared*S0))')
    for i, (s, rho) in enumerate(path):
        n = cd(raw, D*s)
        N = D*s*n
        pad = N-raw
        aug = lr+pad+PROJ
        degree = cd(aug, 4)-1
        sd = seed(N, S)
        pc = rice(PROJ, PROJ*S)
        assert Q*Q > 176**2*SIGMA2*S
        assert F(4121, 100)*SIGMA2 >= PROJ
        vi = sd['bytes']+42+24*s
        G = cd(256*M*S, M-1)-1 if rho is None else 256*S-1
        rec = dict(i=i, s=s, rho=rho, n=n, N=N, raw=raw, S=S, G=G, padding=pad,
                   linear_rows=lr+pad, augmented_rows=aug, aggregation_degree=degree,
                   seed=sd, projection_codec=pc, terminal=rho is None)
        if rho is None:
            assert i == len(path)-1
            ba = csqrt(27*TOP**2*G)
            zc = rice(D*n, G)
            reg(f'A_{i}', a, n, ba, 'ceil(sqrt(27*T_op^2*G_L))')
            reg('B_pivot', ap, a*16, csqrt(8**2*D*a*16), 'ceil(8*sqrt(d*a_L*16))')
            pi = (s-1)*a*384+ap*384+pc['bytes']+3*s*(s+1)//2*384-18+zc['bytes']+2
            rec.update(beta_A=ba, terminal_codec=zc)
        else:
            nxt = bounds(raw, S, s, rho, a)
            reg(f'A_{i}', a, n, nxt['beta_A'], 'ceil(sqrt(27*T_op^2*(1+rho^2)*sigma_squared*S_child))')
            reg(f'B_{i}', ax, nxt['bt_columns'], nxt['beta_aux'], 'ceil(2*sqrt(sigma_squared*S_child))')
            reg(f'D_{i}', ax, nxt['bh_columns'], nxt['beta_aux'], 'ceil(2*sqrt(sigma_squared*S_child))')
            pi = 2*ax*384+pc['bytes']+2
            rec.update(nxt)
            raw, S, lr = nxt['next_raw'], nxt['next_S'], 64*(2*ax+a+3)+3
        rec.update(p_bytes=pi, v_bytes=vi)
        P += pi
        V += vi
        layers.append(rec)
    q4 = Q**4
    ell = f['field_rounds']
    field = 1-(1-F(1, q4))**ell*(1-F(3, q4))**ell
    cauchy = F(2*k, q4-k)
    epsilon = F(1, 2**192)+F(1, 2**150)
    projection = len(layers)*(1-(1-epsilon)**RP)
    aggregation = sum((F(1, Q**3)+(1-F(1, Q**3))*F(x['aggregation_degree'], q4) for x in layers), F(0))
    coordinate = 3*RC*(F(sum(x['s'] for x in layers)-1, M)+F(1, M-1))
    terms = dict(field=field, cauchy=cauchy, projection=projection,
                 aggregation=aggregation, coordinate=coordinate)
    stat = sum(terms.values(), F(0))
    assert stat < F(1, 2**130)
    exhaustion = F(0)
    for x in layers:
        eta = F(int(x['seed']['error']['numerator']), int(x['seed']['error']['denominator']))
        pp_fail = F(1, 2)-F(1, 2*(PROJ*x['S']+1))+eta
        ex = MU*x['S']*(F(M, M-1) if x['terminal'] else 1)
        cc_fail = F(ex, x['G']+1)
        assert pp_fail < F(1, 2) and cc_fail <= F(1, 2)
        exhaustion += pp_fail**RP+cc_fail**RC
    extra = sum(x['seed']['bytes']+24*x['s']+2 for x in layers)
    stats = {'terms': {n: frac(v) for n, v in terms.items()}, 'total': frac(stat),
             'negative_log2_display': log2(stat.denominator)-log2(stat.numerator),
             'less_than_2neg130': True, 'kind': 'statistical_error_bound',
             'field_expression': '1-(1-q^-4)^ell_F*(1-3*q^-4)^ell_F',
             'projection_expression': 'layers*(1-(1-(2^-192+2^-150))^160)'}
    out = dict(k=k, q=Q, d=D, front=f, used=f['used'], S0=initial_S,
               field_rounds=ell, field_rows=f['field_rows'], path=path, layers=layers, roles=roles,
               main_rank=a, front_rank=af, auxiliary_rank=ax, pivot_rank=ap,
               projection_rows=PROJ, sigma_squared=frac(SIGMA2), T_op=TOP, mu=MU,
               P_bytes=P, V_bytes=V, total_bytes=P+V,
               max_accepted_bytes=P+V+159*extra,
               honest_expected_bytes_upper=P+V+extra,
               fresh_commitment_bytes=k*af*384, all_input_commitment_bytes=(k+1)*af*384,
               crs_bytes=sum(384*x['rows']*x['columns'] for x in roles),
               projection_trits=sum(PROJ*x['N'] for x in layers),
               statistical_security=stats,
               completeness={'kind': 'honest_retry_exhaustion_bound', 'total': frac(exhaustion),
                             'simple_upper_bound': frac(F(2*len(layers), 2**160))},
               selection='retained block/radix schedule; common matrix ranks screened with the pinned official estimator after norm propagation; no global minimum claim',
               old_total_bytes=baseline['previous_total_bytes'],
               old_S0=baseline['previous_S0'])
    return out

def main():
    profiles = []
    inputs = []
    for k in (2, 4, 8, 16, 32, 1024):
        x = build(k)
        dump(ROOT/'artifacts'/f'arity-{k}.json', x)
        profiles.append({n: x[n] for n in ('k', 'S0', 'P_bytes', 'V_bytes', 'total_bytes', 'max_accepted_bytes', 'old_total_bytes')})
        for role in x['roles']:
            inputs.append(dict(arity=k, **role))
    dump(ROOT/'artifacts'/'summary.json', profiles)
    dump(ROOT/'artifacts'/'estimator-inputs.json', {'pin': PIN, 'roles': inputs})
    print(json.dumps(profiles, indent=2))

if __name__ == '__main__':
    main()
