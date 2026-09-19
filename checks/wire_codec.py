"""Canonical scalar/packed-symbol codecs for the concrete-v1 ledger.

These are message component codecs, not a prover or a full node verifier.
"""
Q=281474976710597

def encode_fq(v):
    if not isinstance(v,int) or not 0<=v<Q:raise ValueError('noncanonical Fq')
    return v.to_bytes(6,'little')

def decode_fq(b):
    if len(b)!=6:raise ValueError('Fq length')
    v=int.from_bytes(b,'little')
    if v>=Q:raise ValueError('noncanonical Fq')
    return v

def encode_symbols(values,alphabet,width):
    acc=0;out=bytearray();used=0
    for v in values:
        if v not in alphabet:raise ValueError('symbol')
        acc |= alphabet.index(v)<<used;used+=width
        while used>=8:
            out.append(acc&255);acc>>=8;used-=8
    if used:out.append(acc)
    return bytes(out)

def decode_symbols(b,count,alphabet,width):
    if len(b)!=(count*width+7)//8:raise ValueError('packed length')
    if count*width%8 and b[-1]>>(count*width%8):raise ValueError('padding')
    acc=int.from_bytes(b,'little');mask=(1<<width)-1;out=[]
    for _ in range(count):
        v=acc&mask;acc>>=width
        if v>=len(alphabet):raise ValueError('reserved code')
        out.append(alphabet[v])
    return out

def check_components():
    valid=[0,1,Q//2,Q//2+1,Q-2,Q-1]
    for v in valid:assert decode_fq(encode_fq(v))==v
    reject=0
    for b in [Q.to_bytes(6,'little'),b'\xff'*6,b'\x00'*5,b'\x00'*7]:
        try:decode_fq(b)
        except ValueError:reject+=1
        else:raise AssertionError('accepted noncanonical field encoding')
    for alphabet,width in [([0,1,-1],2),([-2,-1,0,1,2],3)]:
        for count in range(1,19):
            values=[alphabet[i%len(alphabet)] for i in range(count)]
            b=encode_symbols(values,alphabet,width)
            assert len(b)==(count*width+7)//8
            assert decode_symbols(b,count,alphabet,width)==values
        try:decode_symbols(bytes([len(alphabet)]),1,alphabet,width)
        except ValueError:reject+=1
        else:raise AssertionError('accepted reserved symbol')
        try:decode_symbols(b'\x80',1,alphabet,width)
        except ValueError:reject+=1
        else:raise AssertionError('accepted nonzero padding')
    return {'status':'COMPONENT_CODEC_LENGTH_AND_CANONICALITY_CHECKS_PASS',
      'field_boundary_roundtrips':len(valid),'packed_symbol_roundtrips':36,
      'malformed_inputs_rejected':reject,'full_node_proof_generated':False,
      'scope':'Ledger representation checks only; no protocol smoke or benchmark.'}
