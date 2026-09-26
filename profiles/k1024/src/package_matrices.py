"""Losslessly archive complete compiler artifacts, with decompression checks."""
from pathlib import Path
import lzma,hashlib,time,json
from cf_profile import ROOT,dump

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def run():
    inp=ROOT/'artifacts/compiler';out=ROOT/'compiler_compressed';out.mkdir(exist_ok=True)
    records=[]
    for p in sorted(inp.iterdir()):
        if not p.is_file():continue
        dest=out/(p.name+'.xz');t=time.perf_counter()
        filters=[]
        if p.suffix=='.ptr':filters=[{'id':lzma.FILTER_DELTA,'dist':4}]
        elif p.suffix=='.ent':filters=[{'id':lzma.FILTER_DELTA,'dist':16}]
        filters.append({'id':lzma.FILTER_LZMA2,'preset':1})
        h=hashlib.sha256()
        with p.open('rb') as f,lzma.open(dest,'wb',filters=filters) as g:
            for b in iter(lambda:f.read(1<<20),b''):h.update(b);g.write(b)
        hh=hashlib.sha256();n=0
        with lzma.open(dest,'rb') as g:
            for b in iter(lambda:g.read(1<<20),b''):hh.update(b);n+=len(b)
        assert hh.digest()==h.digest() and n==p.stat().st_size
        r=dict(file=p.name,raw_bytes=n,raw_sha256=h.hexdigest(),compressed_bytes=dest.stat().st_size,
            compressed_sha256=digest(dest),full_decompression_sha256_verified=True,seconds=time.perf_counter()-t)
        records.append(r);print(json.dumps(r),flush=True)
    dump(out/'MANIFEST.json',dict(status='ALL_FULL_DECOMPRESSIONS_VERIFIED',files=records))
    dump(ROOT/'evidence/artifact_compression.json',dict(status='PASS',raw_bytes=sum(r['raw_bytes'] for r in records),
          compressed_bytes=sum(r['compressed_bytes'] for r in records),file_count=len(records),
          full_decompression_checks=len(records)))
if __name__=='__main__':run()
