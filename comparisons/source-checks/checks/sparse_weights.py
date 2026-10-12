"""Check equality-weight plus sparse correction for grouped sumcheck."""
from array import array
from pathlib import Path
import json
import random
from check import Q, ZERO, ONE, em, ea, es, eq, Counter, sumfield

ROOT=Path(__file__).resolve().parent


def run_case(ell,rng):
    P=1<<ell;terms=P-5;single=terms-19
    ids=list(range(single))+[single]*9+[single+1]*10
    coin=lambda:tuple(rng.randrange(Q) for _ in range(4))
    r=[coin() for _ in range(ell)];wr=eq(r)
    A=[coin() for _ in range(terms)]+[ZERO]*5
    B=[coin() for _ in range(terms)]+[ZERO]*5
    C=[em(a,b) for a,b in zip(A,B)]
    for start,size in ((single,9),(single+9,10)):
        residual=[coin() for _ in range(size-1)]
        residual.append(es(ZERO,sumfield(residual)))
        for t,e in enumerate(residual,start):C[t]=es(C[t],e)
    W=wr[:]
    D={}
    for t,g in enumerate(ids):
        W[t]=wr[g]
        if g!=t:D[t]=es(wr[g],wr[t])
    assert sumfield([em(w,es(em(a,b),c)) for w,a,b,c in zip(W,A,B,C)])==ZERO
    generic,structured,foldg,folds=Counter(),Counter(),Counter(),Counter()
    prefix=ONE;claim=ZERO;support_pairs=[]
    for j in range(ell):
        n=len(A)//2;gp=[ZERO]*4;fp=[ZERO]*3;cp=[ZERO]*4
        suffix=eq(r[j+1:]);support={t%n for t in D};support_pairs.append(len(support))
        for i in range(n):
            a,b,c,w=A[i],B[i],C[i],W[i]
            da,db,dc,dw=es(A[i+n],a),es(B[i+n],b),es(C[i+n],c),es(W[i+n],w)
            p0=es(generic.mul(a,b),c)
            p1=es(ea(generic.mul(a,db),generic.mul(da,b)),dc)
            p2=generic.mul(da,db)
            gp=[ea(x,y) for x,y in zip(gp,[generic.mul(w,p0),
                ea(generic.mul(w,p1),generic.mul(dw,p0)),
                ea(generic.mul(w,p2),generic.mul(dw,p1)),generic.mul(dw,p2)])]
            f0=es(structured.mul(a,b),c);f2=structured.mul(da,db)
            f1=es(es(es(structured.mul(A[i+n],B[i+n]),C[i+n]),f0),f2)
            fp=[ea(x,structured.mul(suffix[i],y)) for x,y in zip(fp,[f0,f1,f2])]
            if i in support:
                d=D.get(i,ZERO);dd=es(D.get(i+n,ZERO),d)
                cp=[ea(x,y) for x,y in zip(cp,[structured.mul(d,f0),
                    ea(structured.mul(d,f1),structured.mul(dd,f0)),
                    ea(structured.mul(d,f2),structured.mul(dd,f1)),structured.mul(dd,f2)])]
        fp=[em(prefix,x) for x in fp]
        e0=es(ONE,r[j]);e1=es(ea(r[j],r[j]),ONE)
        base=[em(e0,fp[0]),ea(em(e0,fp[1]),em(e1,fp[0])),ea(em(e0,fp[2]),em(e1,fp[1])),em(e1,fp[2])]
        assert gp==[ea(x,y) for x,y in zip(base,cp)]
        assert ea(gp[0],sumfield(gp))==claim
        tau=coin();claim=ZERO
        for x in reversed(gp):claim=ea(em(claim,tau),x)
        for tab in (A,B,C,W):
            values=[ea(tab[i],foldg.mul(tau,es(tab[i+n],tab[i]))) for i in range(n)]
            if tab is not W:
                assert values==[ea(tab[i],folds.mul(tau,es(tab[i+n],tab[i]))) for i in range(n)]
            tab[:]=values
        D={i:ea(D.get(i,ZERO),folds.mul(tau,es(D.get(i+n,ZERO),D.get(i,ZERO)))) for i in support}
        prefix=em(prefix,ea(e0,em(e1,tau)))
    assert claim==em(ea(prefix,D.get(0,ZERO)),es(em(A[0],B[0]),C[0]))
    assert generic.n+foldg.n==14*(P-1)
    assert structured.n+folds.n==9*(P-1)+7*sum(support_pairs)
    return dict(rounds=ell,all_polynomials_equal=True,terminal_equal=True,
                generic_core_K_mul=generic.n+foldg.n,structured_core_K_mul=structured.n+folds.n,
                sparse_pair_counts=support_pairs)


def main():
    rng=random.Random(2026101202)
    cases=[run_case(ell,rng) for ell in range(5,11)]
    direct=ROOT.parent/'direct/results/arity-1024'
    meta=json.loads((direct/'compiler.json').read_text())
    ids=array('I')
    group_file=direct/'groups.u32'
    if group_file.exists():
        with group_file.open('rb') as f:ids.fromfile(f,meta['terms'])
    else:
        single=63*meta['free_coefficients']+4*1024+10+69
        ids.extend(range(single))
        group=single
        for size in [10]*4+[9]*(4*1024)+[10]*4:
            ids.extend([group]*size);group+=1
        assert len(ids)==meta['terms'] and group==meta['groups']
    import hashlib
    assert hashlib.sha256(ids.tobytes()).hexdigest()==(direct/'group-map.sha256').read_text().strip()
    support={t for t,g in enumerate(ids) if t!=g}
    initial=len(support);P=1<<(meta['terms']-1).bit_length();n=P//2;counts=[]
    while n:
        support={i%n for i in support};counts.append(len(support));n//=2
    value=dict(scope='Exact small-field-transcript regression and actual k=1024 group-layout support counts; no full optimized k=1024 prover run',
        seed=2026101202,tests=cases,current_group_layout=dict(terms=meta['terms'],padded_terms=P,
            initial_exception_terms=initial,exception_pair_support_per_round=counts,
            sum_exception_pairs=sum(counts),sparse_delta_table_peak_entries=initial,
            generic_core_K_mul=14*(P-1),structured_core_K_mul_upper=9*(P-1)+7*sum(counts),
            carrier_factor_core_K_mul=9*(P-1),
            excluded_costs=['equality weights and initial sparse-delta construction','scalar round operations','sparse-map lookups','encoding and matrix applications','commitments and lattice backend']),
        padding_rule='W(t)=eq(r,t) at padding; A=B=C=0 there, so the Boolean sum is unchanged',
        generic_three_coefficient_messages=True)
    (ROOT/'sparse-weights.json').write_bytes((json.dumps(value,indent=2,sort_keys=True)+'\n').encode())
    print(json.dumps(value['current_group_layout']))


if __name__=='__main__':main()
