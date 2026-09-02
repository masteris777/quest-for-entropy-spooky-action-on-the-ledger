"""Test sequences for the ledger domain model (v3). Two tests:

  test_bell_trace - the doc's five-step Bell walk-through, with audit blocks
  test_chsh_seam  - the seam proof: same ledger, two mechanics plugs;
                    TableWaveMechanics -> |S| = 2*sqrt(2), PresetAnswerMechanics
                    (LHV control) -> |S| <= 2. Bell as dependency injection.

Reading grammar (three kinds of block, three meanings):
  with step("..."):   one narrative step; its BARE statements are the actual
                      OPERATIONS on the model (spawn / tick / touch), numbered # N:
  with audit("..."):  verification - the asserts proving one claim, plus the
                      god-side READS they need (never actions)
  with report():      output only - the log_* calls, nothing else

The domain model itself never prints. Run:

    python test_bell_pair.py
"""
from __future__ import annotations

import asyncio
import math
import random

from ledger_domain import (HiddenLayer, Kind, PresetAnswerMechanics, Question,
                           TableWaveMechanics)
_rng = random.Random(20260901)   # seeded: unequal flights, reproducible trace

from logs import (audit, log_chsh, log_hidden_norms, log_hidden_wave,
                  log_section, log_tsirelson, log_verdict, log_visible, report,
                  step)


async def test_bell_trace() -> None:
    """The five steps of bell-pair-ledger-trace.md, executed and audited."""
    log_section("TEST: the Bell trace (doc steps 1-5)")

    # 1: create the hidden layer for the experiment (quantum table plug)
    hidden = HiddenLayer(mechanics=TableWaveMechanics())

    with step("Step 1 - birth: one SPAWN record starts two worldlines, opens the wave"):

        # 2: spawn the entangled pair - ONE record, TWO worldlines, one wave
        particle_1, particle_2 = await hidden.spawn_pair()

        with audit("the SPAWN record IS the wave id, for both particles"):
            e1 = hidden.god.record(particle_1.head)
            assert particle_1.wave_ref() == e1.id
            assert particle_2.wave_ref() == e1.id

        with report():
            log_visible("%s %s signers=%s" % (e1.id, e1.kind.value, list(e1.signers)))
            log_hidden_wave("W(e1)", hidden.god.wave("p1"))

    with step("Step 2 - time passes: worldlines grow, the ref rides the records"):

        # 3: fly - unequal, arbitrary numbers of ticks (each member's own time;
        #    nothing downstream depends on how long either particle aged)
        flight_1, flight_2 = _rng.randint(1, 10), _rng.randint(1, 10)
        await asyncio.gather(particle_1.tick(flight_1), particle_2.tick(flight_2))

        with audit("the tick record carries the wave ref forward"):
            assert dict(hidden.god.record(particle_2.head).wave_refs)["p2"] == e1.id

        with report():
            log_visible("particle_1.head=%s (%d ticks)  particle_2.head=%s (%d ticks)"
                        % (particle_1.head, flight_1, particle_2.head, flight_2))
            log_hidden_wave("W(e1)", hidden.god.wave("p1"))

    with step("Step 3 - Alice's touch: settlement at a = 0 deg"):

        # 4: spawn Alice - a probe whose question (a = 0 deg) is built into the device
        alice = await hidden.spawn_probe("alice", Question(0.0, "a"))

        # 5: remember p2's state of affairs, then Alice touches p1 - the settlement
        p2_head_before, p2_ref_before = particle_2.head, particle_2.wave_ref()
        alice_answer = await alice.touch(particle_1)

        with audit("p1 signed m1, so its ref moved to the new opener m1"):
            measurement_1 = hidden.god.record(alice.head)   # the touch hands back NO record
            assert particle_1.wave_ref() == measurement_1.id
        with audit("remote events move NOTHING of p2's - head and ref unchanged"):
            assert particle_2.head == p2_head_before
            assert particle_2.wave_ref() == p2_ref_before

        with report():
            log_visible("%s SETTLEMENT signers=%s question=%s outcome=%+d"
                        % (measurement_1.id, list(measurement_1.signers), measurement_1.question.name, alice_answer))
            log_hidden_wave("W(e1) residual, still under the old id",
                            hidden.god.wave("p2"))

    with step("Step 4 - Bob's touch: settlement at b = 45 deg"):

        # 6: spawn Bob - his question (b = 45 deg) built into the device
        bob = await hidden.spawn_probe("bob", Question(math.pi / 4, "b"))

        with report():
            log_hidden_norms("p2 in question b", hidden.god.wave("p2", bob.question))

        # 7: Bob touches p2 - the conditioned readout
        bob_answer = await bob.touch(particle_2)

        with audit("p2 signed m2, so its ref moved to m2"):
            measurement_2 = hidden.god.record(bob.head)
            assert particle_2.wave_ref() == measurement_2.id

        with report():
            log_visible("%s SETTLEMENT question=%s outcome=%+d   (anti-correlated: %s)"
                        % (measurement_2.id, measurement_2.question.name, bob_answer, alice_answer * bob_answer == -1))

    with step("Step 5 - the audit: concurrency and the missing path (god traversal)"):

        with audit("m1 and m2 are concurrent - no DAG path either way"):
            assert hidden.god.concurrent(measurement_1.id, measurement_2.id)
        with audit("m1's ancestry holds the birth e1 but NO tick of p2's"):
            assert e1.id in hidden.god.ancestry(measurement_1.id)
            assert not any(hidden.god.record(h).signers == ("p2",)
                           for h in hidden.god.ancestry(measurement_1.id)
                           if hidden.god.record(h).kind == Kind.TICK)


