"""Exact k=1024 accounting. Does not run or approximate lattice attacks."""
from fractions import Fraction as F
from math import isqrt, log2
from pathlib import Path
import json
Q=2**48-59; D=64; K=1024; M=5**64; PROJ=384; TAU=3; RP=RC=160
PATH=((30,64),(14,128),(8,128),(6,128),(5,None))
PIN='53da5982597709ba0fdf94ea37a84d822310fd84'
ROOT=Path(__file__).resolve().parents[1]
def cd(a,b):return (a+b-1)//b
def cl2(n):return (n-1).bit_length()
def csqrt(n):
 r=isqrt(n);return r+int(r*r<n)
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 # Write canonical UTF-8/LF bytes on every supported host.  Text-mode writes
 # otherwise translate LF to CRLF on Windows and change recorded hashes.
 p.write_bytes((json.dumps(x,indent=2,sort_keys=True)+'\n').encode('utf-8'))
def rf(x):return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
def rice(n,T):
 root=isqrt(n*T)
 bits,j=min((n*(j+1)+(root>>(j-1)),j) for j in range(1,65))
 return dict(n=n,T=T,k=j,bits=bits,bytes=cd(bits,8))
def seed(N,S):
 R=2*PROJ*N;T=PROJ*S;w=cl2((R+1)*4*Q*(T+2));kk=cl2(R)
 b=6*w+2*kk+450+cl2(kk)+3;h=cl2(cd(R,b));bits=b+h*(3*b-1)
 delta=F(1,2**150*2*(2**h-1))
 err=(2**h-1)*delta+F(2**(6*w)*h,2**b)/delta**2
 assert err<F(1,2**150)
 assert F(1,2*(T+1))>F(1,2**150) # honest integrality margin
 return dict(N=N,S=S,R=R,T=T,w=w,b=b,h=h,bits=bits,bytes=cd(bits,8),
             prefix_hashes=cd(R,b)-1,error=rf(err))
def build():
 used=29568*K+69889;rows=46109*K+108595;ell=cl2(rows)
 p=3*32*384+96*ell+72;v=24+48*ell;roles=[]
 def reg(name,a,b,beta):
  assert min(a,b,beta)>0 and beta<Q
  roles.append(dict(matrix_id=name,q=Q,d=D,rows=a,columns=b,beta=beta,
   expanded_sis=dict(n=D*a,m=D*b,norm=2,length_bound=beta),
   estimator_commit=PIN,status='READY_NOT_ESTIMATED'))
 b0=csqrt(64*used)
 reg('A_st',32,219,b0);reg('A_H',32,12*K,b0);reg('A_aux',32,231*K+654,b0)
 raw=S=used;lr=64*32*(K+4)+13;layers=[]
 for i,(s,rho) in enumerate(PATH):
  n=cd(raw,64*s);N=64*s*n;pad=N-raw;R=lr+pad+PROJ;deg=cd(R,4)-1
  sd=seed(N,S);pc=rice(PROJ,PROJ*S)
  assert Q*Q>=176**2*16*S and F(4121,100)*16>PROJ
  rec=dict(i=i,s=s,rho=rho,n=n,N=N,raw=raw,S=S,padding=pad,
   linear_rows=lr+pad,augmented_rows=R,aggregation_degree=deg,seed=sd,projection_codec=pc)
  vi=sd['bytes']+42+24*s
  if rho:
   ellr=cd(48,rho.bit_length()-1);dig=rho//2;G=256*S
   bt=ellr*28*s;bh=ellr*3*s*(s+1)//2
   raw1=128*n+64*(bt+bh)
   S1=64*n*dig**2+cd(2*G+128*n*dig**2,rho**2)+64*(bt+bh)*dig**2
   ba=csqrt(1024**2*(1+rho**2)*16*S1);bx=csqrt(64*S1)
   reg(f'A_{i}',28,n,ba);reg(f'B_{i}',16,bt,bx);reg(f'D_{i}',16,bh,bx)
   pi=12288+pc['bytes']+2
   rec.update(G=G,next_raw=raw1,next_S=S1,digits=ellr,bt_columns=bt,bh_columns=bh,beta_A=ba,beta_aux=bx)
   raw,S,lr=raw1,S1,64*(16+16+28+3)+3
  else:
   G=cd(256*M*S,M-1);zc=rice(64*n,G);ba=csqrt(1024**2*G)
   reg(f'A_{i}',28,n,ba);reg('B_pivot',4,28*16,csqrt(8**2*64*28*16))
   pi=(s-1)*28*384+4*384+pc['bytes']+3*s*(s+1)//2*384-18+zc['bytes']+2
   rec.update(G=G,beta_A=ba,terminal_codec=zc)
  rec.update(p_bytes=pi,v_bytes=vi);p+=pi;v+=vi;layers.append(rec)
 proj=len(layers)*RP*(F(1,2**192)+F(1,2**150))
 coord=3*RC*(F(sum(x['s'] for x in layers)-1,M)+F(1,M-1))
 agg=sum((F(1,Q**3)+(1-F(1,Q**3))*F(x['aggregation_degree'],Q**4) for x in layers),F(0))
 field=F(4*ell,Q**4);cauchy=F(2*K,Q**4-K);stat=proj+coord+agg+field+cauchy
 assert stat<F(1,2**130)
 extra=sum(x['seed']['bytes']+24*x['s']+2 for x in layers)
 out=dict(status='CANDIDATE_WITH_EXACT_ARITHMETIC_NOT_FULL_SECURITY_CERTIFICATE',k=K,q=Q,d=D,
  field_rounds=ell,field_rows=rows,field_padded_rows=1<<ell,used=used,values=77*K+182,
  main_rank=28,aux_rank=16,front_rank=32,pivot_rank=4,projection_rows=PROJ,
  P_bytes=p,V_bytes=v,total_bytes=p+v,layers=layers,roles=roles,
  statistical_terms={n:rf(t) for n,t in [('projection',proj),('coordinate',coord),('aggregation',agg),('field',field),('cauchy',cauchy)]},
  statistical_error=rf(stat),statistical_neglog2=log2(stat.denominator)-log2(stat.numerator),
  exact_less_than_2_to_minus_130=True,crs_bytes=sum(384*r['rows']*r['columns'] for r in roles),
  projection_trits=sum(PROJ*x['N'] for x in layers),
  fresh_commitment_bytes=K*32*384,all_input_commitment_bytes=(K+1)*32*384,
  max_accepted_bytes=p+v+159*extra,unconditional_honest_expected_bytes_strict_upper=p+v+extra,
  honest_exhaustion_bound=rf(F(2*len(layers),2**160)))
 assert out['total_bytes']==280832 and out['crs_bytes']==3474533376
 assert len(roles)==17
 return out
if __name__=='__main__':
 x=build();dump(ROOT/'artifacts/parameters.json',x)
 dump(ROOT/'artifacts/estimator-inputs.json',dict(estimator_commit=PIN,roles=x['roles']))
 print(json.dumps({k:x[k] for k in ['total_bytes','P_bytes','V_bytes','crs_bytes','statistical_neglog2']}))
