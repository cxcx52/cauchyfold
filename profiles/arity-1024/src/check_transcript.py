"""Strict canonical grammar for the proposed k=1024 transcript.

IMPORTANT: parse() is a syntax/norm/field-sumcheck verifier, NOT a verifier for
lattice commitment or principal equations. It never labels a full proof valid.
The explicit byte values RETRY=0, ACCEPT=1 are new serialization choices.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json, hashlib
from compression import Quartic, NormCodec, decode_challenge
from profile import Q, build, ROOT, dump
F=Quartic(); Z=(0,0,0,0); O=(1,0,0,0)
RETRY=0; ACCEPT=1

def add(a,b): return F.add(a,b)
def sub(a,b): return tuple((x-y)%Q for x,y in zip(a,b))
def mul(a,b): return F.mul(a,b)
def polynomial(c,x):
    v=Z
    for a in reversed(c): v=add(mul(v,x),a)
    return v

def pack_fields(a):
    if any(type(x) is not int or not 0<=x<Q for x in a): raise ValueError('noncanonical coefficient')
    return b''.join(x.to_bytes(6,'little') for x in a)
def pack_K(a): return pack_fields(a)

def decode_fields(data):
    if len(data)%6: raise ValueError('unaligned Fq payload')
    a=[int.from_bytes(data[i:i+6],'little') for i in range(0,len(data),6)]
    if any(x>=Q for x in a): raise ValueError('coefficient >= q')
    return a

def pack_short(vectors):
    out=bytearray()
    for v in vectors:
        if len(v)!=64 or any(type(x) is not int or not -2<=x<=2 for x in v):
            raise ValueError('invalid short challenge')
        n=sum((x+2)<<(3*j) for j,x in enumerate(v))
        out.extend(n.to_bytes(24,'little'))
    return bytes(out)

def decode_short(data,s,terminal):
    if len(data)!=24*s: raise ValueError('short challenge size')
    for i in range(s):
        n=int.from_bytes(data[24*i:24*i+24],'little'); nonzero=False
        for j in range(64):
            v=(n>>(3*j))&7
            if v>4: raise ValueError('unused short-challenge symbol')
            nonzero |= v!=2
        if terminal and i==0 and not nonzero: raise ValueError('zero pivot challenge')

class Reader:
    def __init__(self,data):
        self.data=memoryview(data);self.pos=0;self.messages=[];self.totals={'P':0,'V':0}
    def read(self,n,name,party):
        if type(n) is not int or n<0 or self.pos+n>len(self.data): raise ValueError('truncated '+name)
        start=self.pos;self.pos+=n;self.totals[party]+=n
        self.messages.append(dict(name=name,party=party,offset=start,bytes=n))
        return bytes(self.data[start:self.pos])
    def fields(self,n,name,party): return decode_fields(self.read(6*n,name,party))
    def K(self,name,party): return tuple(self.fields(4,name,party))
    def tag(self,name):
        x=self.read(1,name,'P')[0]
        if x not in (RETRY,ACCEPT): raise ValueError('invalid retry tag')
        return x

def field_part(rd:Reader,ell:int):
    r=[rd.K(f'field.r.{j}','V') for j in range(ell)]
    claim=Z; eq=O; taus=[]
    for j in range(ell):
        a=rd.fields(16,f'field.g.{j}','P');g=[tuple(a[4*i:4*i+4]) for i in range(4)]
        if add(g[0],polynomial(g,O))!=claim: raise ValueError('field round consistency')
        t=rd.K(f'field.tau.{j}','V');taus.append(t);claim=polynomial(g,t)
        eq=mul(eq,add(mul(r[j],t),mul(sub(O,r[j]),sub(O,t))))
    a=rd.fields(12,'field.terminals','P');u=[tuple(a[4*i:4*i+4]) for i in range(3)]
    if claim!=mul(eq,sub(mul(u[0],u[1]),u[2])): raise ValueError('field terminal equation')
    return dict(taus=taus,terminal_values=u,
                conditional_on_terminal_linear_claims=True)

def verify_field_bytes(data,ell):
    r=Reader(data);result=field_part(r,ell)
    if r.pos!=len(data): raise ValueError('trailing field bytes')
    return result

def codec(d):
    c=NormCodec(d['n'],d['T'],'rice',d['k'])
    if c.nbytes!=d['bytes'] or c.maximum_bits!=d['bits']: raise ValueError('codec profile mismatch')
    return c

def parse(data:bytes,profile:dict|None=None):
    expected=build()
    if profile is not None and profile!=expected:raise ValueError('unsupported or modified profile')
    p=expected;r=Reader(data)
    if len(data)>p['max_accepted_bytes']:raise ValueError('global accepted-transcript length cap')
    r.fields(32*64,'front.carrier_commitment','P')
    c=r.K('front.cauchy_challenge','V')
    if c[1:]==(0,0,0) and c[0]<p['k']: raise ValueError('Cauchy challenge is a pole')
    r.fields(32*64,'front.output_commitment','P');r.fields(32*64,'front.aux_commitment','P')
    field=field_part(r,p['field_rounds']);retries=[]
    for layer in p['layers']:
        i=layer['i'];s=layer['s'];terminal=layer['rho'] is None
        if terminal:
            r.fields((s-1)*28*64,f'L{i}.disclosed_commitments','P')
            r.fields(4*64,f'L{i}.pivot_commitment','P')
        else:r.fields(16*64,f'L{i}.u1','P')
        for attempt in range(160):
            seed=r.read(layer['seed']['bytes'],f'L{i}.seed.{attempt}','V')
            if int.from_bytes(seed[-1:],'little')>>(8-(8*len(seed)-layer['seed']['bits'])):
                # The expression also works when no padding bits are present.
                raise ValueError('nonzero seed tail')
            if r.tag(f'L{i}.projection_tag.{attempt}')==ACCEPT:
                codec(layer['projection_codec']).decode(r.read(layer['projection_codec']['bytes'],f'L{i}.projection','P'))
                break
        else: raise ValueError('projection retry exhaustion')
        pa=attempt
        decode_challenge(r.read(42,f'L{i}.aggregation','V'))
        if terminal:r.fields(3*s*(s+1)//2*64-3,f'L{i}.symmetric_data','P')
        else:r.fields(16*64,f'L{i}.u2','P')
        for attempt in range(160):
            decode_short(r.read(24*s,f'L{i}.short_challenge.{attempt}','V'),s,terminal)
            if r.tag(f'L{i}.response_tag.{attempt}')==ACCEPT:
                if terminal:codec(layer['terminal_codec']).decode(r.read(layer['terminal_codec']['bytes'],f'L{i}.response','P'))
                break
        else:raise ValueError('short-response retry exhaustion')
        retries.append(dict(layer=i,projection_retries=pa,response_retries=attempt))
    if r.pos!=len(data):raise ValueError('trailing transcript bytes')
    return dict(status='SYNTAX_NORMS_AND_FIELD_EQUATIONS_VALID_NOT_FULL_PROOF_VERIFICATION',
       bytes=r.pos,P_bytes=r.totals['P'],V_bytes=r.totals['V'],messages=r.messages,retries=retries,
       field=field,lattice_commitment_equations_checked=False,principal_equations_checked=False,
       public_projection_adjoint_checked=False)


def synthetic_fixture(field_bytes:bytes,retries:int=0):
    """A grammar fixture, NOT an honest proof: lattice payloads are placeholders."""
    if not 0<=retries<=159:raise ValueError('retry fixture range')
    p=build();out=bytearray()
    def put(x):out.extend(x)
    put(bytes(32*384));put(pack_K((p['k']+17,3,4,5)))
    put(bytes(2*32*384));put(field_bytes)
    for L in p['layers']:
        s=L['s'];terminal=L['rho'] is None
        put(bytes(((s-1)*28+4)*384 if terminal else 16*384))
        for _ in range(retries):put(bytes(L['seed']['bytes']));put(bytes([RETRY]))
        put(bytes(L['seed']['bytes']));put(bytes([ACCEPT]));put(codec(L['projection_codec']).encode([0]*L['projection_codec']['n']))
        put(pack_fields([0]*7)) # zeta=0, chi=(0,0,0,1) is an allowed challenge.
        put(bytes((3*s*(s+1)//2*64-3)*6 if terminal else 16*384))
        ch=pack_short([[1]+[0]*63]+[[0]*64 for _ in range(s-1)])
        for _ in range(retries):put(ch);put(bytes([RETRY]))
        put(ch);put(bytes([ACCEPT]))
        if terminal:put(codec(L['terminal_codec']).encode([0]*L['terminal_codec']['n']))
    return bytes(out)

def tests():
    p=build();field=(ROOT/'artifacts/field/transcript.bin').read_bytes()
    independent=verify_field_bytes(field,p['field_rounds'])
    data=synthetic_fixture(field);result=parse(data,p)
    assert len(data)==p['total_bytes'] and result['P_bytes']==p['P_bytes'] and result['V_bytes']==p['V_bytes']
    offsets={x['name']:x for x in result['messages']};negative=[]
    def bad(name,fn):
        b=bytearray(data);fn(b)
        try:parse(bytes(b),p)
        except ValueError as e:negative.append(dict(test=name,rejected=True,reason=str(e)));return
        raise AssertionError('negative case accepted: '+name)
    def overwrite(name,content,relative=0):
        def mutate(b):
            i=offsets[name]['offset']+relative;b[i:i+len(content)]=content
        return mutate
    bad('coefficient_equal_to_q',overwrite('front.carrier_commitment',Q.to_bytes(6,'little')))
    bad('cauchy_pole',overwrite('front.cauchy_challenge',bytes(24)))
    bad('noncanonical_aggregation',overwrite('L0.aggregation',Q.to_bytes(6,'little')))
    bad('invalid_tag',overwrite('L0.projection_tag.0',bytes([2])))
    bad('noncanonical_seed_tail',overwrite('L0.seed.0',bytes([128]),p['layers'][0]['seed']['bytes']-1))
    bad('invalid_short_symbol',overwrite('L0.short_challenge.0',bytes([255])))
    bad('zero_pivot_challenge',overwrite('L4.short_challenge.0',pack_short([[0]*64])))
    bad('projection_codec_tail',overwrite('L0.projection',bytes([128]),p['layers'][0]['projection_codec']['bytes']-1))
    bad('terminal_codec_tail',overwrite('L4.response',bytes([128]),p['layers'][4]['terminal_codec']['bytes']-1))
    bad('field_round_changed',overwrite('field.g.0',pack_K(O)))
    bad('truncated',lambda b:b.__delitem__(slice(len(b)-1,len(b))))
    bad('trailer',lambda b:b.extend(b'\0'))
    # Additional retries are genuine grammar branches; failed attempts carry no payload.
    maxdata=synthetic_fixture(field,159);maxresult=parse(maxdata,p)
    assert len(maxdata)==p['max_accepted_bytes'] and all(x['projection_retries']==159 and x['response_retries']==159 for x in maxresult['retries'])
    # Turn the 160th projection ACCEPT into RETRY; a 161st trial must not be read.
    event=next(x for x in maxresult['messages'] if x['name']=='L0.projection_tag.159')
    b=bytearray(maxdata);b[event['offset']]=RETRY
    try:parse(bytes(b),p)
    except ValueError as e:negative.append(dict(test='160_retry_exhaustion',rejected=True,reason=str(e)))
    else:raise AssertionError('retry exhaustion accepted')
    output=dict(status='PASS',fixture_is_not_a_full_proof=True,full_lattice_protocol_verified=False,
       independently_verified_actual_field_transcript=True,field_wire_bytes=len(field),
       no_retry_bytes=len(data),max_retry_bytes=len(maxdata),negative_cases=negative,
       profile_sha256=hashlib.sha256((ROOT/'artifacts/parameters.json').read_bytes()).hexdigest())
    (ROOT/'artifacts/wire').mkdir(exist_ok=True)
    (ROOT/'artifacts/wire/SYNTHETIC_SYNTAX_NOT_A_PROOF.bin').write_bytes(data)
    dump(ROOT/'artifacts/wire/message_offsets.json',result['messages'])
    dump(ROOT/'evidence/parser-checks.json',output)
    dump(ROOT/'evidence/field-checks.json',dict(status='PASS',**independent,
        full_lattice_protocol_verified=False,implementation='Python Quartic arithmetic independent of C++'))
    return output

if __name__=='__main__':
    print(json.dumps(tests(),indent=2))
