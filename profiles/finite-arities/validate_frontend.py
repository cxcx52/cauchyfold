"""Independent arity-parametric semantic/encoding checks for the original relation.
Checks all scalar canonical-comparison constraints on each generated assignment;
checks all semantic rows equivalent to the sparse front-end row definitions.
It does not generate or run the full lattice protocol, or measure proof times.
"""
from __future__ import annotations
from collections import Counter
from math import prod
from random import Random
from pathlib import Path
import json, hashlib
from parameters import Q, front
from codec import Quartic, ZERO, ONE, concrete_field_certificate
F=Quartic(Q)


def add(a,b):return F.add(a,b)
def sub(a,b):return tuple((x-y)%Q for x,y in zip(a,b))
def scale(a,x):return F.scale(a,x)
def mul(a,b):
    if not any(a[1:]):return scale(b,a[0])
    if not any(b[1:]):return scale(a,b[0])
    return F.mul(a,b)
def scalar(x):return (x%Q,0,0,0)
def ai(j,l):return 5+16*j+2*l
def bi(j,l):return ai(j,l)+1


def quadratic(z):
    out=[]
    for j in range(4):
        s=ZERO
        for l in range(8):s=add(s,mul(z[ai(j,l)],z[bi(j,l)]))
        out.append(sub(s,mul(z[0],z[j+1])))
    return out

def bilinear(x,z):
    out=[]
    for j in range(4):
        s=ZERO
        for l in range(8):
            s=add(s,mul(x[ai(j,l)],z[bi(j,l)]))
            s=add(s,mul(z[ai(j,l)],x[bi(j,l)]))
        out.append(sub(sub(s,mul(x[0],z[j+1])),mul(z[0],x[j+1])))
    return out

def sources(k):
    out=[]
    for i in range(k+1):
        z=[ZERO]*69;z[0]=scalar(2 if i==0 else 1)
        for j in range(4):
            v=0
            for l in range(8):
                a,b=i+j+l+1,2*i+j+3*l+2
                z[ai(j,l)]=scalar(a);z[bi(j,l)]=scalar(b);v+=a*b
            z[j+1]=scalar(17+j if i==0 else v)
        e=quadratic(z)
        assert i==0 or e==[ZERO]*4
        out.append((z,e))
    return out

def pole_poly(k,excluded=()):
    p=[1]
    for pole in range(k):
        if pole in excluded:continue
        v=[0]*(len(p)+1)
        for j,x in enumerate(p):
            v[j]=(v[j]-pole*x)%Q;v[j+1]=(v[j+1]+x)%Q
        p=v
    return p

def carrier_pair(src):
    k=len(src)-1;H=[[ZERO]*4 for _ in range(k)]
    def accum(v,p):
        for a,c in enumerate(p):
            for j in range(4):H[a][j]=add(H[a][j],scale(v[j],c))
    for i in range(k):accum(bilinear(src[0][0],src[i+1][0]),pole_poly(k,(i,)))
    for i in range(k):
        for j in range(i+1,k):accum(bilinear(src[i+1][0],src[j+1][0]),pole_poly(k,(i,j)))
    return H

def carrier_residues(src):
    # Independent direct residue formula, not claimed to be the fast tree implementation.
    k=len(src)-1;H=[[ZERO]*4 for _ in range(k)]
    for i in range(k):
        v=list(src[0][0])
        for j in range(k):
            if i==j:continue
            inv=pow((i-j)%Q,-1,Q)
            for a in range(69):v[a]=add(v[a],scale(src[j+1][0][a],inv))
        R=bilinear(src[i+1][0],v)
        for a,c in enumerate(pole_poly(k,(i,))):
            for j in range(4):H[a][j]=add(H[a][j],scale(R[j],c))
    return H

def weights(c,k):
    dif=[sub(c,scalar(i)) for i in range(k)]
    assert all(x!=ZERO for x in dif)
    prefix=[ONE]
    for x in dif:prefix.append(mul(prefix[-1],x))
    Dinv=F.pow(prefix[-1],Q**4-2);inverse=Dinv;w=[ZERO]*k
    for i in reversed(range(k)):
        w[i]=mul(inverse,prefix[i]);inverse=mul(inverse,dif[i])
    for x,a in zip(dif,w):assert mul(x,a)==ONE
    return w,Dinv

def fold(src,H,c):
    k=len(src)-1;a,di=weights(c,k)
    z=list(src[0][0]);E=list(src[0][1]);Hc=[ZERO]*4
    for coeff in reversed(H):
        for j in range(4):Hc[j]=add(mul(Hc[j],c),coeff[j])
    for i in range(k):
        for j in range(69):z[j]=add(z[j],mul(a[i],src[i+1][0][j]))
        for j in range(4):E[j]=add(E[j],mul(mul(a[i],a[i]),src[i+1][1][j]))
    for j in range(4):E[j]=add(E[j],mul(di,Hc[j]))
    return z,E,a,di

