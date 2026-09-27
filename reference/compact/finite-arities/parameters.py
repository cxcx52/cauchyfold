"""Finite CauchyFold schedule model. Counts are syntax-level, not proof benchmarks.
Based on manuscript equations (19),(20),(22),(27),(28), Appendix B/C.5/E,
and the prior 42-byte aggregation / fixed-capacity Rice proposal.
No lattice-estimator cost is invented here. All arithmetic decisions are integral.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt
from functools import lru_cache
import json

Q=2**48-59
D=64
A=24
AT=AH=16
AF=32
AP=4
M=864
SIGMA=4
TAU=3
TOP=MU=128
RP=RC=160
CHALLENGE_SIZE=5**64
REFERENCE_MAIN_B=1821
REFERENCE_MAIN_BETA=4567851477
REFERENCE_AUX_B=1728
REFERENCE_AUX_BETA=139383
REFERENCE_FRONT_BETA=8192
REFERENCE_FRONT_AUX_B=4350
REFERENCE_PIVOT_BETA=1255
RING_BYTES=384
AGG_BYTES=42


def ceildiv(a:int,b:int)->int:
    return (a+b-1)//b

def ceil_log2(n:int)->int:
    assert n>0
    return (n-1).bit_length()

def ceil_sqrt(n:int)->int:
    r=isqrt(n)
    return r+(r*r!=n)


def front(k:int,capacity:int|None=None,split_aux:bool=False)->dict:
    if type(k) is not int or not 1<=k<Q:
        raise ValueError('this concrete pole convention requires 1 <= k < q')
    used=29568*k+69889
    cap=used if capacity is None else capacity
    if cap<used:
        raise ValueError('capacity smaller than encoded witness')
    V=77*k+182
    categories={
        'Boolean value bits and helpers':384*V,
        'Canonical prefix recurrences':192*V,
        'First-difference restrictions':16*V,
        'Exclusion of equality to q':4*V,
        'Public coordinates':5*(k+2),
        'Fresh u=1 and E=0':5*k,
        'Fresh base-field restrictions':207*k,
        'Folded source equations':69,
        'Folded residual equations':4,
        'Quadratic product gates':36,
        'Output residual equations':4,
        'Reserved zero constraints':cap-used,
    }
    rows=sum(categories.values())
    assert rows==cap+16541*k+38706
    ell=ceil_log2(rows)
    aux_cols=231*k+654
    aux_chunks=([min(4350,aux_cols-start) for start in range(0,aux_cols,4350)] if split_aux else [aux_cols])
    return dict(k=k,auxiliary_chunks=aux_chunks,canonical_K_values=V,carrier_K_values=4*k,
                carrier_private_bits=768*k,carrier_columns=12*k,
                auxiliary_private_bits=14784*k+41856,auxiliary_columns=231*k+654,
                used=used,capacity=cap,reserved_zeros=cap-used,field_rows=rows,
                field_padded_rows=1<<ell,field_rounds=ell,categories=categories,
                initial_linear_rows=(k+3+len(aux_chunks))*AF*D+13+(cap-used),
                wrapper_p_bytes=(2+len(aux_chunks))*AF*RING_BYTES+96*ell+72,
                wrapper_v_bytes=24+48*ell)

@lru_cache(maxsize=150000)
def rice(n:int,T:int)->tuple[int,int,int]:
    """(byte capacity,k,bit bound), min over publicly fixed k >= 1."""
    root=isqrt(n*T)
    # f(j+1)-f(j) = n - ceil((root >> (j-1))/2), so the first
    # nonnegative difference occurs when root >> (j-1) <= 2*n.
    # This is the exact discrete optimum, including ties, not a log estimate.
    j=1+(root//(2*n+1)).bit_length()
    bits=n*(j+1)+(root>>(j-1))
    return ceildiv(bits,8),j,bits

@lru_cache(maxsize=150000)
def seed(N:int,S:int)->tuple[int,int,int,int,int]:
    """(bytes,block length,depth,state log bound,seed bits)."""
    R=2*M*N
    T=M*S
    w=ceil_log2((R+1)*4*Q*(T+2))
    K=ceil_log2(R)
    b=6*w+2*K+450+ceil_log2(K)+3
    h=max(0,ceil_log2(ceildiv(R,b)))
    assert b*(1<<h)>=R and (h==0 or b*(1<<(h-1))<R)
    bits=b+h*(3*b-1)
    return ceildiv(bits,8),b,h,w,bits


def seed_certificate(N:int,S:int)->dict:
    by,b,h,w,bits=seed(N,S)
    delta=Fraction(1,2**150*2*(2**h-1))
    error=(2**h-1)*delta+Fraction(2**(6*w)*h,2**b)/delta**2
    assert error<Fraction(1,2**150)
    assert Fraction(1,2**150)<Fraction(1,2*(M*S+1))
    return dict(bytes=by,block_bits=b,depth=h,state_bits=w,seed_bits=bits,
                error_lt_2_to_minus_150=True,honest_integrality_slack_ok=True)


def dims(raw:int,s:int)->tuple[int,int,int]:
    n=ceildiv(raw,D*s)
    N=D*s*n
    return n,N,N-raw


def child(raw:int,S:int,s:int,rho:int)->tuple[int,int,int,int,int,int]:
    assert rho>1 and rho&(rho-1)==0
    n,N,pad=dims(raw,s)
    ell=ceildiv(48,rho.bit_length()-1)
    digit_bound=rho//2
    G=256*S
    nd=D*n
    bt=ell*A*s
    bh=ell*TAU*s*(s+1)//2
    raw1=2*nd+D*(bt+bh)
    # Equation (20), exact ceiling, not the sharper unpublished energy bound.
    S1=nd*digit_bound**2 + ceildiv(2*G+2*nd*digit_bound**2,rho*rho) + D*(bt+bh)*digit_bound**2
    betaA=ceil_sqrt((8*TOP)**2*(1+rho*rho)*SIGMA**2*S1)
    beta_aux=ceil_sqrt(4*SIGMA**2*S1)
    return raw1,S1,bt,bh,betaA,beta_aux


def terminal_G(S:int)->int:
    return ceildiv(256*CHALLENGE_SIZE*S,CHALLENGE_SIZE-1)


def layer_cost(raw:int,S:int,s:int,terminal:bool)->tuple[int,int]:
    n,N,pad=dims(raw,s)
    p_bytes=rice(M,M*S)[0]
    v=seed(N,S)[0]+AGG_BYTES+24*s
    if terminal:
        G=terminal_G(S)
        p=(s-1)*A*RING_BYTES+AP*RING_BYTES+p_bytes+TAU*s*(s+1)//2*RING_BYTES-TAU*6+rice(D*n,G)[0]+2
    else:
        p=(AT+AH)*RING_BYTES+p_bytes+2
    return p,v


def main_feasible(raw:int,S:int,s:int)->bool:
    n,N,pad=dims(raw,s)
    return n<=REFERENCE_MAIN_B and (128*SIGMA)**2*S<=Q*Q


def transition_feasible(raw:int,S:int,s:int,rho:int)->bool:
    if not main_feasible(raw,S,s):
        return False
    raw1,S1,bt,bh,ba,baux=child(raw,S,s,rho)
    return max(bt,bh)<=REFERENCE_AUX_B and ba<=REFERENCE_MAIN_BETA and baux<=REFERENCE_AUX_BETA


def evaluate_schedule(k:int,path:list[tuple[int,int|None]],capacity:int|None=None,
                   S0:int|None=None,enforce_backend_envelope:bool=True,split_aux:bool=False)->dict:
    """path consists of (block count, radix), ending in (block count,None)."""
    f=front(k,capacity,split_aux)
    raw=f['capacity']; S=f['used'] if S0 is None else S0
    assert S>=f['used']
    base_rows=f['initial_linear_rows']
    P=f['wrapper_p_bytes']; V=f['wrapper_v_bytes']
    records=[]; roles=[]
    beta_front=ceil_sqrt(4*SIGMA**2*S)
    for role,b in [('Ast',219),('AH',f['carrier_columns'])]+[(f'Aaux{j}',b) for j,b in enumerate(f['auxiliary_chunks'])]:
        roles.append(dict(role=role,a=AF,b=b,beta=beta_front))
    for i,(s,rho) in enumerate(path):
        terminal=rho is None
        assert terminal==(i==len(path)-1)
        assert s>=2
        n,N,pad=dims(raw,s)
        assert (128*SIGMA)**2*S<=Q*Q
        p,v=layer_cost(raw,S,s,terminal)
        sc=seed_certificate(N,S)
        R=base_rows+pad+M
        deg=ceildiv(R,4)-1
        G=terminal_G(S) if terminal else 256*S
        record=dict(i=i,s=s,rho=rho,n=n,N=N,N_raw=raw,S=S,G=G,padding=pad,
                    linear_rows=base_rows+pad,augmented_rows=R,aggregation_degree=deg,
                    seed=sc,projection_codec_bytes=rice(M,M*S)[0],projection_codec_k=rice(M,M*S)[1],
                    p_bytes=p,v_bytes=v,terminal=terminal)
        if terminal:
            beta=ceil_sqrt((8*TOP)**2*G)
            record.update(terminal_codec_bytes=rice(D*n,G)[0],terminal_codec_k=rice(D*n,G)[1])
            roles.extend([dict(role=f'A{i}',a=A,b=n,beta=beta),
                          dict(role='Bp',a=AP,b=A*16,beta=ceil_sqrt(8**2*D*A*16))])
            if enforce_backend_envelope:
                assert n<=REFERENCE_MAIN_B and beta<=REFERENCE_MAIN_BETA
        else:
            raw1,S1,bt,bh,ba,baux=child(raw,S,s,rho)
            assert not enforce_backend_envelope or transition_feasible(raw,S,s,rho)
            record.update(next_raw=raw1,next_S=S1,bt_columns=bt,bh_columns=bh)
            roles.extend([dict(role=f'A{i}',a=A,b=n,beta=ba),
                          dict(role=f'B{i}',a=AT,b=bt,beta=baux),
                          dict(role=f'D{i}',a=AH,b=bh,beta=baux)])
            raw,S,base_rows=raw1,S1,D*(AT+AH+A+TAU)+TAU
        records.append(record); P+=p; V+=v
    # Conservative exact rational statistical ledger.
    theta=Fraction(7,8)+Fraction(1,2**1000)
    projection=len(path)*RP*(Fraction(48,47)*theta)**M
    coordinate=3*RC*(Fraction(sum(s for s,r in path)-1,CHALLENGE_SIZE)+Fraction(1,CHALLENGE_SIZE-1))
    aggregation=Fraction(len(path),Q**3)+Fraction(sum(r['aggregation_degree'] for r in records),Q**4)
    field=Fraction(4*f['field_rounds'],Q**4)
    cauchy=Fraction(2*k,Q**4-k)
    error=field+cauchy+projection+coordinate+aggregation
    assert error<Fraction(1,2**128)
    comp=Fraction(2*len(path),2**160)
    for r in roles:
        assert r['beta']<Q
        if r['a']==AF:
            # Use the largest original 32-row front key as a reference.
            r['reference']='Aaux(original)'
            r['reference_b']=4350; r['reference_beta']=8192
        elif r['a']==A:
            r['reference']='A0(original)';r['reference_b']=1821;r['reference_beta']=4567851477
        elif r['a']==AT:
            r['reference']='B0(original)';r['reference_b']=1728;r['reference_beta']=139383
        else:
            r['reference']='Bp(original)';r['reference_b']=384;r['reference_beta']=1255
        r['zero_extension_dominance']=(r['b']<=r['reference_b'] and r['beta']<=r['reference_beta'])
    # Display-only floats; every probability decision above used Fraction.
    from decimal import Decimal,localcontext
    with localcontext() as c:
        c.prec=45
        exponent=-(Decimal(error.numerator).ln()-Decimal(error.denominator).ln())/Decimal(2).ln()
    extra_attempts=sum(r['seed']['bytes']+24*r['s']+2 for r in records)
    total=P+V
    registry_bytes=sum(r['a']*r['b']*RING_BYTES for r in roles)
    return dict(front=f,path=path,layers=records,roles=roles,role_count=len(roles),
                all_roles_reference_dominated=all(r['zero_extension_dominance'] for r in roles),
                non_dominated_roles=[r['role'] for r in roles if not r['zero_extension_dominance']],
                p_bytes=P,v_bytes=V,total_bytes=total,KiB=total/1024,MiB=total/2**20,
                plus_fresh_commitments=total+k*AF*RING_BYTES,
                plus_all_input_commitments=total+(k+1)*AF*RING_BYTES,
                max_accepted_bytes=total+159*extra_attempts,
                honest_unconditional_expectation_upper_bytes=total+extra_attempts,
                input_commitments_bytes=(k+1)*AF*RING_BYTES,crs_bytes=registry_bytes,
                statistical_error_lt_2neg128=True,statistical_error_lt_2neg130=error<Fraction(1,2**130),
                statistical_exponent_display=str(exponent),
                exact_error_expression=dict(field_rounds=f['field_rounds'],k=k,layers=len(path),sum_blocks=sum(s for s,r in path),sum_aggregation_degrees=sum(r['aggregation_degree'] for r in records),projection_theta='7/8 + 2^-1000'),
                projection_trits_per_one_scan=sum(M*r['N'] for r in records),
                completeness_error=f'{2*len(path)} * 2^-160')

@dataclass(slots=True)
class Node:
    raw:int
    S:int
    cost:int
    path:tuple


def pareto(nodes:list[Node])->list[Node]:
    # Exact skyline of (spent cost,raw,S), used as a HEURISTIC search pruning.
    # Nisan seed length can drop at a recursion-depth boundary, so this does NOT
    # certify global dominance of complete future schedules. Every output is
    # checked independently for feasibility; no optimality theorem is asserted.
    nodes.sort(key=lambda a:(a.cost,a.raw,a.S,a.path))
    xs=sorted({a.raw for a in nodes})
    positions={x:i+1 for i,x in enumerate(xs)}
    inf=10**100
    tree=[inf]*(len(xs)+1)
    out=[]
    for a in nodes:
        idx=positions[a.raw]; j=idx; best=inf
        while j>0:
            best=min(best,tree[j]); j-=j&-j
        if best<=a.S:
            continue
        out.append(a)
        while idx<len(tree):
            tree[idx]=min(tree[idx],a.S);idx+=idx&-idx
    return out


def optimize(k:int,radices:tuple=(4,8,16,32,64,128),max_nonterminal:int=5)->dict:
    """Finite parameter grid; DOES NOT claim a global protocol optimum.
    Keeps ranks, sigma,m,tau,challenge alphabet, retries and pivot radix fixed.
    Backend reference envelopes cap both widths and kernel radii.
    """
    f=front(k,split_aux=True)
    nodes=[Node(f['capacity'],f['used'],0,())]
    best=None; levels=[]
    choices=[(s,rho) for s in range(2,33) for rho in radices
             if max(ceildiv(48,rho.bit_length()-1)*A*s,
                    ceildiv(48,rho.bit_length()-1)*TAU*s*(s+1)//2)<=REFERENCE_AUX_B]
    transitions=0; terminal_checks=0
    for depth in range(max_nonterminal+1):
        for a in nodes:
            for s in range(2,33):
                if not main_feasible(a.raw,a.S,s):continue
                G=terminal_G(a.S)
                if ceil_sqrt((8*TOP)**2*G)>REFERENCE_MAIN_BETA:continue
                p,v=layer_cost(a.raw,a.S,s,True)
                terminal_checks+=1
                value=a.cost+p+v
                key=(value,a.path+((s,None),))
                if best is None or key[0]<best[0]:best=key
        levels.append(dict(nonterminal_depth=depth,frontier_size=len(nodes),best_backend_bytes=None if best is None else best[0]))
        if depth==max_nonterminal:break
        nexts=[]
        for a in nodes:
            for s,rho in choices:
                if not transition_feasible(a.raw,a.S,s,rho):continue
                p,v=layer_cost(a.raw,a.S,s,False)
                cost=a.cost+p+v
                if best is not None and cost>=best[0]:continue
                raw1,S1,*_=child(a.raw,a.S,s,rho)
                nexts.append(Node(raw1,S1,cost,a.path+((s,rho),)))
                transitions+=1
        if not nexts:break
        nodes=pareto(nexts)
    if best is None:raise RuntimeError('no feasible schedule in this search grid')
    result=evaluate_schedule(k,list(best[1]),split_aux=True)
    assert result['total_bytes']==best[0]+f['wrapper_p_bytes']+f['wrapper_v_bytes']
    result['search']=dict(radices=radices,max_nonterminal=max_nonterminal,block_count_range=[2,32],
                          transitions=transitions,terminal_checks=terminal_checks,levels=levels,
                          algorithm='Pareto-pruned finite candidate search; no certified optimality (seed lengths have discontinuities)')
    return result


def baseline():
    path=[(9,64),(6,64),(5,64),(4,64),(4,64),(7,None)]
    b=evaluate_schedule(16,path,capacity=2**20,S0=2**20)
    assert [x['S'] for x in b['layers']]==[1048576,303555488,216957652,163590043,133127892,122566619]
    assert [x['n'] for x in b['layers']]==[1821,1075,762,711,608,318]
    assert [x['seed']['bytes'] for x in b['layers']]==[9486,9346,8829,8331,8289,8276]
    assert [x['augmented_rows'] for x in b['layers']]==[547756,4643,4899,4643,4771,4771]
    assert b['total_bytes']==288157 and b['p_bytes']==233476 and b['v_bytes']==54681
    assert b['crs_bytes']==155814912
    return b

if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--k',type=int,nargs='+',default=[2,4,8,16,32]);
    p.add_argument('--radices',type=int,nargs='+',default=[4,8,16,32,64,128]);
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'results');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    b=baseline()
    # Omit giant exact fractions from the compact baseline file, preserve in detailed results.
    (a.output/'baseline.json').write_bytes((json.dumps(b,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    for k in a.k:
        r=optimize(k,tuple(a.radices))
        (a.output/f'arity-{k}-candidate.json').write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode('utf-8'))
        print(k,r['total_bytes'],r['KiB'],r['path'],r['non_dominated_roles'],flush=True)
