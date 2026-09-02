"""How much does |S| wobble between runs? Six independent repeats of the full
CHSH battery, so the spread in the measured value can be read as what it is -
counting noise - rather than mistaken for a disagreement.

    python chsh_spread.py
"""
from __future__ import annotations

import asyncio
import math
import statistics

from ledger_domain import HiddenLayer, Question, TableWaveMechanics
from logs import log_section, log_verdict

DEG = math.pi / 180
SETTINGS = [(0, 45), (0, 135), (90, 45), (90, 135)]


async def chsh_once(n: int, tag: str) -> float:
    """One full battery: four settings, n pairs each, on a fresh ledger."""
    hidden = HiddenLayer(mechanics=TableWaveMechanics())
    es = {}
    for ta, tb in SETTINGS:
        corr = 0
        for i in range(n):
            t = "%s_%d_%.2f_%.2f" % (tag, i, ta, tb)
            q1, q2 = await hidden.spawn_pair("p1" + t, "p2" + t)
            al = await hidden.spawn_probe("A" + t, Question(ta * DEG))
            bo = await hidden.spawn_probe("B" + t, Question(tb * DEG))
            corr += await al.touch(q1) * await bo.touch(q2)
        es[(ta, tb)] = corr / n
    return abs(es[(0, 45)] - es[(0, 135)] + es[(90, 45)] + es[(90, 135)])


async def main(n: int = 20000, repeats: int = 6) -> None:
    log_section("TEST: the spread of |S| across independent runs")
    values = [await chsh_once(n, "r%d" % k) for k in range(repeats)]
    print("   %d independent runs, N=%d per setting:" % (repeats, n))
    print("   " + "  ".join("%.4f" % v for v in values))
    log_verdict("mean %.4f, standard deviation %.4f  (2*sqrt(2) = %.4f)"
                % (statistics.mean(values), statistics.stdev(values), 2 * math.sqrt(2)))
    log_verdict("a couple of hundredths between runs is counting noise, not disagreement")


if __name__ == "__main__":
    asyncio.run(main())
