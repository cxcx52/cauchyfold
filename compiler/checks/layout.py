"""Independent complete CSR templates and affine-embedding checks."""
from pathlib import Path
import json
import sys
import numpy as np
from templates import row_templates

ROOT=Path(__file__).resolve().parents[1]
Q=2**48-59;NEG=1<<31


def patterns(special):
    rows=[];one=(-1,0)
    def var(i,negative=False,power=0):return (i,(NEG if negative else 0)+power)
    def bit(i):rows.append(([var(i)],[var(i),(-1,NEG)],[]))
    def notbit(i):return [one,var(i,True)]
    for i in range(48):bit(i)
    if special:
        for i in range(48,54):bit(i)
        rows.append(([one],[var(48+j,power=j) for j in range(6)]+[var(j) for j in range(6,48)]+[(-1,NEG+j) for j in [1,3,5]],[]))
        rows.append((notbit(48),notbit(49),[var(54)]))
        for j in range(2,6):rows.append(([var(52+j)],notbit(48+j),[var(53+j)]))
        rows.append(([var(58)],[var(2)],[var(59)]))
        rows.append(([var(58)],[var(j) for j in [3,4,5]],[]))
        rows.append(([var(59)],[var(0),var(1)],[]))
    else:
        for j in reversed(range(48)):
            nxt=one if j==47 else var(48+j+1)
            rows.append(([nxt],[var(j)] if Q>>j&1 else notbit(j),[var(48+j)]))
            if not (Q>>j&1):rows.append(([nxt],[var(j)],[]))
        rows.append(([one],[var(48)],[]))
    return rows


def check(mode,k):
    directory=ROOT/'build'/f'{mode}-{k}'
    meta=json.loads((directory/'compiler.json').read_text());sp=mode=='special';stride=60 if sp else 96
    V=77*k+182;nc=4*V;free=84*k+728;one=stride*free
    groups=np.arange(nc,dtype=np.int64);v=groups//4;s=v//73;j=v%73;t=groups%4
    fixed=(s>=1)&(s<=k)&((j==0)|(j>=69)|(t>0))
    val=(j==0)&(t==0)
    indices=np.cumsum(~fixed)-1;indices[fixed]=-1
    ps=[np.memmap(directory/(name+'.ptr'),dtype='<u4',mode='r') for name in 'ABC']
    es=[np.memmap(directory/(name+'.ent'),dtype='<u4',mode='r').reshape(-1,2) for name in 'ABC']
    rows=patterns(sp);count=len(rows);assert count==(63 if sp else 101)
    bases=[]
    for a in range(3):
        lengths=[len(row[a]) for row in rows];ptr=np.r_[0,np.cumsum(lengths)].astype(np.uint64)
        flat=[e for row in rows for e in row[a]];nnz=len(flat);bases.append(free*nnz)
        for lo in range(0,free,2048):
            hi=min(free,lo+2048);g=np.arange(lo,hi,dtype=np.uint64)
            want=(g[:,None]*nnz+ptr[None,:-1]).ravel()
            assert np.array_equal(ps[a][lo*count:hi*count],want)
            cols=np.array([x[0] for x in flat]);keys=np.array([x[1] for x in flat],dtype=np.uint32)
            got=es[a][lo*nnz:hi*nnz].reshape(hi-lo,nnz,2)
            expected=np.where(cols[None,:]<0,one,g[:,None]*stride+cols[None,:])
            assert np.array_equal(got[:,:,0],expected)
            assert np.array_equal(got[:,:,1],np.broadcast_to(keys,got[:,:,1].shape))
        assert ps[a][free*count]==free*nnz
    nr=free*count
    for ri,row in enumerate(row_templates(k,semantic_only=True)):
        if ri<5*(k+2):
            state,coord=divmod(ri,5)
            if 1<=state<=k and coord==0:continue
        elif ri<5*(k+2)+212*k:continue
        for a,form in enumerate(row):
            arr=np.array(form,dtype=np.uint32).reshape(-1,2)
            col=arr[:,0].astype(np.int64);oldone=col==384*V
            g=np.minimum(col//48,nc-1);b=col%48
            fix=fixed[g]&~oldone
            keep=~fix|(val[g]&(b==0))
            selected=arr[keep].copy();cg=g[keep];cb=b[keep];oo=oldone[keep];ff=fix[keep]
            selected[:,0]=np.where(oo|ff,one,stride*indices[cg]+cb)
            begin,end=int(ps[a][nr]),int(ps[a][nr+1])
            assert end-begin==len(selected)
            assert np.array_equal(es[a][begin:end],selected),(mode,k,nr,a)
        nr+=1
    assert nr==meta['rows'] and all(len(p)==nr+1 for p in ps)
    w=np.fromfile(directory/'witness.u8',dtype=np.uint8)
    c=np.fromfile(directory/'fixed.u8',dtype=np.uint8)
    full=np.fromfile(directory/'physical.u8',dtype=np.uint8)
    ins=np.fromfile(directory/'insertion.u32',dtype='<u4')
    assert w[-1]==1 and len(ins)==one and len(np.unique(ins))==one
    assert np.all(c[ins]==0)
    reconstructed=c.copy();reconstructed[ins]=w[:-1]
    assert np.array_equal(reconstructed,full)
    # Test signed differences and cleared comparisons, not just Boolean vectors.
    rng=np.random.default_rng(20260928);x=rng.integers(-4,5,one,dtype=np.int64)
    y=rng.integers(-4,5,one,dtype=np.int64);delta=x-y
    assert np.sum(delta*delta)==np.sum(delta[np.argsort(ins)]**2)
    # Sparse insertion is injective; affine offset cancels before clearing.
    d1,d2=3,-2
    left=np.zeros(len(c),dtype=np.int64);left[ins]=x*d2-y*d1
    v1=c.astype(np.int64)*d1;v1[ins]+=x
    v2=c.astype(np.int64)*d2;v2[ins]+=y
    assert np.array_equal(v1*d2-v2*d1,left)
    result=dict(status='PASS',mode=mode,k=k,all_CSR_entries_checked=True,all_row_pointers_checked=True,
        actual_affine_reconstruction=True,disjoint_fixed_support=True,injective_insertion=True,
        cleared_comparison_offsets_cancel=True,finite_regression_not_proof=True,seed=20260928,
        scalar_rows=nr,nnz=meta['nnz'],comparator_nnz_per_coefficient=[len([v for row in rows for v in row[a]]) for a in range(3)])
    (directory/'independent_layout.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(mode,k,'all matrices and embedding checked',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--arity',type=int,default=4)
    parser.add_argument('--mode',choices=['special','prefix'],default='special')
    args=parser.parse_args();check(args.mode,args.arity)
