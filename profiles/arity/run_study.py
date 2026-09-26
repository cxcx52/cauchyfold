"""Verify supplied results; optionally rerun the exhaustive five-point search."""
from pathlib import Path
import argparse,json
from front_validation import run as validate_front
from verify_results import verify
from exact_search import exact_search

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--search',action='store_true',help='rerun exhaustive restricted-grid searches for the five reported arities')
    args=p.parse_args();root=Path(__file__).parent/'results';root.mkdir(exist_ok=True)
    if args.search:
        for k in (2,4,8,16,32):
            r=exact_search(k)
            (root/f'k{k}_exact.json').write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    f=validate_front();(root/'front_validation.json').write_bytes((json.dumps(f,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    v=verify();(root/'verification.json').write_bytes((json.dumps(v,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(v,indent=2))
