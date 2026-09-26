"""Exact fixed-Nisan reference operator for validation, not a large benchmark.

All seed bits are specified: x then increasing-level (a,b), each LSB first.
No random coins are sampled by Eval/Adj. Only Gen consumes fresh OS random bits.
"""
from dataclasses import dataclass
import secrets


@dataclass(frozen=True)
class Descriptor:
    n: int
    k: int
    x: int
    hashes: tuple

    def __post_init__(self):
        if self.n < 1 or self.k < 0 or len(self.hashes) != self.k:
            raise ValueError('invalid descriptor shape')
        if not 0 <= self.x < 1 << self.n:
            raise ValueError('invalid x')
        for a,b in self.hashes:
            if not 0 <= a < 1 << (2*self.n-1) or not 0 <= b < 1 << self.n:
                raise ValueError('invalid hash')

    @property
    def bits(self):
        return self.n + self.k*(3*self.n-1)

    def to_bytes(self):
        value, pos = self.x, self.n
        for a,b in self.hashes:
            value |= a << pos
            pos += 2*self.n-1
            value |= b << pos
            pos += self.n
        return value.to_bytes((self.bits+7)//8, 'little')

    @classmethod
    def from_bytes(cls, raw, n, k):
        size = n + k*(3*n-1)
        if len(raw) != (size+7)//8:
            raise ValueError('wrong descriptor length')
        value = int.from_bytes(raw, 'little')
        if value >> size:
            raise ValueError('noncanonical padding')
        mask = (1<<n)-1
        x = value & mask
        value >>= n
        hashes = []
        for _ in range(k):
            a = value & ((1<<(2*n-1))-1)
            value >>= 2*n-1
            b = value & mask
            value >>= n
            hashes.append((a,b))
        return cls(n,k,x,tuple(hashes))


def gen(n,k):
    size = n + k*(3*n-1)
    value = secrets.randbits(size)
    return Descriptor.from_bytes(value.to_bytes((size+7)//8,'little'),n,k)


def hash_block(x,a,b,n):
    # Exactly y_j = b_j XOR sum_i a_(i+j) x_i over F_2.
    out = b
    mask = (1<<n)-1
    for j in range(n):
        out ^= (((a>>j)&mask&x).bit_count() & 1) << j
    return out


def block_at(d,index,stats=None):
    if not 0 <= index < 1<<d.k:
        raise ValueError('block outside generator')
    value=d.x
    for level in range(d.k,0,-1):
        if index & (1<<(level-1)):
            a,b=d.hashes[level-1]
            value=hash_block(value,a,b,d.n)
            if stats is not None:
                stats['hash_calls']=stats.get('hash_calls',0)+1
    return value


def iter_blocks(d,count=None,stats=None):
    count = 1<<d.k if count is None else count
    if not 0 <= count <= 1<<d.k:
        raise ValueError('too many blocks')
    def walk(value,level,needed):
        if not needed:
            return
        if level==0:
            yield value
            return
        half=1<<(level-1)
        yield from walk(value,level-1,min(needed,half))
        if needed>half:
            a,b=d.hashes[level-1]
            right=hash_block(value,a,b,d.n)
            if stats is not None:
                stats['hash_calls']=stats.get('hash_calls',0)+1
            yield from walk(right,level-1,needed-half)
    yield from walk(d.x,d.k,count)


def iter_bits(d,limit,stats=None):
    if not 0<=limit<=d.n*(1<<d.k):
        raise ValueError('insufficient generator length')
    left=limit
    for block in iter_blocks(d,(limit+d.n-1)//d.n,stats):
        take=min(left,d.n)
        for j in range(take):
            yield (block>>j)&1
        left-=take


def iter_trits(d,count,stats=None):
    bits=iter(iter_bits(d,2*count,stats))
    for _ in range(count):
        yield next(bits)-next(bits)


def eval_projection(d,w,m,q,stats=None):
    n=len(w)
    trits=iter(iter_trits(d,m*n,stats))
    out=[]
    for _ in range(m):
        value=0
        for z in w:
            trit=next(trits)
            value=(value+trit*z)%q
        out.append(value)
    return out


def adj_projection(d,alpha,N,q,stats=None):
    out=[0]*N
    trits=iter(iter_trits(d,len(alpha)*N,stats))
    for a in alpha:
        for j in range(N):
            out[j]=(out[j]+a*next(trits))%q
    return out


def adj_batch(d,alphas,N,q,stats=None):
    if not alphas or len({len(a) for a in alphas})!=1:
        raise ValueError('nonempty equal-length rows required')
    m=len(alphas[0])
    out=[[0]*N for _ in alphas]
    trits=iter(iter_trits(d,m*N,stats))
    for i in range(m):
        for j in range(N):
            z=next(trits)
            for row,a in zip(out,alphas):
                row[j]=(row[j]+a[i]*z)%q
    return out


def centered(x,q):
    x%=q
    return x-q if x>q//2 else x
