"""Exact matched-layout counts, generic cubic message compression, and sensitivity."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from field_arithmetic import Q, em, ea, es, ZERO
import parameter_model as model


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def put(path, value):
    model.dump(path, value)


def compress(folder, target):
    meta = read(folder/'field.json')
    raw = (folder/'field.bin').read_bytes()
    assert len(raw) % 24 == 0
    elements = [tuple(int.from_bytes(raw[i+j:i+j+6], 'little') for j in range(0, 24, 6))
                for i in range(0, len(raw), 24)]
    g, ell = meta['batching_variables'], meta['rounds']
    retained = elements[:g]
    claim = ZERO
    for round_index in range(ell):
        offset = g+5*round_index
        original = elements[offset:offset+4]
        tau = elements[offset+4]
        g1, g2, g3 = original[1:]
        twice_g0 = es(es(es(claim, g1), g2), g3)
        g0 = tuple(v*pow(2, -1, Q) % Q for v in twice_g0)
        assert g0 == original[0]
        claim = ZERO
        for coefficient in reversed([g0, g1, g2, g3]):
            claim = ea(em(claim, tau), coefficient)
        retained.extend([g1, g2, g3, tau])
    retained.extend(elements[g+5*ell:])
    encoded = b''.join(x.to_bytes(6, 'little') for v in retained for x in v)
    target.write_bytes(encoded)
    assert len(encoded) == len(raw)-24*ell
    return dict(rounds=ell, all_polynomials_reconstructed_exactly=True,
                original_bytes=len(raw), compressed_bytes=len(encoded), saved_bytes=24*ell,
                scope='Exact re-encoding of the stored field transcript; original terminal verification is preserved')


def profile(carrier, coefficients):
    k = 1024
    directory = ROOT/'results/arity-1024' if carrier else ROOT.parent/'direct/results/arity-1024'
    comp = read(directory/'compiler.json')
    terms, groups, used = comp['terms'], comp['groups'], comp['columns']
    ell, g = (terms-1).bit_length(), (groups-1).bit_length()
    V = 73*(k+2)+(4*k if carrier else 0)
    helpers = 48*V
    f = dict(k=k, used=used, capacity=used, reserved_zeros=0,
             auxiliary_private_bits=helpers, auxiliary_columns=(helpers+63)//64,
             auxiliary_padding=(-helpers) % 64, auxiliary_chunks=[(helpers+63)//64],
             field_rows=terms, original_constraint_groups=groups,
             field_rounds=ell, field_padded_rows=1 << ell, batching_variables=g,
             wrapper_v_bytes=24*(1+g+ell), state_columns=219,
             carrier_columns=12*k if carrier else 0, canonical_K_values=V,
             with_carrier=carrier, round_coefficients=coefficients)
    x = model.build(k, front_override=f, S0_override=comp['S0'])
    x['encoding']='specialized canonical comparator; grouped constraints; three-coefficient degree-three messages'
    x['comparison_status']='Exact retained-schedule candidate calculation; compiler outputs are executed, not full backend proofs'
    x['statistical_security']['scope']='Derived subject to the imported backend extraction theorem and stated front-end composition'
    x['statistical_security']['field_expression']='1-(1-q^-4)^g*(1-3*q^-4)^ell'
    x['extractor_runtime']['front_end'] = {
        'scope': 'Symbolic expected-work bound, relative to the imported linear-chain theorem; see ../METHODS.md',
        'field': 'T_F <= 2*(H_F + T_0) + W_F',
        'node': ('T_node <= 2*(H_C + T_F) + W_C' if carrier else
                 'T_node <= H_C + T_F'),
        'backend_extractor_coefficient_after_expansion': 4 if carrier else 2,
        'H_F': 'Uniform conditional cost of a field continuation, excluding the linear-chain extractor',
        'W_F': 'Opening comparison, exact norm tests, affine insertion, decoding, and full relation checks',
        'H_C': 'Uniform conditional cost from the source checkpoint to fixed post-Cauchy commitments',
        'W_C': 'Pre-Cauchy source/carrier comparison and checking; used only by the carrier route',
        'speedup_claim': False,
    }
    return x


def main():
    results = ROOT.parent/'results'
    baseline = read(ROOT.parent/'baseline/profile.json')
    direct, carrier = profile(False, 3), profile(True, 3)
    for name, value in [('direct', direct), ('carrier', carrier)]:
        put(results/(name+'-profile.json'), value)
    entries = []
    for name, x in [('original_carrier_two_coefficients', baseline), ('grouped_carrier_three_coefficients', carrier),
                    ('grouped_direct_three_coefficients', direct)]:
        entries.append(dict(name=name, **{n:x[n] for n in ['used','S0','field_rows','field_rounds','P_bytes','V_bytes','total_bytes','crs_bytes']},
                            independently_sampled_matrices=len(x['roles'])))
    put(results/'comparison.json', entries)
    put(ROOT/'results/estimator-inputs.json', dict(pin=model.PIN, roles=[dict(arity=1024, **r) for r in carrier['roles']]))
    compression = {}
    for name, directory in [('direct-k4', ROOT.parent/'direct/results/arity-4'),
                            ('direct-k1024', ROOT.parent/'direct/results/arity-1024'),
                            ('carrier-k4', ROOT/'results/arity-4')]:
        compression[name] = compress(directory, results/(name+'-compressed-field.bin'))
    put(results/'compression-checks.json', compression)
    sensitivity = []
    k = 1024
    def dimensions(length):
        n = 5+8*length
        fd = (n-1)*k+8*(n+4)
        fc = fd+16*k
        md = 63*fd+4*k+10+n+4*k*(length+1)+8*(length+2)
        mc = 63*fc+4*k+10+n+4+4*(length+2)
        assert mc-md == 4*(k*(251-length)-length-1)
        return dict(dot_product_length=length,n=n,direct_terms=md,carrier_terms=mc,
                                carrier_minus_direct_terms=mc-md,direct_active=60*fd+1,carrier_active=60*fc+1,
                                direct_padded=1 << (md-1).bit_length(),carrier_padded=1 << (mc-1).bit_length())
    sensitivity=[dimensions(h) for h in (1,8,64,128,250,251,256,512,1024,4096)]
    boundary=[dimensions(h) for h in range(1,10001) if dimensions(h)['carrier_padded'] < dimensions(h)['direct_padded']]
    put(results/'relation-sensitivity.json', dict(scope='Derived layout formulas only; no new large relation compiled or screened', values=sensitivity,
        scanned_integer_dot_lengths=[1,10000], padded_advantage_cases=boundary,
        long_dot_length_term_ratio_limit={'numerator':520140,'denominator':524240}))
    print(json.dumps(entries, indent=2))


if __name__ == '__main__':
    main()
