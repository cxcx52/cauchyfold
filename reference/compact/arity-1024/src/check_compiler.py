"""Complete independent template comparison; vectorized repeated row families.
Every stored pointer and sparse entry is checked. No sampling is used.
"""
from pathlib import Path
import struct,json,time
import numpy as np
from profile import Q,ROOT,dump
from check_templates import row_templates,PACK

def run(root,k):
    start=time.perf_counter();root=Path(root)
    p=[np.memmap(root/(n+'.ptr'),dtype='<u4',mode='r') for n in 'ABC']
    e=[np.memmap(root/(n+'.ent'),dtype='<u4',mode='r').reshape(-1,2) for n in 'ABC']
    V=77*k+182;B=192*V;nbo=2*B;one=nbo;ng=4*V
    def eq(a,b):
        if not np.array_equal(a,b):raise AssertionError('independent full template mismatch')
    chunk=1<<18
    for lo in range(0,nbo,chunk):
        hi=min(nbo,lo+chunk);x=np.arange(lo,hi,dtype=np.uint32)
        eq(p[0][lo:hi],x);eq(p[1][lo:hi],2*x);eq(p[2][lo:hi],np.zeros_like(x))
        eq(e[0][lo:hi,0],x);eq(e[0][lo:hi,1],np.zeros_like(x))
        b=e[1][2*lo:2*hi].reshape(-1,2,2)
        eq(b[:,0,0],x);eq(b[:,0,1],np.zeros_like(x))
        eq(b[:,1,0],np.full_like(x,one));eq(b[:,1,1],np.full_like(x,2**31))
    print('Boolean templates checked',time.perf_counter()-start,flush=True)
    assert tuple(int(a[nbo]) for a in p)==(nbo,2*nbo,0)
    # A generic coefficient-comparison block has 53 rows. 0=source bit,
    # 1=prefix helper, 2=the globally fixed one coordinate.
    rows=[]
    for bit in reversed(range(48)):
        nxt=(2,0,0) if bit==47 else (1,bit+1,0)
        if (Q>>bit)&1:rows.append(([nxt],[(0,bit,0)],[(1,bit,0)]))
        else:
            rows.append(([nxt],[(2,0,0),(0,bit,2**31)],[(1,bit,0)]))
            rows.append(([nxt],[(0,bit,0)],[]))
    rows.append(([(2,0,0)],[(1,0,0)],[]));assert len(rows)==53
    ptr=[];desc=[]
    for a in range(3):
        local=[0];flat=[]
        for row in rows:flat+=row[a];local.append(len(flat))
        ptr.append(np.array(local,dtype=np.uint64));desc.append(flat)
    bases=[nbo,2*nbo,0]
    for lo in range(0,ng,4096):
        hi=min(ng,lo+4096);g=np.arange(lo,hi,dtype=np.uint64)
        for a in range(3):
            nnz=len(desc[a]);rp=(bases[a]+g[:,None]*nnz+ptr[a][None,:-1]).reshape(-1)
            eq(p[a][nbo+53*lo:nbo+53*hi],rp)
            expected=np.empty((hi-lo,nnz,2),dtype=np.uint32)
            for j,(kind,offset,key) in enumerate(desc[a]):
                expected[:,j,0]=one if kind==2 else 48*g+offset+(B if kind==1 else 0)
                expected[:,j,1]=key
            eq(e[a][bases[a]+lo*nnz:bases[a]+hi*nnz],expected.reshape(-1,2))
    print('Canonical templates checked',time.perf_counter()-start,flush=True)
    nr=nbo+53*ng
    for a in range(3):assert int(p[a][nr])==bases[a]+ng*len(desc[a])
    # Independent vectorized semantic templates. Avoid constructing tens of
    # millions of Python tuple objects merely to compare a canonical CSR.
    offsets=[int(p[a][nr]) for a in range(3)]
    onecode=np.array([one,0],dtype=np.uint32)
    units=np.array([64*t+b for t in range(4) for b in range(48)],dtype=np.uint32)
    ds=np.arange(192,dtype=np.uint32)
    def batch(mats):
        nonlocal nr
        nrows=mats[0].shape[0]
        for a,expected in enumerate(mats):
            assert expected.shape[0]==nrows and expected.shape[-1]==2
            width=expected.shape[1]
            eq(p[a][nr:nr+nrows+1],offsets[a]+width*np.arange(nrows+1,dtype=np.uint64))
            eq(e[a][offsets[a]:offsets[a]+nrows*width],expected.reshape(-1,2))
            offsets[a]+=nrows*width
        nr+=nrows
    def linear(bb):
        nrows=bb.shape[0]
        batch([np.broadcast_to(onecode,(nrows,1,2)),bb,np.empty((nrows,0,2),dtype=np.uint32)])
    def decoded(starts,keys=units):
        starts=np.asarray(starts,dtype=np.uint32)
        arr=np.empty((len(starts),192,2),dtype=np.uint32)
        arr[:,:,0]=starts[:,None]+ds;arr[:,:,1]=keys
        return arr
    # Public coordinates: one complete affine form per public K coordinate.
    idx=np.arange(5*(k+2),dtype=np.uint32)
    starts=192*(73*(idx//5)+idx%5)
    bb=np.empty((len(idx),193,2),dtype=np.uint32);bb[:,:192]=decoded(starts)
    bb[:,192,0]=one;bb[:,192,1]=2**31+2**28+idx*256;linear(bb)
    # Fresh u=1 and four residual-zero equations.
    for st in range(1,k+1):
        bb=np.empty((1,193,2),dtype=np.uint32);bb[:,:192]=decoded([192*73*st]);bb[0,192]=[one,2**31];linear(bb)
        linear(decoded(192*(73*st+69+np.arange(4,dtype=np.uint32))))
    # Fresh coordinates must lie in the base field: t=1,2,3 separately.
    for lo in range(0,k*69*3,4096):
        idx=np.arange(lo,min(k*69*3,lo+4096),dtype=np.uint32)
        st=1+idx//207;j=(idx%207)//3;t=1+idx%3
        bb=np.empty((len(idx),48,2),dtype=np.uint32)
        bb[:,:,0]=(192*(73*st+j)+48*t)[:,None]+np.arange(48,dtype=np.uint32)
        bb[:,:,1]=(64*t)[:,None]+np.arange(48,dtype=np.uint32);linear(bb)
    output=192*73*(k+1);carrier=192*73*(k+2);aux=carrier+192*4*k
    indices=np.arange(k,dtype=np.uint32)
    # Folded semantic z: output minus accumulator minus weighted sources.
    weightkeys=2**31+2*2**28+256*indices[:,None]+units[None,:]
    for j in range(69):
        bb=np.concatenate([decoded([output+192*j]),decoded([192*j],units+2**31),
             decoded(192*(73*(indices+1)+j),weightkeys)],axis=0).reshape(1,-1,2)
        linear(bb)
    # Folded residual: squared source weights and all carrier coefficients.
    squarekeys=2**31+3*2**28+256*indices[:,None]+units[None,:]
    carrierkeys=2**31+4*2**28+256*indices[:,None]+units[None,:]
    for j in range(4):
        bb=np.concatenate([decoded([output+192*(69+j)]),decoded([192*(69+j)],units+2**31),
           decoded(192*(73*(indices+1)+69+j),squarekeys),
           decoded(carrier+192*(4*indices+j),carrierkeys)],axis=0).reshape(1,-1,2)
        linear(bb)
    for j in range(4):
        for l in range(9):
            aa,bb=(5+16*j+2*l,6+16*j+2*l) if l<8 else (0,j+1)
            batch([decoded([output+192*aa]),decoded([output+192*bb]),decoded([aux+192*(9*j+l)])])
    for j in range(4):
        bs=[decoded([aux+192*(9*j+l)],units+(2**31 if l==8 else 0)) for l in range(9)]
        bs.append(decoded([output+192*(69+j)],units+2**31));linear(np.concatenate(bs,axis=0).reshape(1,-1,2))
    assert all(len(x)==nr+1 for x in p)
    assert all(int(p[a][-1])==len(e[a]) for a in range(3))
    result=dict(status='PASS',k=k,rows=nr,entries=sum(len(x) for x in e),
       every_sparse_entry_compared=True,every_row_pointer_compared=True,
       numeric_witness_used=False,method='independent Python/Numpy row templates, complete vectorized comparison',seconds=time.perf_counter()-start)
    dump(ROOT/'evidence/compiler-checks.json',result);return result
if __name__=='__main__': print(json.dumps(run(ROOT/'artifacts/compiler',1024),indent=2))
