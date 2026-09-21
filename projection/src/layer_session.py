"""CFdagger-N projection/short-checkpoint interface and canonical message parser.

This implements the replaced interface, not the unchanged full-node verifier.
The caller supplies complete prover snapshots and the existing child/terminal
verifier. Online verifier randomness is deliberately outside restored snapshots.
"""
from dataclasses import dataclass
import pickle
import secrets
from reference_operator import Descriptor


class Rejected(ValueError):
    pass


class OnlineCoins:
    def bits(self, n):
        return secrets.randbits(n)

    def below(self, q):
        n = q.bit_length()
        while True:
            value = self.bits(n)
            if value < q:
                return value


@dataclass(frozen=True)
class Config:
    parameter_id: str
    layer: int
    q: int
    N: int
    m: int
    T: int
    s: int
    d: int
    b: int
    depth: int
    relation_rows: int
    tau: int
    prefix_bytes: int
    symmetric_bytes: int
    terminal_response_bytes: int
    terminal: bool = False
    projection_cap: int = 160
    short_cap: int = 160


@dataclass(frozen=True)
class Checkpoint:
    config: Config
    public_context: bytes
    local_state: bytes
    complete_prover_state: bytes


class LayerSession:
    def __init__(self, config, public_context, coins=None):
        if not isinstance(public_context, bytes):
            raise TypeError('The full immutable public context must be supplied.')
        self.config, self.public_context = config, public_context
        self.coins = coins if coins is not None else OnlineCoins()
        self.state = {'phase': 'PREFIX', 'projection_attempts': 0, 'short_attempts': 0,
                      'transcript': []}

    def _fail(self, reason):
        self.state['phase'] = 'REJECTED'
        raise Rejected(reason)

    def _phase(self, expected):
        if self.state['phase'] != expected:
            self._fail('chronology: expected '+expected)

    def _fq(self, raw, expected):
        if not isinstance(raw, bytes) or len(raw) != expected or expected % 6:
            self._fail('fixed field payload length')
        for pos in range(0, len(raw), 6):
            if int.from_bytes(raw[pos:pos+6], 'little') >= self.config.q:
                self._fail('noncanonical field coefficient')

    def _record(self, direction, name, raw):
        self.state['transcript'].append((direction, name, raw))
        return raw

    def prefix(self, raw):
        self._phase('PREFIX')
        self._fq(raw, self.config.prefix_bytes)
        self.state['fixed_prefix'] = raw
        self.state['phase'] = 'PROJECTION_READY'
        self._record('P->V', 'prefix', raw)

    def projection_message(self):
        self._phase('PROJECTION_READY')
        c = self.config
        if self.state['projection_attempts'] >= c.projection_cap:
            self._fail('projection attempts exhausted')
        bits = c.b+c.depth*(3*c.b-1)
        raw = self.coins.bits(bits).to_bytes((bits+7)//8, 'little')
        Descriptor.from_bytes(raw, c.b, c.depth)
        self.state['descriptor'] = raw
        self.state['projection_attempts'] += 1
        self.state['phase'] = 'PROJECTION_REPLY'
        return self._record('V->P', 'projection_descriptor', raw)

    def projection_reply(self, raw):
        self._phase('PROJECTION_REPLY')
        if raw == b'\x00':
            self._record('P->V', 'projection_retry', raw)
            self.state.pop('descriptor')
            if self.state['projection_attempts'] == self.config.projection_cap:
                self._fail('projection attempts exhausted')
            self.state['phase'] = 'PROJECTION_READY'
            return
        if not raw or raw[0] != 1:
            self._fail('projection tag or retry payload')
        payload = raw[1:]
        self._fq(payload, 6*self.config.m)
        energy = 0
        for pos in range(0, len(payload), 6):
            x = int.from_bytes(payload[pos:pos+6], 'little')
            x = x if x <= self.config.q//2 else x-self.config.q
            energy += x*x
        if energy > self.config.T:
            self._fail('projection norm')
        self.state['p'] = payload
        self.state['phase'] = 'AGGREGATION_READY'
        self._record('P->V', 'selected_projection', raw)

    def aggregation_message(self):
        self._phase('AGGREGATION_READY')
        c = self.config
        # A packed byte buffer, not a Python-object array of field coefficients.
        raw = bytearray(6*c.tau*(c.relation_rows+c.m))
        for offset in range(0, len(raw), 6):
            raw[offset:offset+6] = self.coins.below(c.q).to_bytes(6, 'little')
        raw = bytes(raw)
        self.state['alpha'] = raw
        self.state['phase'] = 'SYMMETRIC'
        return self._record('V->P', 'aggregation', raw)

    def symmetric(self, raw):
        self._phase('SYMMETRIC')
        self._fq(raw, self.config.symmetric_bytes)
        self.state['fixed_symmetric'] = raw
        self.state['phase'] = 'SHORT_READY'
        self._record('P->V', 'symmetric_or_u2', raw)

    def short_message(self):
        self._phase('SHORT_READY')
        c = self.config
        if self.state['short_attempts'] >= c.short_cap:
            self._fail('short attempts exhausted')
        value = 0
        for block in range(c.s):
            while True:
                packed = 0
                nonzero = False
                for j in range(c.d):
                    code = self.coins.below(5)
                    packed |= code << (3*j)
                    nonzero |= code != 2
                if not (c.terminal and block == 0 and not nonzero):
                    break
            value |= packed << (3*c.d*block)
        raw = value.to_bytes((3*c.d*c.s+7)//8, 'little')
        self.state['short'] = raw
        self.state['short_attempts'] += 1
        self.state['phase'] = 'SHORT_REPLY'
        return self._record('V->P', 'short_challenge', raw)

    def short_reply(self, raw):
        self._phase('SHORT_REPLY')
        if raw == b'\x00':
            self._record('P->V', 'short_retry', raw)
            if self.state['short_attempts'] == self.config.short_cap:
                self._fail('short attempts exhausted')
            self.state['phase'] = 'SHORT_READY'
            return
        if not raw or raw[0] != 1:
            self._fail('short tag or retry payload')
        if self.config.terminal:
            self._fq(raw[1:], self.config.terminal_response_bytes)
            self.state['response'] = raw[1:]
            self.state['phase'] = 'TERMINAL_CHECK'
        else:
            if len(raw) != 1:
                self._fail('child follows selection; no extra response payload')
            self.state['phase'] = 'CHILD'
        self._record('P->V', 'selected_short', raw)

    def finish(self, accepted):
        if self.state['phase'] not in ('CHILD', 'TERMINAL_CHECK'):
            self._fail('no submitted child/terminal')
        # Result of the unchanged exact child/terminal verifier, never an
        # inference from message syntax or the success of a component test.
        self.state['phase'] = 'ACCEPTED' if accepted else 'REJECTED'

    def snapshot(self, complete_prover_state):
        if not isinstance(complete_prover_state, bytes):
            raise TypeError('Complete prover state must be exported as immutable bytes.')
        return Checkpoint(self.config, self.public_context, pickle.dumps(self.state, protocol=4), complete_prover_state)

    def restore(self, checkpoint):
        if checkpoint.config != self.config or checkpoint.public_context != self.public_context:
            self._fail('checkpoint public-context mismatch')
        # Only locally created trusted extractor checkpoints, never wire data.
        self.state = pickle.loads(checkpoint.local_state)
        # Restore ALL prover state through the caller's adapter. Never rewind
        # online verifier coins with the prover snapshot.
        return checkpoint.complete_prover_state
