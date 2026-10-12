"""Exact semantic continuation tests and dense field-kernel operation counts."""
from pathlib import Path
import sys
import json
import random

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from field_arithmetic import Q, ZERO, ONE, ea, es, em, quadratic


def power(x,n):
    y=ONE
    while n:
        if n&1:y=em(y,x)
        x=em(x,x);n//=2
    return y


def weights(k,c):
    diffs=[es(c,(i,0,0,0)) for i in range(k)]
    pref=[ONE]
    for d in diffs:pref.append(em(pref[-1],d))
    inv=power(pref[-1],Q**4-2)
    assert em(inv,pref[-1])==ONE
    out=[ZERO]*k
    for i in reversed(range(k)):
        out[i]=em(inv,pref[i]);inv=em(inv,diffs[i])
    return out


def bilinear(a,b):
    return [es(es(v,x),y) for v,x,y in zip(quadratic([ea(x,y) for x,y in zip(a,b)]),quadratic(a),quadratic(b))]


def fresh(rng):
    z=[(rng.randrange(Q),0,0,0) for _ in range(69)]
    z[0]=ONE
    z[1:5]=[ZERO]*4
    z[1:5]=quadratic(z)
    assert quadratic(z)==[ZERO]*4
    return z


def semantic():
    rng=random.Random(20261012)
    cases=[]
    for k in (2,4,16,1024):
        acc=[tuple(rng.randrange(Q) for _ in range(4)) for _ in range(69)]
        for depth in range(3):
            w=weights(k,(k+17+depth,3+depth,4,5))
            if depth==0:
                acc[0]=ZERO
                for x in w:acc[0]=es(acc[0],x)
            E=quadratic(acc)
            out=acc[:]
            expanded=E[:]
            for a in w:
                z=fresh(rng)
                scaled=[em(a,x) for x in z]
                cross=bilinear(out,scaled)
                expanded=[ea(e,b) for e,b in zip(expanded,cross)]
                out=[ea(x,y) for x,y in zip(out,scaled)]
            assert quadratic(out)==expanded
            if depth==0:assert out[0]==ZERO
            encoded=[(v>>j)&1 for x in out+expanded for v in x for j in range(48)]
            assert len(encoded)==14016 and sum(encoded)<=14016
            recovered=[]
            for p in range(0,len(encoded),192):
                recovered.append(tuple(sum(encoded[p+48*t+j]<<j for j in range(48)) for t in range(4)))
            assert recovered==out+expanded
            cases.append(dict(k=k,fold_depth=depth+1,output_is_next_accumulator=True,
                output_u_zero=out[0]==ZERO,encoding_bits=len(encoded),ring_columns=219,
                encoding_squared_norm=sum(encoded),expansion_matches_output_Q=True))
            acc=out
    return dict(seed=20261012,scope='Finite semantic continuation regression; not recursive proof-system execution',cases=cases)


class Counter:
    def __init__(self):self.n=0
    def mul(self,a,b):self.n+=1;return em(a,b)


def eq(r):
    v=[ONE]
    for a in r:
        z=[]
        for x in v:
            y=em(x,a);z.extend([es(x,y),y])
        v=z
    return v


def kernels():
    rng=random.Random(98213)
    records=[]
    coin=lambda:tuple(rng.randrange(Q) for _ in range(4))
    for ell in range(1,7):
        P=1<<ell;r=[coin() for _ in range(ell)]
        A=[coin() for _ in range(P)];B=[coin() for _ in range(P)];C=[em(a,b) for a,b in zip(A,B)]
        W=eq(r);prefix=ONE
        gc,fc,gfold,ffold=Counter(),Counter(),Counter(),Counter()
        claim=ZERO
        for j in range(ell):
            n=len(A)//2;gen=[ZERO]*4;tot=[ZERO]*3;suffix=eq(r[j+1:])
            for i in range(n):
                a,b,c,w=A[i],B[i],C[i],W[i]
                da,db,dc,dw=es(A[i+n],a),es(B[i+n],b),es(C[i+n],c),es(W[i+n],w)
                p0=es(gc.mul(a,b),c);p1=es(ea(gc.mul(a,db),gc.mul(da,b)),dc);p2=gc.mul(da,db)
                parts=[gc.mul(w,p0),ea(gc.mul(w,p1),gc.mul(dw,p0)),ea(gc.mul(w,p2),gc.mul(dw,p1)),gc.mul(dw,p2)]
                gen=[ea(x,y) for x,y in zip(gen,parts)]
                f0=es(fc.mul(a,b),c);f2=fc.mul(da,db)
                f1=es(es(es(fc.mul(A[i+n],B[i+n]),C[i+n]),f0),f2)
                tot=[ea(x,fc.mul(suffix[i],y)) for x,y in zip(tot,[f0,f1,f2])]
            tot=[em(prefix,x) for x in tot]
            e0=es(ONE,r[j]);e1=es(ea(r[j],r[j]),ONE)
            fact=[em(e0,tot[0]),ea(em(e0,tot[1]),em(e1,tot[0])),ea(em(e0,tot[2]),em(e1,tot[1])),em(e1,tot[2])]
            assert gen==fact
            assert ea(gen[0],sumfield(gen))==claim
            assert es(claim,em(r[j],ea(tot[1],tot[2])))==tot[0]
            tau=coin();claim=ZERO
            for x in reversed(gen):claim=ea(em(claim,tau),x)
            for tab in [A,B,C,W]:
                generic=[ea(tab[i],gfold.mul(tau,es(tab[i+n],tab[i]))) for i in range(n)]
                if tab is not W:
                    factor=[ea(tab[i],ffold.mul(tau,es(tab[i+n],tab[i]))) for i in range(n)]
                    assert generic==factor
                tab[:]=generic
            prefix=em(prefix,ea(e0,em(e1,tau)))
        assert gc.n==10*(P-1) and fc.n==6*(P-1)
        assert gfold.n==4*(P-1) and ffold.n==3*(P-1)
        records.append(dict(rounds=ell,padded_rows=P,identical_round_polynomials=True,
                            generic_pair_K_mul=gc.n,factor_pair_K_mul=fc.n,
                            generic_fold_K_mul=gfold.n,factor_fold_K_mul=ffold.n))
    P=1<<23
    return dict(seed=98213,tests=records,
       count_scope='Dense pair and table-fold loops only; scalar round work, equality generation, encoding, commitments and backend excluded',
       current_instance=dict(padded_rows=P,generic_grouped_K_mul=14*(P-1),
           factored_equality_K_mul=9*(P-1),saved_K_mul=5*(P-1),
           dense_table_payload_bytes=dict(generic_four_tables=4*P*32,factored_three_tables=3*P*32),
           memory_scope='Conceptual dense E tables only; excludes weights, artifacts and streamed implementations',
           advantage_of_algorithm_not_carrier_lower_bound=True))


def sumfield(xs):
    s=ZERO
    for x in xs:s=ea(s,x)
    return s


def main():
    result=dict(recursive_semantics=semantic(),field_kernels=kernels())
    (ROOT/'checks.json').write_bytes((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
    print('PASS 12 recursive semantic continuations and 6 field-kernel equivalence tests')


if __name__=='__main__':main()
