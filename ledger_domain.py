"""The ledger domain model, v3. Executable companion to
artifacts/quantum-blockchain/bell-pair-ledger-trace.md.

The picture (user ruling 2026-08-31):

    Particle (pointer) -> Records (carry the wave ref) -> WaveMechanics (owns content,
                                                          keyed by opening record)

  HIDDEN LAYER = the distributed DAG of records (P1; the central dict here is the god
                 view every simulation has) + the injected WaveMechanics, which owns
                 all wave content in its own store, keyed by WaveId.
  VISIBLE LAYER = the interface only: Particle objects and the Records touches hand
                 out. Records are exposable; wave content is never exposable (no
                 method returns it - hiddenness is an interface property).

  There is NO wave registry in the domain: the ledger IS the index. A particle's head
  record carries its wave ref; resolution follows head -> ref -> mechanics store.
  Because nothing in the domain tracks membership, a remote settlement updates
  nothing of the absent members - the no-signalling rule is enforced by the absence
  of machinery that could break it.

One socket: WaveMechanics. Plugs: TableWaveMechanics (imported math, today),
LatticeWaveMechanicsV1 (the homegrown wave machine - future; the counting machine
does not yet do multi-particle waves), PresetAnswerMechanics (the LHV control -
design A physics; same ledger, |S| caps at 2).

No printing anywhere in this module - logging lives in logs.py, tests in
test_bell_pair.py. Pure stdlib; spin-1/2; toy scope.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import NewType, Optional, Protocol, Union

# ---------------------------------------------------------------- primitive types

Hash = NewType("Hash", str)              # content id of a Record (causal pointer)
ParticleId = NewType("ParticleId", str)  # move-only handle: never copy one (no-cloning)
WaveId = Hash                            # a wave's identity = the record that OPENED it
Draw = NewType("Draw", float)            # u in [0,1) - hash-derived, P6: no dice
Outcome = int                            # +1 or -1
Config = tuple[Outcome, ...]             # one joint configuration of a wave's members


class Kind(Enum):
    SPAWN = "SPAWN"            # creation - opens a wave (the record IS the wave's id)
    TICK = "TICK"              # time evolution of one member; carries the wave ref forward
    SETTLEMENT = "SETTLEMENT"  # a loud touch - the measured member leaves its wave


@dataclass(frozen=True)
class Question:
    """The measurement QUESTION: which direction to ask the spin (radians on one
    great circle; answers +1 along / -1 against). Lives on the PROBE - the apparatus
    carries its orientation (P7: settings derive from the probe's own history).
    Generalizes beyond spin: a lattice mechanics' natural question is 'where?'."""
    angle: float
    name: str = ""


# ------------------------------------------------- preparations (declarative specs)
# A Preparation says WHAT wave to create; HOW is the plug's business
# (same philosophy as "the table is the clause").

@dataclass(frozen=True)
class Singlet:
    """Two members, one wave: anti-correlate on every axis."""


@dataclass(frozen=True)
class Ready:
    """A calibrated probe: one member, known state."""


@dataclass(frozen=True)
class Definite:
    """One member, definite answer to `question` (a just-measured particle)."""
    question: Question
    outcome: Outcome


Preparation = Union[Singlet, Ready, Definite]


# ---------------------------------------------------------------- the visible data

@dataclass(frozen=True)
class Record:
    """The EVENT: immutable, append-only, co-signed. The only exposable data.

    wave_refs: each listed signer's wave id AFTER this event. Resolution rule
    (see HiddenLayer._resolve): an OPENER is its own ref - a SPAWN record, and a
    SETTLEMENT record for its measured member, need no entry; other signers are
    listed explicitly. A particle's ref changes only at records it signs.
    No amplitude field exists, by design (the no-snapshot law).
    """
    id: Hash
    parents: tuple[Hash, ...]
    signers: tuple[ParticleId, ...]
    kind: Kind
    question: Optional[Question] = None
    outcomes: tuple[tuple[ParticleId, Outcome], ...] = ()
    wave_refs: tuple[tuple[ParticleId, WaveId], ...] = ()


# ---------------------------------------------------------------- the one socket

class WaveMechanics(Protocol):
    """Seam for the physics. Owns ALL wave content in its own store, keyed by
    WaveId. The domain passes ids and reads outcomes; it never holds wave state.
    The draw u is always passed IN by the ledger (P6: the dice belong to the
    chain) - no plug can bring its own randomness."""

    def create(self, wid: WaveId, members: tuple[ParticleId, ...],
               preparation: Preparation) -> None: ...

    def evolve(self, wid: WaveId, member: ParticleId) -> None:
        """One tick of ONE member's share of the evolution. The state may be
        unsplittable; free evolution splits per member (U = U1 x U2)."""
        ...

    def join(self, new_wid: WaveId, a: WaveId, b: WaveId) -> None:
        """Entangling touch: two waves meet, one joint wave (dimensions add).
        Unused in phase 1 - the Bell pair is born joint."""
        ...

    def settle(self, wid: WaveId, member: ParticleId, question: Question,
               u: Draw) -> Outcome:
        """The loud touch. The measured member LEAVES the wave; the residual
        stays stored under the SAME wid (this is what keeps stale refs valid -
        an absent member's head still resolves correctly)."""
        ...

    def snapshot(self, wid: WaveId, member: Optional[ParticleId] = None,
                 question: Optional[Question] = None) -> dict:
        """God-side only: render the wave for the modeler's instruments
        (optionally viewed in `question`'s basis for `member`). No in-world
        code path leads here."""
        ...


# ---------------------------------------------------------------- plug 1: the table

@dataclass(frozen=True)
class _Row:
    config: Config
    amplitude: complex


@dataclass
class _TableWave:
    members: tuple[ParticleId, ...]
    rows: tuple[_Row, ...]
    version: int


class TableWaveMechanics:
    """The imported-math plug: a wave = an amplitude table over member configs.
    Two entangled members = ONE wave whose table does not factor (that leftover
    IS the entanglement); superposition = more than one row; rows never fork
    the DAG. Settlement statistics = Born via the one-draw form (the battery's
    full protocol is double-entry, QM-30/31 - two signers, norm-linear, WHY it
    is norm squared)."""

    def __init__(self) -> None:
        self._waves: dict[WaveId, _TableWave] = {}   # the plug's own store

    # -- port --

    def create(self, wid: WaveId, members: tuple[ParticleId, ...],
               preparation: Preparation) -> None:
        s = 1.0 / math.sqrt(2.0)
        if isinstance(preparation, Singlet):
            rows = (_Row((+1, -1), +s), _Row((-1, +1), -s))
        elif isinstance(preparation, Ready):
            rows = (_Row((+1,), 1.0 + 0j),)
        else:  # Definite: |outcome along question>, expressed in the z convention
            t = preparation.question.angle
            if preparation.outcome == +1:
                rows = (_Row((+1,), complex(math.cos(t / 2))),
                        _Row((-1,), complex(math.sin(t / 2))))
            else:
                rows = (_Row((+1,), complex(-math.sin(t / 2))),
                        _Row((-1,), complex(math.cos(t / 2))))
            rows = tuple(r for r in rows if abs(r.amplitude) > 1e-12)
        self._waves[wid] = _TableWave(members, rows, 1)

    def evolve(self, wid: WaveId, member: ParticleId) -> None:
        # free flight is identity on spin; a spatial plug would propagate here
        self._waves[wid].version += 1

    def join(self, new_wid: WaveId, a: WaveId, b: WaveId) -> None:
        wa, wb = self._waves.pop(a), self._waves.pop(b)
        rows = tuple(_Row(ra.config + rb.config, ra.amplitude * rb.amplitude)
                     for ra in wa.rows for rb in wb.rows)
        self._waves[new_wid] = _TableWave(wa.members + wb.members, rows, 1)

    def settle(self, wid: WaveId, member: ParticleId, question: Question,
               u: Draw) -> Outcome:
        w = self._waves[wid]
        rows = self._rotated(w, member, question)
        i = w.members.index(member)
        p_plus = sum(abs(r.amplitude) ** 2 for r in rows if r.config[i] == +1)
        outcome: Outcome = +1 if u < p_plus else -1
        # prune + renormalize + drop the leaving member's axis
        kept = [r for r in rows if r.config[i] == outcome]
        nrm = math.sqrt(sum(abs(r.amplitude) ** 2 for r in kept))
        residual: dict[Config, complex] = {}
        for r in kept:
            cfg = r.config[:i] + r.config[i + 1:]
            residual[cfg] = residual.get(cfg, 0) + r.amplitude / nrm
        rest_members = w.members[:i] + w.members[i + 1:]
        if rest_members:
            self._waves[wid] = _TableWave(
                rest_members,
                tuple(_Row(k, v) for k, v in residual.items()), w.version + 1)
        else:
            del self._waves[wid]
        return outcome

    def snapshot(self, wid: WaveId, member: Optional[ParticleId] = None,
                 question: Optional[Question] = None) -> dict:
        w = self._waves[wid]
        rows = w.rows if (member is None or question is None) \
            else self._rotated(w, member, question)
        return {"members": list(w.members), "version": w.version,
                "rows": [(r.config, r.amplitude) for r in rows]}

    # -- internal --

    @staticmethod
    def _rotated(w: _TableWave, member: ParticleId,
                 question: Question) -> tuple[_Row, ...]:
        # re-express one member's axis in the question's basis (reversible):
        # <+q|+> = cos(t/2), <+q|-> = sin(t/2), <-q|+> = -sin(t/2), <-q|-> = cos(t/2)
        i = w.members.index(member)
        cos, sin = math.cos(question.angle / 2), math.sin(question.angle / 2)
        overlap = {(+1, +1): cos, (+1, -1): sin, (-1, +1): -sin, (-1, -1): cos}
        acc: dict[Config, complex] = {}
        for row in w.rows:
            for new_v in (+1, -1):
                cfg = row.config[:i] + (new_v,) + row.config[i + 1:]
                acc[cfg] = acc.get(cfg, 0) + overlap[(new_v, row.config[i])] * row.amplitude
        return tuple(_Row(k, v) for k, v in acc.items() if abs(v) > 1e-12)


# ---------------------------------------------------------------- plug 2: the control

class PresetAnswerMechanics:
    """The LHV control (design A physics): the first draw fixes a hidden axis
    lambda = 2*pi*u shared by the pair; answers are sign(cos(theta - lambda)),
    the second member anti-aligned. Deterministic pre-set answers - same ledger,
    same records, and |S| caps at 2 (Bell). Kept on purpose as the corpse in
    the morgue: swap the plug and watch the ceiling move."""

    def __init__(self) -> None:
        self._waves: dict[WaveId, tuple[tuple[ParticleId, ...], Optional[float]]] = {}

    def create(self, wid: WaveId, members: tuple[ParticleId, ...],
               preparation: Preparation) -> None:
        self._waves[wid] = (members, None)

    def evolve(self, wid: WaveId, member: ParticleId) -> None:
        pass

    def join(self, new_wid: WaveId, a: WaveId, b: WaveId) -> None:
        raise NotImplementedError("the control has no joint waves to make")

    def settle(self, wid: WaveId, member: ParticleId, question: Question,
               u: Draw) -> Outcome:
        members, lam = self._waves[wid]
        if len(members) == 2:                      # first touch: the draw fixes lambda
            lam = 2.0 * math.pi * u
            other = next(m for m in members if m != member)
            self._waves[wid] = ((other,), lam)
            return +1 if math.cos(question.angle - lam) >= 0 else -1
        del self._waves[wid]                       # second touch: anti-aligned readout
        assert lam is not None
        return -1 if math.cos(question.angle - lam) >= 0 else +1

    def snapshot(self, wid: WaveId, member: Optional[ParticleId] = None,
                 question: Optional[Question] = None) -> dict:
        members, lam = self._waves[wid]
        return {"members": list(members), "lambda": lam}


# ---------------------------------------------------------------- the interface

class Particle:
    """The INTERFACE - a particle's presence in the visible layer is its
    TOUCHABILITY. It is a POINTER: an id and a head into the DAG, nothing else.
    Probes additionally carry their Question (the apparatus orientation)."""

    def __init__(self, pid: ParticleId, head: Hash, hidden: "HiddenLayer",
                 question: Optional[Question] = None) -> None:
        self.id = pid
        self.head = head
        self.question = question
        self._hidden = hidden

    async def tick(self, n: int = 1) -> None:
        """Time evolution: n self-records. The chain growing IS moving through
        time; each tick evolves this member's share of its wave and carries the
        wave ref forward. Returns NOTHING: aging hands you no receipt - the
        records it wrote are simply part of you now, reachable off your head."""
        for _ in range(n):
            self._hidden._tick(self.id)

    async def touch(self, other: "Particle") -> Outcome:
        """The only read/write: rendezvous + atomic write + co-signed record,
        asking THIS particle's question. Returns ONLY the outcome - the answer
        is what an apparatus gives you. The settlement record is NOT handed
        back: it is appended to both worldlines, so it is already part of the
        prober (head now points at it). Reading a record's CONTENTS is a
        modeler's move (God.record) - phase 1 exposes no in-world reader.
        Phase 1 implements the LOUD flavor only (probes are loud by
        declaration - O5 open)."""
        assert self.question is not None, "only a probe (a particle with a question) measures"
        _, outcome = self._hidden._touch(self.id, other.id, self.question)
        return outcome

    def wave_ref(self) -> WaveId:
        """In-world legitimate: your wave's id, read off your OWN head record
        (identity, never state). Remote events cannot move it."""
        return self._hidden._resolve(self.id)


# ---------------------------------------------------------------- the hidden layer

class God:
    """The modeler's instrument panel. NO in-world code path leads here - the god
    view exists and no insider has it. Named explicitly rather than underscore-
    prefixed: _ means "internal, don't touch"; these are MEANT to be touched -
    by the modeler only."""

    def __init__(self, hidden: "HiddenLayer") -> None:
        self._h = hidden

    def wave(self, pid: str, question: Optional[Question] = None) -> dict:
        h = self._h
        wid = h._resolve(ParticleId(pid))
        member = ParticleId(pid) if question is not None else None
        return h._mechanics.snapshot(wid, member, question)

    def record(self, rid: Hash) -> Record:
        return self._h._dag[rid]

    def ancestry(self, rid: Hash) -> set[Hash]:
        seen: set[Hash] = set()
        stack = [rid]
        while stack:
            r = self._h._dag[stack.pop()]
            for p in r.parents:
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return seen

    def concurrent(self, a: Hash, b: Hash) -> bool:
        # vector-clock concurrency: neither record in the other's causal past
        return a not in self.ancestry(b) and b not in self.ancestry(a)


def _hash_draw(head_a: Hash, head_b: Hash) -> Draw:
    # P6, no dice, in-domain: the dice belong to the chain, not the physics.
    # Each head commits to its whole ancestry, so the draw depends on both full
    # histories and nothing else.
    h = hashlib.sha256((head_a + head_b).encode()).hexdigest()
    return Draw(int(h[:13], 16) / float(16 ** 13))


class HiddenLayer:
    """The DAG of records + the injected WaveMechanics. No wave registry: the
    ledger IS the index (head -> ref -> mechanics store). The DAG is DISTRIBUTED
    in the model (P1); self._dag is the simulation's god view, reached via .god."""

    def __init__(self, mechanics: Optional[WaveMechanics] = None) -> None:
        self._mechanics: WaveMechanics = mechanics if mechanics is not None \
            else TableWaveMechanics()
        self._dag: dict[Hash, Record] = {}
        self._particles: dict[ParticleId, Particle] = {}
        self.god = God(self)

    # -- the interface (spawning) --

    async def spawn_pair(self, a: str = "p1", b: str = "p2") -> tuple[Particle, Particle]:
        # pair production: ONE record starts TWO worldlines and opens the wave
        # (the record IS the wave's id). Event first, projection second.
        p1, p2 = ParticleId(a), ParticleId(b)
        rec = self._append((), (p1, p2), Kind.SPAWN)
        self._mechanics.create(rec.id, (p1, p2), Singlet())
        for pid in (p1, p2):
            self._particles[pid] = Particle(pid, rec.id, self)
        return self._particles[p1], self._particles[p2]

    async def spawn_probe(self, name: str, question: Question) -> Particle:
        # a calibrated apparatus particle; an observer is a particle that keeps
        # records (P5) - same class, its question built into the device
        pid = ParticleId(name)
        rec = self._append((), (pid,), Kind.SPAWN)
        self._mechanics.create(rec.id, (pid,), Ready())
        self._particles[pid] = Particle(pid, rec.id, self, question)
        return self._particles[pid]

    # -- resolution: the ledger is the index --

    def _resolve(self, pid: ParticleId) -> WaveId:
        # an OPENER is its own ref: a SPAWN record, and a SETTLEMENT record for
        # its measured member; every other signer is listed in wave_refs.
        rec = self._dag[self._particles[pid].head]
        if rec.kind == Kind.SPAWN:
            return rec.id
        if rec.kind == Kind.SETTLEMENT and rec.outcomes and rec.outcomes[0][0] == pid:
            return rec.id
        return dict(rec.wave_refs)[pid]

    # -- internal machinery (called via Particle methods) --

    def _append(self, parents: tuple[Hash, ...], signers: tuple[ParticleId, ...],
                kind: Kind, question: Optional[Question] = None,
                outcomes: tuple[tuple[ParticleId, Outcome], ...] = (),
                wave_refs: tuple[tuple[ParticleId, WaveId], ...] = ()) -> Record:
        payload = repr((parents, signers, kind.value,
                        None if question is None else question.angle,
                        outcomes, wave_refs, len(self._dag)))
        rid = Hash(hashlib.sha256(payload.encode()).hexdigest()[:12])
        rec = Record(rid, parents, signers, kind, question, outcomes, wave_refs)
        self._dag[rid] = rec
        return rec

    def _tick(self, pid: ParticleId) -> Record:
        p = self._particles[pid]
        wid = self._resolve(pid)
        rec = self._append((p.head,), (pid,), Kind.TICK,
                           wave_refs=((pid, wid),))          # carry the pointer forward
        p.head = rec.id
        self._mechanics.evolve(wid, pid)                     # this member's share of time
        return rec

    def _touch(self, a: ParticleId, b: ParticleId,
               question: Question) -> tuple[Record, Outcome]:
        # ONE atomic transaction (the doc's five-line section): draw, settle,
        # record. Inside it, ordering is bookkeeping; outside, only the record
        # exists. The measured member b leaves its wave; its new one-member wave
        # opens under this record's id. Absent members: nothing here touches
        # them - their stale refs stay valid (residual stored under the old wid).
        pa, pb = self._particles[a], self._particles[b]
        wid = self._resolve(b)
        u = _hash_draw(pa.head, pb.head)
        outcome = self._mechanics.settle(wid, b, question, u)
        rec = self._append((pa.head, pb.head), (a, b), Kind.SETTLEMENT, question,
                           outcomes=((b, outcome),),
                           wave_refs=((a, self._resolve(a)),))
        pa.head = pb.head = rec.id
        self._mechanics.create(rec.id, (b,), Definite(question, outcome))
        return rec, outcome
