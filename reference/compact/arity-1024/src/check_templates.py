"""Independent Python reconstruction of the manuscript's field row templates.
Compares EVERY row of the k=2 CSR fixture, not just a satisfying assignment.
"""
from __future__ import annotations
import mmap,struct,time,json,sys
from pathlib import Path
from profile import Q,ROOT,dump
PACK=struct.Struct('<II')

def key(kind=0,index=0,basis=0,bit=0,negative=False):
    return int(negative)*2**31+kind*2**28+index*256+basis*64+bit

def row_templates(k,cap=None,semantic_only=False):
    V=77*k+182;B=192*V;used=2*B+1;cap=cap or used;one=used-1
    H=192*73*(k+2);aux=H+192*4*k;out=192*73*(k+1)
    def sc(x,neg=False):return [(x,key(negative=neg))]
    def decode(start,neg=False,kind=0,index=0,comp=None):
        return [(start+48*t+b,key(kind,index,t,b,neg)) for t in range(4) if comp is None or t==comp for b in range(48)]
    def linear(b):return sc(one),b,[]
    if not semantic_only:
        for i in range(used-1):yield sc(i),sc(i)+sc(one,True),[]
        for vi in range(V):
            for t in range(4):
                base=B+192*vi+48*t
                for b in reversed(range(48)):
                    bit=192*vi+48*t+b;nxt=one if b==47 else base+b+1
                    if (Q>>b)&1:yield sc(nxt),sc(bit),sc(base+b)
                    else:
                        yield sc(nxt),sc(one)+sc(bit,True),sc(base+b)
                        yield sc(nxt),sc(bit),[]
                yield linear(sc(base))
    for state in range(k+2):
        for j in range(5):yield linear(decode(192*(73*state+j))+[(one,key(1,5*state+j,negative=True))])
    for state in range(1,k+1):
        yield linear(decode(192*73*state)+sc(one,True))
        for j in range(4):yield linear(decode(192*(73*state+69+j)))
    for state in range(1,k+1):
        for j in range(69):
            for t in (1,2,3):yield linear(decode(192*(73*state+j),comp=t))
    for j in range(69):
        b=decode(out+192*j)+decode(192*j,True)
        for i in range(k):b+=decode(192*(73*(i+1)+j),True,2,i)
        yield linear(b)
    for j in range(4):
        b=decode(out+192*(69+j))+decode(192*(69+j),True)
        for i in range(k):b+=decode(192*(73*(i+1)+69+j),True,3,i)
        for i in range(k):b+=decode(H+192*(4*i+j),True,4,i)
        yield linear(b)
    for j in range(4):
        for l in range(9):
            a,b=(5+16*j+2*l,6+16*j+2*l) if l<8 else (0,j+1)
            yield decode(out+192*a),decode(out+192*b),decode(aux+192*(9*j+l))
    for j in range(4):
        b=sum((decode(aux+192*(9*j+l),l==8) for l in range(9)),[])+decode(out+192*(69+j),True)
        yield linear(b)
    for i in range(used,cap):yield linear(sc(i))

def check(directory,k,cap=None):
    files=[];maps=[];ptrs=[];ents=[];t=time.perf_counter()
    try:
        for name in 'ABC':
            f=open(Path(directory)/(name+'.ptr'),'rb');files.append(f);m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);maps.append(m);ptrs.append(memoryview(m).cast('I'))
            f=open(Path(directory)/(name+'.ent'),'rb');files.append(f);m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);maps.append(m);ents.append(m)
        n=0
        for n,row in enumerate(row_templates(k,cap),1):
            for a,expected in enumerate(row):
                start,stop=ptrs[a][n-1],ptrs[a][n]
                if stop-start!=len(expected):raise AssertionError(('row length mismatch',n-1,a))
                raw=b''.join(PACK.pack(*x) for x in expected)
                if ents[a][start*8:stop*8]!=raw:raise AssertionError(('row contents mismatch',n-1,a))
        assert all(len(p)==n+1 for p in ptrs)
        return dict(status='PASS',k=k,rows=n,every_sparse_entry_compared=True,
                    seconds=time.perf_counter()-t,method='independent Python row-template generator versus saved C++ CSR')
    finally:
        for p in ptrs:p.release()
        for m in maps:m.close()
        for f in files:f.close()
if __name__=='__main__':
    directory=sys.argv[1];k=int(sys.argv[2]);cap=int(sys.argv[3]) if len(sys.argv)>3 else None
    result=check(directory,k,cap);dump(ROOT/'evidence'/f'template-checks-{k}.json',result);print(json.dumps(result,indent=2))
