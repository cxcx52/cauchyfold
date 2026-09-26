"""Losslessly archive complete compiler artifacts, with decompression checks."""
from pathlib import Path
import lzma,hashlib,json
from profile import ROOT,dump

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def archive_name(name):
    names={
        'A.ent':'matrix-a-entries.bin.xz','A.ptr':'matrix-a-row-pointers.bin.xz',
        'B.ent':'matrix-b-entries.bin.xz','B.ptr':'matrix-b-row-pointers.bin.xz',
        'C.ent':'matrix-c-entries.bin.xz','C.ptr':'matrix-c-row-pointers.bin.xz',
        'compiler.json':'compiler-metadata.json.xz','evaluation_codes.u8':'evaluation-codes.u8.xz',
        'evaluation_dictionary.u64':'evaluation-dictionary.u64.xz','values.u64':'field-values.u64.xz',
        'verification_second.json':'verification-second.json.xz','witness_second.u8':'witness-second.u8.xz',
    }
    return names.get(name,name+'.xz')

def run():
    inp=ROOT/'artifacts/compiler';out=ROOT/'compiler-data';out.mkdir(exist_ok=True)
    records=[]
    for p in sorted(inp.iterdir()):
        if not p.is_file():continue
        dest=out/archive_name(p.name)
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
        r=dict(file=p.name,archive=dest.name,raw_bytes=n,raw_sha256=h.hexdigest(),compressed_bytes=dest.stat().st_size,
            compressed_sha256=digest(dest),full_decompression_sha256_verified=True)
        records.append(r);print(json.dumps(r),flush=True)
    dump(out/'manifest.json',dict(status='ALL_FULL_DECOMPRESSIONS_VERIFIED',files=records))
    dump(ROOT/'evidence/compiler-data-checks.json',dict(status='PASS',raw_bytes=sum(r['raw_bytes'] for r in records),
          compressed_bytes=sum(r['compressed_bytes'] for r in records),file_count=len(records),
          full_decompression_checks=len(records)))
if __name__=='__main__':run()