async def test_chsh_seam() -> None:
    """Same ledger machinery, two mechanics plugs: the quantum table sits at
    2*sqrt(2); the pre-set-answer control caps at 2 (Bell). Statistical bands
    are generous (N = 20000 per setting -> sigma_S ~ 0.02)."""
    log_section("TEST: the seam proof - Bell as dependency injection")

    deg = math.pi / 180
    settings = [(0, 45), (0, 135), (90, 45), (90, 135)]
    n = 20000

    async def run_pair(hidden: HiddenLayer, i: int, ta: float, tb: float,
                       bob_first: bool) -> tuple[int, int]:
        # one full experiment: spawn pair + two probes, two settlements
        tag = "%d_%.2f_%.2f_%s" % (i, ta, tb, bob_first)
        q1, q2 = await hidden.spawn_pair("p1" + tag, "p2" + tag)
        al = await hidden.spawn_probe("A" + tag, Question(ta))
        bo = await hidden.spawn_probe("B" + tag, Question(tb))
        if bob_first:
            ob = await bo.touch(q2)
            oa = await al.touch(q1)
        else:
            oa = await al.touch(q1)
            ob = await bo.touch(q2)
        return oa, ob

    async def chsh(name: str, make_mechanics) -> list[float]:
        # both settle orders, all four settings, n pairs each
        s_values = []
        for order, bob_first in (("Alice first", False), ("Bob first  ", True)):
            hidden = HiddenLayer(mechanics=make_mechanics())
            es = {}
            marginals = []
            for ta, tb in settings:
                corr = plus_b = 0
                for i in range(n):
                    oa, ob = await run_pair(hidden, i, ta * deg, tb * deg, bob_first)
                    corr += oa * ob
                    plus_b += (ob == +1)
                es[(ta, tb)] = corr / n
                marginals.append(plus_b / n)
            s = es[(0, 45)] - es[(0, 135)] + es[(90, 45)] + es[(90, 135)]

            with report():
                log_chsh(name, order, es, s, marginals)

            with audit("Bob's marginals are flat - no signal in either order"):
                assert all(abs(m - 0.5) < 0.02 for m in marginals)
            s_values.append(abs(s))
        return s_values

    with step("Plug 1: the quantum table - expect the Tsirelson value"):

        # 1: run the full CHSH battery on the quantum plug
        quantum = await chsh("TableWaveMechanics (quantum)", TableWaveMechanics)

        with audit("the shared-wave plug lands in the Tsirelson band [2.70, 2.95]"):
            assert all(2.70 < s < 2.95 for s in quantum)

        with report():
            log_tsirelson()

    with step("Plug 2: the pre-set-answer control - expect Bell's ceiling"):

        # 2: run the identical battery on the LHV control
        control = await chsh("PresetAnswerMechanics (LHV) ", PresetAnswerMechanics)

        with audit("pre-set answers cap at Bell's ceiling: |S| < 2.10"):
            assert all(s < 2.10 for s in control)

        with report():
            log_verdict("design A physics, dead on arrival - and kept on purpose")


async def main() -> None:
    await test_bell_trace()
    print()
    await test_chsh_seam()
    print("\nALL TESTS PASS")


if __name__ == "__main__":
    asyncio.run(main())
