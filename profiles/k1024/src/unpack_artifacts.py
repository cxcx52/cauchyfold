"""Restore full compressed compiler artifacts and check both hash layers."""
from pathlib import Path
import lzma,hashlib,json
from cf_profile import ROOT

def unpack():
    folder=ROOT/'compiler_compressed';m=json.loads((folder/'MANIFEST.json').read_text())
    out=ROOT/'artifacts/compiler';out.mkdir(parents=True,exist_ok=True)
    for r in m['files']:
        name=r['file']
        if name in ('.','..') or Path(name).name!=name:raise ValueError('unsafe artifact name')
        compressed=folder/(name+'.xz');h=hashlib.sha256()
        with compressed.open('rb') as f:
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
        if h.hexdigest()!=r['compressed_sha256']:raise ValueError('compressed artifact hash mismatch')
        dest=out/name;tmp=out/(name+'.tmp');h=hashlib.sha256();n=0
        try:
            with lzma.open(compressed,'rb') as f,tmp.open('wb') as g:
                for b in iter(lambda:f.read(1<<20),b''):
                    n+=len(b)
                    if n>r['raw_bytes']:raise ValueError('decompression size exceeded')
                    h.update(b);g.write(b)
            if n!=r['raw_bytes'] or h.hexdigest()!=r['raw_sha256']:raise ValueError('raw artifact hash mismatch')
            tmp.replace(dest)
        finally:
            if tmp.exists():tmp.unlink()


if __name__=="__main__":unpack()
