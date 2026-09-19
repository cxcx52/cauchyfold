"""Exact primality and degree-four field certificate checks."""
from pathlib import Path
from math import gcd
import json
ROOT = Path(__file__).resolve().parent

def poly_add(a,b,p):
    c=[0]*max(len(a),len(b))
    for i,x in enumerate(a):c[i]+=x
    for i,x in enumerate(b):c[i]+=x
    return poly_trim([x%p for x in c])


def poly_trim(a):
    a=a[:]
    while len(a)>1 and a[-1]==0:a.pop()
    return a


def poly_scale(a,t,p):return poly_trim([(x*t)%p for x in a])


def poly_mul(a,b,p):
    c=[0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):c[i+j]=(c[i+j]+x*y)%p
    return poly_trim(c)


def ptrim(a,p):
    a=[x%p for x in a]
    while len(a)>1 and a[-1]==0:a.pop()
    return a


def verify_prime_and_field():
    source=json.loads((ROOT/'prime_certificate.json').read_text());cert=source['certificate'];done=set()
    def check(n):
        if n in done:return
        if n==2:
            assert cert[str(n)]=={'base':True};done.add(n);return
        c=cert[str(n)];fac={int(p):e for p,e in c['factorization_n_minus_1'].items()}
        prod=1
        for p,e in fac.items():
            assert e>=1;check(p);prod*=p**e
            a=c['witnesses'][str(p)]
            assert pow(a,n-1,n)==1 and gcd(pow(a,(n-1)//p,n)-1,n)==1
        assert prod==n-1;done.add(n)
    q=source['prime'];check(q)
    def modpoly(a,b):
        a=ptrim(a,q);b=ptrim(b,q)
        while len(a)>=len(b) and a!=[0]:
            shift=len(a)-len(b);c=a[-1]*pow(b[-1],-1,q)%q
            for j,v in enumerate(b):a[j+shift]=(a[j+shift]-c*v)%q
            a=ptrim(a,q)
        return a
    def pgcd(a,b):
        while b!=[0]:a,b=b,modpoly(a,b)
        return poly_scale(a,pow(a[-1],-1,q),q)
    g=[2,0,-4,0,1]
    def pmul(a,b):return modpoly(poly_mul(a,b,q),g)
    def ppow(a,e):
        out=[1]
        while e:
            if e&1:out=pmul(out,a)
            a=pmul(a,a);e//=2
        return out
    x=[0,1];t=x;frob=[]
    for j in range(4):t=ppow(t,q);frob.append(t)
    assert frob[3]==x
    assert pgcd(g,poly_add(frob[1],[0,-1],q))==[1]
    return {'prime':q,'recursive_prime_nodes':len(done),'full_factorization_certificate_verified':True,'extension_polynomial':[2,0,-4,0,1],'x_q4_mod_g':frob[3],'gcd_x_q2_minus_x_g':[1],'irreducible_degree_4':True,'not_a_hardness_certificate':True}