def encode_with_helpers(values):
    B=192*len(values)
    bits=bytearray(2*B+1)
    for vi,value in enumerate(values):
        for t,x in enumerate(value):
            assert 0<=x<2**48
            offset=192*vi+48*t
            e=1
            for j in reversed(range(48)):
                b=(x>>j)&1;bits[offset+j]=b
                e=e*int(b==((Q>>j)&1));bits[B+offset+j]=e
    bits[-1]=1
    return bits

def decode_values(bits,V):
    return [tuple(sum(bits[192*i+48*t+j]<<j for j in range(48))%Q for t in range(4)) for i in range(V)]

def check_canonical_rows(bits,V):
    B=192*V
    if len(bits)!=2*B+1 or bits[-1]!=1:return False,'constant/length'
    if any(b not in (0,1) for b in bits[:-1]):return False,'boolean'
    for offset in range(0,B,48):
        for j in reversed(range(48)):
            b=bits[offset+j];enext=1 if j==47 else bits[B+offset+j+1]
            expected=enext*(b if (Q>>j)&1 else 1-b)
            if expected!=bits[B+offset+j]:return False,'prefix recurrence'
            if ((Q>>j)&1)==0 and enext*b:return False,'first difference'
        if bits[B+offset]:return False,'equality to q'
    return True,'ok'

def run():
    out={'field_certificate':concrete_field_certificate(),'scope':'Front-end and counting regression, not full lattice-protocol integration','cases':[]}
    for k in [1,2,3,4,6,8,10,16,32]:
        f=front(k);src=sources(k);H=carrier_pair(src);assert carrier_residues(src)==H
        for ci,c in enumerate([scalar(k),(k+17,3,4,5)]):
            z,E,a,di=fold(src,H,c);assert quadratic(z)==E
            # All semantic constraint families of the original front end.
            for zs,es in src[1:]:
                assert zs[0]==ONE and es==[ZERO]*4
                assert not any(any(v[1:]) for v in zs)
            for j in range(5):
                x=src[0][0][j]
                for i in range(k):x=add(x,mul(a[i],src[i+1][0][j]))
                assert x==z[j]
            gates=[]
            for j in range(4):
                gates.extend(mul(z[ai(j,l)],z[bi(j,l)]) for l in range(8))
                gates.append(mul(z[0],z[j+1]))
            for j in range(4):
                total=ZERO
                for l in range(8):total=add(total,gates[j*9+l])
                assert sub(total,gates[j*9+8])==E[j]
            values=[v for zs,es in src+[(z,E)] for v in zs+es]+[v for coeff in H for v in coeff]+gates
            assert len(values)==f['canonical_K_values']
            bits=encode_with_helpers(values);assert len(bits)==f['used']
            assert check_canonical_rows(bits,len(values))==(True,'ok')
            assert decode_values(bits,len(values))==values
            assert sum(b*b for b in bits)<=f['used']
            bad=bytearray(bits);bad[192*len(values)]^=1
            assert not check_canonical_rows(bad,len(values))[0]
            bad=bytearray(bits);bad[0]=2
            assert not check_canonical_rows(bad,len(values))[0]
            altered=list(values);altered[0]=(Q,0,0,0)
            bad=encode_with_helpers(altered)
            assert check_canonical_rows(bad,len(values))==(False,'equality to q')
            Hbad=[list(v) for v in H];Hbad[0][0]=add(Hbad[0][0],ONE)
            zb,Eb,*_=fold(src,Hbad,c);assert quadratic(zb)!=Eb
            out['cases'].append(dict(k=k,challenge=list(c),used=f['used'],rows=f['field_rows'],rounds=f['field_rounds'],
                                     carrier_pair_residue_agreement=True,all_canonical_constraints_checked=True,
                                     witness_sha256=hashlib.sha256(bits).hexdigest(),honest_witness_energy=sum(bits),
                                     negative_checks=4))
    # Reproduce the original compiler's exact layout and row counts.
    b=front(16,2**20)
    assert b['used']==542977 and b['field_rows']==1351938 and b['field_rounds']==21
    assert b['auxiliary_columns']==4350 and b['carrier_columns']==192
    out['original_front_manifest_reproduced']=True
    return out

if __name__=='__main__':
    result=run();p=Path(__file__).parent/'results'/'frontend-validation.json'
    p.write_bytes((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'));print('front checks passed:',len(result['cases']),'assignments, 9 arities')
