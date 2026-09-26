"""Reference components for a CauchyFold communication-compression proposal.

Standard-library only. This is NOT an implementation of the complete protocol.
It implements the new public aggregation and two norm-bounded wire codecs.
All parameters are taken from the attached 63-page manuscript.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt, prod, gcd
from secrets import randbelow
from typing import Iterable, Iterator, Sequence

Q = 2**48 - 59
Element = tuple[int, int, int, int]
ZERO: Element = (0, 0, 0, 0)
ONE: Element = (1, 0, 0, 0)
THETA: Element = (0, 1, 0, 0)


@dataclass(frozen=True)
class Quartic:
    """Arithmetic modulo x^4-4*x^2+2; call the certificate before assuming a field."""
    q: int = Q

    def add(self, a: Element, b: Element) -> Element:
        return tuple((x + y) % self.q for x, y in zip(a, b))

    def scale(self, a: Element, c: int) -> Element:
        return tuple(c * x % self.q for x in a)

    def mul(self, a: Element, b: Element) -> Element:
        t = [0] * 7
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                t[i+j] += x*y
        # x^4 = 4*x^2 - 2. Descending reduction includes newly formed terms.
        for i in range(6, 3, -1):
            t[i-2] += 4*t[i]
            t[i-4] -= 2*t[i]
        return tuple(t[i] % self.q for i in range(4))

    def theta_mul(self, a: Element) -> Element:
        a0, a1, a2, a3 = a
        return (-2*a3 % self.q, a0, (a1+4*a3) % self.q, a2)

    def pow(self, a: Element, n: int) -> Element:
        if n < 0:
            raise ValueError("negative exponents are not accepted")
        out = ONE
        while n:
            if n & 1:
                out = self.mul(out, a)
            a = self.mul(a, a)
            n >>= 1
        return out

    def sample(self) -> Element:
        # Exact uniform field coefficients, not reduction of a fixed-length seed.
        return tuple(randbelow(self.q) for _ in range(4))

    def canonical(self, a: Sequence[int]) -> bool:
        return len(a) == 4 and all(type(x) is int and 0 <= x < self.q for x in a)


def _poly_trim(a: list[int], q: int) -> list[int]:
    a = [x % q for x in a]
    while a and a[-1] == 0:
        a.pop()
    return a


def _poly_rem(a: list[int], b: list[int], q: int) -> list[int]:
    a = _poly_trim(a, q)
    b = _poly_trim(b, q)
    if not b:
        raise ZeroDivisionError("zero polynomial")
    inv = pow(b[-1], -1, q)
    while len(a) >= len(b):
        shift, c = len(a)-len(b), a[-1]*inv % q
        for j, x in enumerate(b):
            a[j+shift] = (a[j+shift]-c*x) % q
        a = _poly_trim(a, q)
    return a


def poly_gcd(a: list[int], b: list[int], q: int) -> list[int]:
    a, b = _poly_trim(a, q), _poly_trim(b, q)
    while b:
        a, b = b, _poly_rem(a, b, q)
    return [(x*pow(a[-1], -1, q)) % q for x in a] if a else []


def trial_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % d for d in range(3, isqrt(n)+1, 2))


def concrete_field_certificate() -> dict:
    """Deterministic Lucas primality certificate and degree-four Rabin test."""
    factors = {2: 2, 797: 1, 2459: 1, 35905663: 1}
    if prod(p**e for p, e in factors.items()) != Q-1:
        raise AssertionError("wrong factorization")
    if not all(trial_prime(p) for p in factors):
        raise AssertionError("a claimed prime factor is composite")
    witness = next(a for a in range(2, 1000)
                   if pow(a, Q-1, Q) == 1 and
                   all(gcd(pow(a, (Q-1)//p, Q)-1, Q) == 1 for p in factors))
    f = Quartic()
    xq2 = f.pow(THETA, Q*Q)
    xq4 = f.pow(THETA, Q**4)
    g = list(xq2)
    g[1] -= 1
    divisor = poly_gcd([2, 0, -4, 0, 1], g, Q)
    if xq4 != THETA or divisor != [1]:
        raise AssertionError("the extension polynomial failed irreducibility")
    return {
        "q": Q, "q_minus_one_prime_factors": factors,
        "lucas_witness": witness,
        "lucas_residues": {str(p): pow(witness, (Q-1)//p, Q) for p in factors},
        "all_prime_factors_checked_by_trial_division": True,
        "theta_to_q_squared": xq2, "theta_to_q_fourth": xq4,
        "gcd_x_to_q_squared_minus_x_with_modulus": divisor,
        "primality_and_irreducibility_certificates_verified": True,
    }


def aggregation_columns(m: int, rho: Element, delta: Element,
                        field: Quartic | None = None) -> Iterator[tuple[int, int, int]]:
    """Column j is first3(delta * theta^(j mod 4) * rho^(j//4)).

    Group four Fq residual entries into one extension coefficient.
    One multiplication by rho is needed between consecutive four-entry groups.
    No public matrix is materialized. The three rows are NOT iid vectors.
    The 42-byte protocol samples delta[3]=1; the arithmetic identity also works
    for other canonical delta values, which some algebra-only tests exercise.
    """
    f = field or Quartic()
    if type(m) is not int or m < 1:
        raise ValueError("m must be a positive integer")
    if not f.canonical(rho) or not f.canonical(delta):
        raise ValueError("noncanonical challenge coefficients")
    mu, produced = delta, 0
    while produced < m:
        v = mu
        for s in range(min(4, m-produced)):
            if s:
                v = f.theta_mul(v)
            yield v[:3]
            produced += 1
        if produced < m:
            mu = f.mul(mu, rho)


def aggregate_residual(residual: Sequence[int], rho: Element, delta: Element,
                       field: Quartic | None = None) -> tuple[int, int, int]:
    f = field or Quartic()
    if not residual:
        raise ValueError("empty residual")
    out = [0, 0, 0]
    for r, col in zip(residual, aggregation_columns(len(residual), rho, delta, f)):
        if type(r) is not int or not 0 <= r < f.q:
            raise ValueError("residual must have canonical Fq entries")
        for e in range(3):
            out[e] = (out[e] + r*col[e]) % f.q
    return tuple(out)


def packed_evaluation(residual: Sequence[int], rho: Element,
                      field: Quartic | None = None) -> Element:
    """Independent Horner ordering for checking the aggregation identity."""
    f = field or Quartic()
    out = ZERO
    for start in reversed(range(0, len(residual), 4)):
        a = tuple(residual[start:start+4])
        a = a + (0,)*(4-len(a))
        out = f.add(f.mul(out, rho), a)
    return out


def sample_aggregation_challenge() -> tuple[Element, Element]:
    """Exact uniform rho in K and delta in the affine hyperplane delta[3]=1."""
    f = Quartic()
    rho = f.sample()
    delta = (randbelow(Q), randbelow(Q), randbelow(Q), 1)
    return rho, delta


def encode_challenge(rho: Element, delta: Element) -> bytes:
    f = Quartic()
    if not f.canonical(rho) or not f.canonical(delta) or delta[3] != 1:
        raise ValueError("challenge must be canonical with delta[3]=1")
    # The fourth multiplier coefficient is the PUBLIC constant one, not a wire field.
    return b''.join(x.to_bytes(6, 'little') for x in rho+delta[:3])


def decode_challenge(data: bytes) -> tuple[Element, Element]:
    if len(data) != 42:
        raise ValueError("aggregation challenge must be exactly 42 bytes")
    a = tuple(int.from_bytes(data[i:i+6], 'little') for i in range(0, 42, 6))
    if any(x >= Q for x in a):
        raise ValueError("noncanonical Fq coefficient")
    return a[:4], a[4:]+(1,)


class BitWriter:
    def __init__(self, nbytes: int):
        self.data = bytearray(nbytes)
        self.position = 0

    def write(self, value: int, width: int) -> None:
        if width < 0 or value < 0 or value.bit_length() > width:
            raise ValueError("value does not fit bit width")
        if self.position+width > 8*len(self.data):
            raise ValueError("wire capacity exceeded")
        for j in range(width):
            if (value >> j) & 1:
                p = self.position+j
                self.data[p//8] |= 1 << (p % 8)
        self.position += width

    def zeros(self, width: int) -> None:
        if width < 0 or self.position+width > 8*len(self.data):
            raise ValueError("wire capacity exceeded")
        self.position += width


class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.position = 0

    def read(self, width: int) -> int:
        if width < 0 or self.position+width > 8*len(self.data):
            raise ValueError("truncated bit string")
        out = 0
        for j in range(width):
            p = self.position+j
            out |= ((self.data[p//8] >> (p % 8)) & 1) << j
        self.position += width
        return out

    def require_zero_tail(self) -> None:
        while self.position < 8*len(self.data):
            if self.read(1):
                raise ValueError("nonzero unused padding")


@dataclass(frozen=True)
class NormCodec:
    """Canonical fixed-length encoding of integer vectors with sum(v_j^2)<=T.

    fixed: offset-binary coordinates with width ceil(log2(2*floor(sqrt(T))+1)).
    rice: signed Rice code, padded to a proven PUBLIC worst-case byte budget.
    The decoded vector, not the byte string, is passed to the original verifier.
    """
    n: int
    T: int
    mode: str = "fixed"
    k: int | None = None

    def __post_init__(self):
        if type(self.n) is not int or self.n < 1 or type(self.T) is not int or self.T < 0:
            raise ValueError("invalid public norm codec parameters")
        if self.mode not in ("fixed", "rice"):
            raise ValueError("unknown codec mode")
        if self.mode == "rice" and (type(self.k) is not int or self.k < 1):
            raise ValueError("Rice k must be a positive integer")

    @property
    def B(self) -> int:
        return isqrt(self.T)

    @property
    def coordinate_bits(self) -> int:
        return (2*self.B).bit_length()

    @property
    def maximum_bits(self) -> int:
        if self.mode == "fixed":
            return self.n*self.coordinate_bits
        return self.n*(self.k+1) + (isqrt(self.n*self.T) >> (self.k-1))

    @property
    def nbytes(self) -> int:
        return (self.maximum_bits+7)//8

    @classmethod
    def rice_optimized(cls, n: int, T: int) -> NormCodec:
        # Search all relevant k; optimum minimizes the proven bit budget, then k.
        top = max(2, (2*isqrt(T)).bit_length()+2)
        k = min(range(1, top+1),
                key=lambda h: (n*(h+1)+(isqrt(n*T) >> (h-1)), h))
        return cls(n, T, "rice", k)

    def encode(self, values: Sequence[int]) -> bytes:
        if len(values) != self.n or any(type(x) is not int for x in values):
            raise ValueError("wrong vector dimension or noninteger coordinate")
        if sum(x*x for x in values) > self.T:
            raise ValueError("norm threshold exceeded")
        w = BitWriter(self.nbytes)
        for x in values:
            if self.mode == "fixed":
                w.write(x+self.B, self.coordinate_bits)
            else:
                u = 2*x if x >= 0 else -2*x-1
                quotient, rem = divmod(u, 1 << self.k)
                w.zeros(quotient)
                w.write(1, 1)
                w.write(rem, self.k)
        if w.position > self.maximum_bits:
            raise AssertionError("proved bit bound violated")
        return bytes(w.data)

    def decode(self, data: bytes) -> list[int]:
        if len(data) != self.nbytes:
            raise ValueError("wrong fixed payload byte length")
        r = BitReader(data)
        out, energy = [], 0
        for _ in range(self.n):
            if self.mode == "fixed":
                code = r.read(self.coordinate_bits)
                if code > 2*self.B:
                    raise ValueError("unused offset-binary symbol")
                x = code-self.B
            else:
                quotient = 0
                # Both a physical payload cap and a coordinate cap bound this loop.
                while r.read(1) == 0:
                    quotient += 1
                    if quotient > ((2*self.B) >> self.k):
                        raise ValueError("Rice quotient exceeds coordinate cap")
                u = (quotient << self.k) + r.read(self.k)
                x = u//2 if u % 2 == 0 else -(u+1)//2
                if abs(x) > self.B:
                    raise ValueError("coordinate exceeds norm-implied bound")
            energy += x*x
            if energy > self.T:
                raise ValueError("norm threshold exceeded")
            out.append(x)
        if r.position > self.maximum_bits:
            raise ValueError("coded vector exceeds public bit budget")
        r.require_zero_tail()
        return out


def canonical_ring_coefficients(values: Sequence[int], q: int = Q) -> list[int]:
    """Map a verified centered integer vector to the original Fq coefficients."""
    if any(abs(x) > (q-1)//2 for x in values):
        raise ValueError("integer is not the unique centered representative")
    return [x % q for x in values]
