"""Executable factored CauchyFold child equations, over F_q[X]/(X^d+1).

This is an arithmetic reference, not a wire codec or a production prover.
Scalar vectors are coefficient-major within each ring element. Digit layout is
target-ring-major, radix-digit-major, coefficient-major. Public B/D columns
must use that convention. No dense projection or scalar child matrix is built.
"""

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

Poly = tuple[int, ...]


@dataclass(frozen=True)
class NegacyclicRing:
    q: int
    degree: int

    def __post_init__(self):
        # Primality is a public parameter precondition, not tested by this class.
        if self.q < 3 or self.q % 2 == 0 or self.degree < 1:
            raise ValueError("odd prime modulus and positive degree required")

    def poly(self, coefficients: Sequence[int]) -> Poly:
        if len(coefficients) != self.degree:
            raise ValueError("ring coefficient length")
        return tuple(int(c) % self.q for c in coefficients)

    def zero(self) -> Poly:
        return (0,) * self.degree

    def scalar(self, c: int) -> Poly:
        return (c % self.q,) + (0,) * (self.degree - 1)

    def add(self, a: Poly, b: Poly) -> Poly:
        return tuple((x+y) % self.q for x, y in zip(a, b))

    def sub(self, a: Poly, b: Poly) -> Poly:
        return tuple((x-y) % self.q for x, y in zip(a, b))

    def scale(self, a: Poly, c: int) -> Poly:
        return tuple(c*x % self.q for x in a)

    def mul(self, a: Poly, b: Poly) -> Poly:
        out = [0] * self.degree
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                index = i+j
                out[index % self.degree] += x*y if index < self.degree else -x*y
        return tuple(x % self.q for x in out)

    def star(self, a: Poly) -> Poly:
        """Coefficient-space adjoint involution a(X^{-1}); also CT lift iota."""
        return (a[0],) + tuple(-a[self.degree-j] % self.q
                               for j in range(1, self.degree))

    def dot(self, a: Sequence[Poly], b: Sequence[Poly]) -> Poly:
        if len(a) != len(b):
            raise ValueError("ring inner-product shape")
        out = self.zero()
        for x, y in zip(a, b):
            out = self.add(out, self.mul(x, y))
        return out

    def centered(self, a: Poly) -> tuple[int, ...]:
        return tuple(x if x <= self.q//2 else x-self.q for x in a)

    def inverse(self, a: Poly) -> Poly:
        """Public unit inverse via polynomial Euclid, not a short integer inverse."""
        q = self.q

        def trim(p):
            p = [x % q for x in p]
            while p and p[-1] == 0:
                p.pop()
            return p

        def subtract(a_, b_):
            out = list(a_) + [0]*max(0, len(b_)-len(a_))
            for j, x in enumerate(b_):
                out[j] = (out[j]-x) % q
            return trim(out)

        def multiply(a_, b_):
            if not a_ or not b_:
                return []
            out = [0]*(len(a_)+len(b_)-1)
            for i, x in enumerate(a_):
                for j, y in enumerate(b_):
                    out[i+j] = (out[i+j]+x*y) % q
            return trim(out)

        def divide(a_, b_):
            remainder = trim(a_)
            divisor = trim(b_)
            if not divisor:
                raise ZeroDivisionError
            quotient = [0]*max(0, len(remainder)-len(divisor)+1)
            inv_lead = pow(divisor[-1], -1, q)
            while remainder and len(remainder) >= len(divisor):
                shift = len(remainder)-len(divisor)
                factor = remainder[-1]*inv_lead % q
                quotient[shift] = factor
                for j, value in enumerate(divisor):
                    remainder[shift+j] = (remainder[shift+j]-factor*value) % q
                remainder = trim(remainder)
            return trim(quotient), remainder

        modulus = [1]+[0]*(self.degree-1)+[1]
        old_r, new_r = modulus, trim(a)
        old_t, new_t = [], [1]
        while new_r:
            quotient, remainder = divide(old_r, new_r)
            old_r, new_r = new_r, remainder
            old_t, new_t = new_t, subtract(old_t, multiply(quotient, new_t))
        if len(old_r) != 1:
            raise ValueError("challenge is not a ring unit")
        _, reduced = divide([x*pow(old_r[0], -1, q) % q for x in old_t], modulus)
        answer = self.poly(reduced+[0]*(self.degree-len(reduced)))
        if self.mul(a, answer) != self.scalar(1):
            raise AssertionError("inverse implementation")
        return answer


def flatten(polynomials: Sequence[Poly]) -> list[int]:
    return [c for p in polynomials for c in p]


def unflatten(ring: NegacyclicRing, values: Sequence[int]) -> list[Poly]:
    if len(values) % ring.degree:
        raise ValueError("incomplete ring coefficient block")
    return [ring.poly(values[i:i+ring.degree])
            for i in range(0, len(values), ring.degree)]


@dataclass(frozen=True)
class RingMatrix:
    """Immutable explicit public ring matrix; may be shared between fork objects."""
    ring: NegacyclicRing
    data: tuple[tuple[Poly, ...], ...]

    @classmethod
    def from_rows(cls, ring, rows):
        rows = tuple(tuple(ring.poly(p) for p in row) for row in rows)
        if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("nonempty rectangular ring matrix required")
        return cls(ring, rows)

    @property
    def rows(self):
        return len(self.data)

    @property
    def cols(self):
        return len(self.data[0])

    def apply(self, vector):
        if len(vector) != self.cols:
            raise ValueError("ring matrix input shape")
        return [self.ring.dot(row, vector) for row in self.data]

    def transpose(self, dual):
        """Transpose in the scalar coefficient pairing, not plain ring transpose."""
        if len(dual) != self.rows:
            raise ValueError("ring matrix dual shape")
        out = [self.ring.zero() for _ in range(self.cols)]
        for i, row in enumerate(self.data):
            for j, entry in enumerate(row):
                out[j] = self.ring.add(out[j], self.ring.mul(self.ring.star(entry), dual[i]))
        return out


class ScalarOperator(Protocol):
    rows: int
    cols: int

    def apply(self, vector: Sequence[int]) -> list[int]: ...
    def transpose(self, dual: Sequence[int]) -> list[int]: ...


@dataclass(frozen=True)
class AggregationCache:
    ring: NegacyclicRing
    s: int
    n: int
    # phi[e] contains s*n ring elements, j-major then witness coordinate.
    phi: tuple[tuple[Poly, ...], ...]
    b: tuple[int, ...]

    @property
    def tau(self):
        return len(self.b)

    @property
    def scalar_cache_size(self):
        return self.tau*self.s*self.n*self.ring.degree


def prepare_aggregation(ring: NegacyclicRing, s: int, n: int,
                        previous: ScalarOperator, y: Sequence[int],
                        descriptor: Any, p: Sequence[int],
                        alpha_l: Sequence[Sequence[int]],
                        alpha_p: Sequence[Sequence[int]],
                        adj_callback: Callable[[Any, Sequence[int], int, int], Sequence[int]] | None = None,
                        *, adj_batch_callback: Callable | None = None) -> AggregationCache:
    """Compute/cache phi from the SAME projection descriptor and previous transpose.

    adj_callback has root reference signature adj_projection(d,alpha,N,q).
    The intended one-scan mode uses adj_batch_callback(d,alpha_p,N,q);
    the single-row fallback deliberately performs tau separate scans.
    It must implement the selected descriptor, not an unrelated operator.
    Neither descriptor nor previous operator is retained by the returned cache.
    """
    size = ring.degree*s*n
    if previous.cols != size or len(y) != previous.rows:
        raise ValueError("previous linear system shape")
    if not alpha_l or len(alpha_l) != len(alpha_p):
        raise ValueError("aggregation count")
    if adj_callback is None and adj_batch_callback is None:
        raise ValueError("a projection adjoint implementation is required")
    for left, right in zip(alpha_l, alpha_p):
        if len(left) != previous.rows or len(right) != len(p):
            raise ValueError("aggregation row shape")
    projected_rows = None
    if adj_batch_callback is not None:
        projected_rows = list(adj_batch_callback(descriptor, alpha_p, size, ring.q))
        if len(projected_rows) != len(alpha_p):
            raise ValueError("batched adjoint returned wrong row count")
    phi, rhs = [], []
    for e, (left, right) in enumerate(zip(alpha_l, alpha_p)):
        base_row = list(previous.transpose(left))
        if projected_rows is None:
            projected_row = adj_callback(descriptor, right, size, ring.q)
        else:
            projected_row = projected_rows[e]
            projected_rows[e] = None  # Release each row as it is converted to phi.
        if len(base_row) != size or len(projected_row) != size:
            raise ValueError("transpose returned wrong coefficient length")
        v = [(x+z) % ring.q for x, z in zip(base_row, projected_row)]
        phi.append(tuple(ring.star(poly) for poly in unflatten(ring, v)))
        rhs.append((sum(a*b for a, b in zip(left, y))+
                    sum(a*b for a, b in zip(right, p))) % ring.q)
    return AggregationCache(ring, s, n, tuple(phi), tuple(rhs))


def radix_digits(ring, polynomials, rho, ell):
    """Source C.6 signed convention; each target ring has ell digit rings."""
    if rho <= 0 or rho % 2 or rho >= ring.q or ell < 1:
        raise ValueError("radix parameters")
    out = []
    for p in polynomials:
        digits = [[0]*ring.degree for _ in range(ell)]
        for j, value in enumerate(ring.centered(p)):
            sign = -1 if value < 0 else 1
            remaining = abs(value)
            for r in range(ell):
                following = (remaining+rho//2-1)//rho
                digits[r][j] = sign*(remaining-rho*following)
                remaining = following
            if remaining:
                raise ValueError("insufficient digits")
        out.extend(ring.poly(row) for row in digits)
    return out


def recompose(ring, digits, rho, ell):
    if len(digits) % ell:
        raise ValueError("radix input length")
    out = []
    for start in range(0, len(digits), ell):
        p = ring.zero()
        for r in range(ell):
            p = ring.add(p, ring.scale(digits[start+r], pow(rho, r, ring.q)))
        out.append(p)
    return out


def split_response(ring, polynomials, rho):
    """Honest two-part integer split only; not a constraint in ChildOperator."""
    low, high = [], []
    for p in polynomials:
        l, h = [], []
        for value in ring.centered(p):
            sign = -1 if value < 0 else 1
            following = (abs(value)+rho//2-1)//rho
            l.append(sign*(abs(value)-rho*following))
            h.append(sign*following)
        low.append(ring.poly(l))
        high.append(ring.poly(h))
    return low, high


class ChildOperator:
    """Lazy factored scalar-linear operator for source equations (16)--(18).

    apply() is homogeneous linear; public RHS is a separate property. No norm,
    digit-range or honest-source predicate is hidden inside apply/transpose.
    """

    def __init__(self, a: RingMatrix, b_matrix: RingMatrix, d_matrix: RingMatrix,
                 cache: AggregationCache, chi: Sequence[Poly], u1: Sequence[Poly],
                 u2: Sequence[Poly], rho: int, ell: int, padding: int = 0):
        self.ring, self.s, self.n, self.tau = cache.ring, cache.s, cache.n, cache.tau
        ring = self.ring
        if any(matrix.ring != ring for matrix in (a, b_matrix, d_matrix)):
            raise ValueError("ring mismatch")
        if a.cols != self.n or len(chi) != self.s or padding < 0:
            raise ValueError("main/short/padding shape")
        if rho <= 0 or rho % 2 or rho >= ring.q or ell < 1:
            raise ValueError("radix parameters")
        self.pairs = tuple((j, k) for j in range(self.s) for k in range(j, self.s))
        self.pair_index = {pair: index for index, pair in enumerate(self.pairs)}
        self.t_count = self.s*a.rows
        self.h_count = self.tau*len(self.pairs)
        if b_matrix.cols != ell*self.t_count or d_matrix.cols != ell*self.h_count:
            raise ValueError("B/D digit columns do not match declared order")
        if len(u1) != b_matrix.rows or len(u2) != d_matrix.rows:
            raise ValueError("commitment dimensions")
        if len(cache.phi) != self.tau or any(len(row) != self.s*self.n for row in cache.phi):
            raise ValueError("phi cache dimensions")
        self.a, self.b_matrix, self.d_matrix, self.cache = a, b_matrix, d_matrix, cache
        self.chi = tuple(ring.poly(p) for p in chi)
        self.u1, self.u2 = tuple(map(ring.poly, u1)), tuple(map(ring.poly, u2))
        self.rho, self.ell, self.padding = rho, ell, padding
        self.weights = tuple(pow(rho, r, ring.q) for r in range(ell))
        self.raw_cols = ring.degree*(2*self.n+ell*(self.t_count+self.h_count))
        self.cols = self.raw_cols+padding
        self.ring_rows = b_matrix.rows+d_matrix.rows+a.rows+self.tau
        self.rows = ring.degree*self.ring_rows+self.tau+padding
        # Per-short-instance caches; phi is shared across forks, these depend on chi.
        self.g = tuple(tuple(self._g_entry(e, coordinate) for coordinate in range(self.n))
                       for e in range(self.tau))
        self.pair_coefficients = tuple(ring.scale(ring.mul(self.chi[j], self.chi[k]),
                                                 1 if j == k else 2)
                                       for j, k in self.pairs)

    def _g_entry(self, e, coordinate):
        ring, out = self.ring, self.ring.zero()
        for j in range(self.s):
            out = ring.add(out, ring.mul(self.chi[j], self.cache.phi[e][j*self.n+coordinate]))
        return out

    @property
    def rhs(self):
        return (flatten(self.u1)+flatten(self.u2)+
                [0]*(self.ring.degree*(self.a.rows+self.tau))+
                list(self.cache.b)+[0]*self.padding)

    @property
    def cache_sizes(self):
        return {'shared_phi_Fq': self.cache.scalar_cache_size,
                'shared_b_Fq': self.tau,
                'fork_g_Fq': self.tau*self.n*self.ring.degree,
                'fork_pair_coefficients_Fq': len(self.pairs)*self.ring.degree,
                'fork_chi_Fq': self.s*self.ring.degree}

    def _split(self, vector):
        if len(vector) != self.cols:
            raise ValueError("child input length")
        polys = unflatten(self.ring, vector[:self.raw_cols])
        zlo, zhi = polys[:self.n], polys[self.n:2*self.n]
        boundary = 2*self.n+self.ell*self.t_count
        return zlo, zhi, polys[2*self.n:boundary], polys[boundary:], list(vector[self.raw_cols:])

    def apply(self, vector):
        ring = self.ring
        zlo, zhi, td, hd, pad = self._split(vector)
        z = [ring.add(x, ring.scale(y, self.rho)) for x, y in zip(zlo, zhi)]
        t, h = recompose(ring, td, self.rho, self.ell), recompose(ring, hd, self.rho, self.ell)
        out = self.b_matrix.apply(td)+self.d_matrix.apply(hd)
        main = self.a.apply(z)
        for row in range(self.a.rows):
            for j in range(self.s):
                main[row] = ring.sub(main[row], ring.mul(self.chi[j], t[j*self.a.rows+row]))
        out += main
        for e in range(self.tau):
            principal = ring.dot(self.g[e], z)
            for pair, multiplier in enumerate(self.pair_coefficients):
                principal = ring.sub(principal, ring.mul(multiplier, h[e*len(self.pairs)+pair]))
            out.append(principal)
        diagonal = [sum(h[e*len(self.pairs)+self.pair_index[j, j]][0]
                        for j in range(self.s)) % ring.q for e in range(self.tau)]
        return flatten(out)+diagonal+[int(x) % ring.q for x in pad]

    def transpose(self, dual):
        if len(dual) != self.rows:
            raise ValueError("child dual length")
        ring = self.ring
        polys = unflatten(ring, dual[:self.ring_rows*ring.degree])
        bt = polys[:self.b_matrix.rows]
        pos = self.b_matrix.rows
        dh = polys[pos:pos+self.d_matrix.rows]
        pos += self.d_matrix.rows
        main = polys[pos:pos+self.a.rows]
        principals = polys[pos+self.a.rows:]
        diagonal = dual[self.ring_rows*ring.degree:self.ring_rows*ring.degree+self.tau]
        td_grad, hd_grad = self.b_matrix.transpose(bt), self.d_matrix.transpose(dh)
        z_grad = self.a.transpose(main)

        def rec_pullback_add(grad, target, value):
            for digit, weight in enumerate(self.weights):
                index = target*self.ell+digit
                grad[index] = ring.add(grad[index], ring.scale(value, weight))

        for j in range(self.s):
            multiplier = ring.star(self.chi[j])
            for row in range(self.a.rows):
                value = ring.scale(ring.mul(multiplier, main[row]), -1)
                rec_pullback_add(td_grad, j*self.a.rows+row, value)
        for e in range(self.tau):
            for coordinate in range(self.n):
                z_grad[coordinate] = ring.add(z_grad[coordinate],
                    ring.mul(ring.star(self.g[e][coordinate]), principals[e]))
            for pair, multiplier in enumerate(self.pair_coefficients):
                value = ring.scale(ring.mul(ring.star(multiplier), principals[e]), -1)
                rec_pullback_add(hd_grad, e*len(self.pairs)+pair, value)
            for j in range(self.s):
                rec_pullback_add(hd_grad, e*len(self.pairs)+self.pair_index[j, j],
                                 ring.scalar(diagonal[e]))
        out = flatten(z_grad)+flatten([ring.scale(p, self.rho) for p in z_grad])
        out += flatten(td_grad)+flatten(hd_grad)
        out += [int(x) % ring.q for x in dual[self.ring_rows*ring.degree+self.tau:]]
        return out

    def residual(self, vector):
        return [(a-b) % self.ring.q for a, b in zip(self.apply(vector), self.rhs)]


def make_honest_child(a, b_matrix, d_matrix, cache, chi, w_blocks, rho, ell, padding=0):
    """Separate private helper to test equations; not a source extractor or norm proof."""
    ring = cache.ring
    if len(w_blocks) != cache.s or any(len(block) != cache.n for block in w_blocks):
        raise ValueError("source block dimensions")
    w = [tuple(ring.poly(p) for p in block) for block in w_blocks]
    t = [p for block in w for p in a.apply(block)]
    pairs = [(j, k) for j in range(cache.s) for k in range(j, cache.s)]
    h = []
    for e in range(cache.tau):
        for j, k in pairs:
            fj = cache.phi[e][j*cache.n:(j+1)*cache.n]
            fk = cache.phi[e][k*cache.n:(k+1)*cache.n]
            h.append(ring.scale(ring.add(ring.dot(fj, w[k]), ring.dot(fk, w[j])),
                                pow(2, -1, ring.q)))
    td, hd = radix_digits(ring, t, rho, ell), radix_digits(ring, h, rho, ell)
    z = [ring.zero() for _ in range(cache.n)]
    for j in range(cache.s):
        for coordinate in range(cache.n):
            z[coordinate] = ring.add(z[coordinate], ring.mul(chi[j], w[j][coordinate]))
    lo, hi = split_response(ring, z, rho)
    child = ChildOperator(a, b_matrix, d_matrix, cache, chi,
                          b_matrix.apply(td), d_matrix.apply(hd), rho, ell, padding)
    vector = flatten(lo)+flatten(hi)+flatten(td)+flatten(hd)+[0]*padding
    if any(child.residual(vector)):
        raise ValueError("source does not satisfy the declared scalar aggregations")
    return child, vector


def terminal_check(a: RingMatrix, pivot: RingMatrix, cache: AggregationCache,
                   chi: Sequence[Poly], disclosed_t: Sequence[Poly], vp: Sequence[Poly],
                   partial_h: Sequence[Sequence[int | None]], z: Sequence[Poly],
                   rho_p: int, ell_p: int, g_bound: int):
    """Separate NONLINEAR terminal validation; there is no terminal ChildOperator.

    partial_h has tau*s(s+1)/2 ring entries, with only coefficient zero of
    each h_00 omitted as None. Other inputs are arithmetic field values,
    not a claimed production canonical wire parser.
    """
    ring, s, n, tau = cache.ring, cache.s, cache.n, cache.tau
    pairs = [(j, k) for j in range(s) for k in range(j, s)]
    pair_index = {p: i for i, p in enumerate(pairs)}
    if a.ring != ring or pivot.ring != ring or a.cols != n:
        raise ValueError("terminal matrix shape")
    if len(chi) != s or len(z) != n or len(disclosed_t) != (s-1)*a.rows:
        raise ValueError("terminal response/image shape")
    if pivot.cols != a.rows*ell_p or len(vp) != pivot.rows or len(partial_h) != tau*len(pairs):
        raise ValueError("terminal commitment/symmetric shape")
    h = []
    for e in range(tau):
        segment = [list(p) for p in partial_h[e*len(pairs):(e+1)*len(pairs)]]
        for index, poly in enumerate(segment):
            if len(poly) != ring.degree:
                raise ValueError("terminal h coefficient length")
            for coefficient, value in enumerate(poly):
                omitted = index == 0 and coefficient == 0
                if (value is None) != omitted:
                    raise ValueError("only ct(h00) must be omitted")
        segment[0][0] = (cache.b[e]-sum(segment[pair_index[j, j]][0]
                                      for j in range(1, s))) % ring.q
        h.extend(ring.poly(poly) for poly in segment)
    chi = [ring.poly(p) for p in chi]
    z = [ring.poly(p) for p in z]
    numerator = a.apply(z)
    for row in range(a.rows):
        for j in range(1, s):
            numerator[row] = ring.sub(numerator[row], ring.mul(chi[j], disclosed_t[(j-1)*a.rows+row]))
    inverse = ring.inverse(chi[0])
    t0 = [ring.mul(inverse, p) for p in numerator]
    pivot_ok = pivot.apply(radix_digits(ring, t0, rho_p, ell_p)) == [ring.poly(p) for p in vp]
    norm_ok = sum(x*x for p in z for x in ring.centered(p)) <= g_bound
    principal_ok = True
    for e in range(tau):
        g = [ring.zero() for _ in range(n)]
        for j in range(s):
            for coordinate in range(n):
                g[coordinate] = ring.add(g[coordinate], ring.mul(chi[j], cache.phi[e][j*n+coordinate]))
        expected = ring.zero()
        for pair, (j, k) in enumerate(pairs):
            factor = ring.scale(ring.mul(chi[j], chi[k]), 1 if j == k else 2)
            expected = ring.add(expected, ring.mul(factor, h[e*len(pairs)+pair]))
        principal_ok &= ring.dot(g, z) == expected
    return {'accepted': bool(pivot_ok and norm_ok and principal_ok),
            'pivot_ok': pivot_ok, 'norm_ok': norm_ok, 'principal_ok': bool(principal_ok),
            't0': t0, 'h': h}
