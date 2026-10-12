"""Check saved dimensions, estimator coverage, and file digests."""
from pathlib import Path
from hashlib import sha256
from fractions import Fraction
import json
import sys

sys.set_int_max_str_digits(0)

ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))


def main():
    for name,count in [('direct',16),('carrier',17)]:
        p=read(ROOT/'results'/f'{name}-profile.json')
        e=read(ROOT/name/'results/estimator/results.json')
        assert len(p['roles'])==count
        assert p['total_bytes']==p['P_bytes']+p['V_bytes']
        assert e['counts']==dict(DONE=2*count,FAILED=0,PENDING=0,UNKNOWN_NONFINITE=0)
        assert e['estimator_commit']=='53da5982597709ba0fdf94ea37a84d822310fd84'
        for role in p['roles']:
            for model in ['classical','quantum']:
                entries=[v for v in e['role_results'] if v['matrix_id']==role['matrix_id'] and v['model']==model]
                assert len(entries)==1
                assert all(entries[0][key]==role[key] for key in ['q','d','rows','columns','beta'])
        for v in e['results']:
            base=ROOT if name=='carrier' else ROOT/'direct'
            assert sha256((base/v['raw_output']).read_bytes()).hexdigest()==v['raw_output_sha256']
        f=lambda x:Fraction(int(x['numerator']),int(x['denominator']))
        s=p['statistical_security']
        assert sum((f(x) for x in s['terms'].values()),Fraction(0))==f(s['total'])
    for name,v in read(ROOT/'results/compression-checks.json').items():
        assert v['all_polynomials_reconstructed_exactly']
        assert v['original_bytes']-v['compressed_bytes']==24*v['rounds']
    print('PASS dimensions, 66 estimator entries, exact statistical totals, and transcript compression')


if __name__=='__main__':main()
