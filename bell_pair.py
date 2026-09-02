"""The article's snippet, verbatim and runnable: one entangled pair, two probes,
two concurrent measurements. The whole flow the piece describes is here;
test_bell_pair.py is where the same run gets audited step by step.

    python bell_pair.py
"""
from __future__ import annotations

import asyncio
import math
from random import randint

from ledger_domain import HiddenLayer, Question, TableWaveMechanics


async def main() -> None:
    hidden = HiddenLayer(mechanics=TableWaveMechanics())
    particle_1, particle_2 = await hidden.spawn_pair()

    alice, bob = await asyncio.gather(
        hidden.spawn_probe("alice", Question(0.0, "a")),
        hidden.spawn_probe("bob", Question(math.pi / 4, "b")),
    )
    await asyncio.gather(
        particle_1.tick(randint(1, 10)),
        particle_2.tick(randint(1, 10)),
    )
    alice_answer, bob_answer = await asyncio.gather(
        alice.touch(particle_1),
        bob.touch(particle_2),
    )

    # the answers are all the experiment gets; the rest is the modeler's view
    print("alice (a = 0 deg)   : %+d" % alice_answer)
    print("bob   (b = 45 deg)  : %+d" % bob_answer)
    print("anti-correlated     : %s" % (alice_answer * bob_answer == -1))
    print("settlements concurrent (god view): %s"
          % hidden.god.concurrent(alice.head, bob.head))


if __name__ == "__main__":
    asyncio.run(main())
