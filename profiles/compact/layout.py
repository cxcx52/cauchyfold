"""Canonical front-end dimensions and fixed-capacity Rice coding."""
from __future__ import annotations
from functools import lru_cache
from math import isqrt

Q = 2**48 - 59
D = 64
RING_BYTES = 384

def ceildiv(a:int,b:int)->int:
    return (a+b-1)//b

def ceil_log2(n:int)->int:
    assert n>0
    return (n-1).bit_length()

def front(k:int,capacity:int|None=None,split_aux:bool=False, *, rank:int)->dict:
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
                initial_linear_rows=(k+3+len(aux_chunks))*rank*D+13+(cap-used),
                wrapper_p_bytes=(2+len(aux_chunks))*rank*RING_BYTES+96*ell+72,
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
