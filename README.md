# Spooky Action on the Ledger

Companion code for *Quest for Entropy #16*. The article ships with it as
`article.md`.

## Run it

Python 3.10+, no dependencies.

    python run_all.py

`bell_pair.py` is the article's snippet, exactly as printed: one entangled pair,
two probes, two concurrent measurements. `test_bell_pair.py` walks the same run
record by record and asserts what the article claims - the wave reference moves
only where its owner signed, and the two settlements are concurrent - then
measures the CHSH statistic in both measurement orders.

## What is in here

| file | what it is |
|---|---|
| `ledger_domain.py` | the model: records, worldlines, waves behind one socket |
| `logs.py` | all printing (the domain model itself is silent) |
| `bell_pair.py` | the article's snippet, runnable |
| `test_bell_pair.py` | the trace with audits, and the CHSH measurement |
| `chsh_spread.py` | six independent repeats, so the run-to-run spread is visible |
| `run_all.py` | both of the above, in order |
| `expected_output/run_all.txt` | what a correct run prints, to diff against |

One line legitimately varies between runs: the snippet's two answers, because
`bell_pair.py` flies the pair for a random number of ticks and the settlement
draw is fed by the record hashes. The pair comes out anti-correlated every time,
and everything below the snippet - the audited trace, the CHSH numbers - is
identical run to run.

## Scope

The wave arithmetic here is standard quantum arithmetic, imported rather than
derived; what this code demonstrates is the ledger's contribution - no
signalling, no ordering, no causal path between the two measurements. The
article's Confession section says exactly where that line falls.

## Licence

MIT.
