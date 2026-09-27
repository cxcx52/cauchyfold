"""Verify supplied results; optionally rerun the exhaustive five-point search."""
from pathlib import Path
import argparse,json
from validate_frontend import run as validate_front
from verify import verify
from search import exact_search

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--search',action='store_true',help='rerun exhaustive restricted-grid searches for the five reported arities')
    args=p.parse_args();root=Path(__file__).parent/'results';root.mkdir(exist_ok=True)
    if args.search:
        for k in (2,4,8,16,32):
            r=exact_search(k)
            (root/f'arity-{k}.json').write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    f=validate_front();(root/'frontend-validation.json').write_bytes((json.dumps(f,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    v=verify();(root/'checks.json').write_bytes((json.dumps(v,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(v,indent=2))
