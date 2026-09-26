"""Independent codec ledger, shape and conservative whole-grid error checks."""
from pathlib import Path
from fractions import Fraction
from math import isqrt
import json
from parameters import *
from codec import NormCodec

ROOT=Path(__file__).parent

def verify():
    baseline_result=baseline()
    restored=(baseline_result['total_bytes']+10286694-6*42+(31104-10389)+(122112-33613))
    assert restored==10683813
    # A single safe error bound for every accepted cost-search state/path.
    max_sum_blocks=5*10+32
    max_deg_sum=28040
    worst=(Fraction(84,Q**4)+Fraction(64,Q**4-32)
           +960*(Fraction(48,47)*(Fraction(7,8)+Fraction(1,2**1000)))**864
           +Fraction(6,Q**3)+Fraction(max_deg_sum,Q**4)
           +480*(Fraction(max_sum_blocks-1,CHALLENGE_SIZE)+Fraction(1,CHALLENGE_SIZE-1)))
    assert worst<Fraction(1,2**130)
    codec_cases=0;reports=[]
    for k in (2,4,8,16,32):
        r=json.loads((ROOT/'results'/f'arity-{k}.json').read_text())
        f=r['front'];p=f['wrapper_p_bytes'];v=f['wrapper_v_bytes']
        for layer in r['layers']:
            s,n,S,G=layer['s'],layer['n'],layer['S'],layer['G']
            cp=NormCodec.rice_optimized(864,864*S)
            assert cp.nbytes==layer['projection_codec_bytes']
            p+=cp.nbytes+2;v+=layer['seed']['bytes']+42+24*s
            codecs=[cp]
            if layer['terminal']:
                cz=NormCodec.rice_optimized(64*n,G)
                assert cz.nbytes==layer['terminal_codec_bytes']
                p+=(s-1)*24*384+4*384+3*s*(s+1)//2*384-18+cz.nbytes
                codecs.append(cz)
                assert G==256*S+1
            else:
                p+=2*16*384
                raw1,S1,bt,bh,ba,baux=child(layer['N_raw'],S,s,layer['rho'])
                assert raw1==layer['next_raw'] and S1==layer['next_S']
            for codec in codecs:
                n,T=codec.n,codec.T
                a=isqrt(T//n)
                for vec in [[0]*n,[a if j%2 else -a for j in range(n)],[isqrt(T)]+[0]*(n-1)]:
                    wire=codec.encode(vec)
                    assert len(wire)==codec.nbytes and codec.decode(wire)==vec
                    assert codec.encode(codec.decode(wire))==wire
                    codec_cases+=1
        assert (p,v)==(r['p_bytes'],r['v_bytes']) and p+v==r['total_bytes']
        assert r['all_roles_reference_dominated'] and r['statistical_error_lt_2neg130']
        for role in r['roles']:
            assert role['b']<=role['reference_b'] and role['beta']<=role['reference_beta']
        reports.append(dict(k=k,bytes=p+v,P=p,V=v,all_roles_reference_dominated=True))
    # Rice minimizing k via exact finite differences, checked against enumeration.
    rice_checks=0
    for n in range(1,50):
        for root in range(1000):
            j=1+(root//(2*n+1)).bit_length()
            assert (n*(j+1)+(root>>(j-1)),j)==min((n*(i+1)+(root>>(i-1)),i) for i in range(1,20))
            rice_checks+=1
    return dict(baseline_original_bytes_restored=restored,
                whole_restricted_grid_statistical_bound_lt_2neg130=True,
                codec_roundtrip_cases=codec_cases,closed_form_rice_optimum_test_cases=rice_checks,
                profile_ledger_checks=reports,
                lattice_estimator_rerun=False,full_interactive_proof_files_generated=False,
                full_security_formalization=False)

if __name__=='__main__':
    r=verify();(ROOT/'results'/'verification.json').write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode('utf-8'));print(json.dumps(r,indent=2))
