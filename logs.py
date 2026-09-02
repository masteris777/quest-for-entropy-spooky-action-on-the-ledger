"""ALL printing for the domain-model tests lives here. The domain model itself
never prints; test files call these so that logging is visibly logging, never
action. Every function only formats and prints - no side effects on the model."""
from __future__ import annotations

import math
from contextlib import contextmanager


@contextmanager
def step(title: str):
    """Visually groups one narrative step of a walk-through:

        with step("Step 1 - birth: ..."):
            # actions, audits and logs of that step

    Prints the title on entry; the indented block below it IS the step. Purely
    narrative - use audit() for verification."""
    print("\n%s" % title)
    yield


@contextmanager
def report():
    """Visually groups the log_* calls of one step - output only, never checks,
    never actions. Prints nothing itself; it exists so that in the test source
    the three kinds of block are unmistakable: bare statements inside step() are
    OPERATIONS, audit() blocks are ASSERTS, report() blocks are OUTPUT."""
    yield


@contextmanager
def audit(claim: str):
    """Visually groups the asserts that verify ONE claim:

        with audit("the record IS the wave id"):
            assert p1.wave_ref() == e1.id

    Prints the claim with its verdict when the block passes; a failing assert
    inside aborts the run with that claim on screen."""
    yield
    print("   AUDIT    %s: ok" % claim)


def log_section(title: str) -> None:
    """A banner separating major test phases."""
    print("=" * 72)
    print(title)
    print("=" * 72)


def log_visible(text: str) -> None:
    """A visible-layer fact: something an in-world observer could hold."""
    print("   VISIBLE  %s" % text)


def log_hidden_wave(label: str, snapshot: dict) -> None:
    """A god-view rendering of one wave (modelers only - no in-world path)."""
    if "rows" in snapshot:
        rows = " | ".join(
            "%s : %+.3f" % ("".join("+" if v > 0 else "-" for v in config),
                            amplitude.real)
            for config, amplitude in snapshot["rows"])
        print("   HIDDEN (god view)  %s = {members: %s, v%d, rows: [ %s ]}"
              % (label, snapshot["members"], snapshot["version"], rows))
    else:  # the control plug: a hidden axis instead of rows
        lam = snapshot.get("lambda")
        print("   HIDDEN (god view)  %s = {members: %s, lambda: %s}"
              % (label, snapshot["members"],
                 "unset" if lam is None else "%.3f rad" % lam))


def log_hidden_norms(label: str, snapshot: dict) -> None:
    """God-view of a wave in a question's basis, with the row norms spelled out."""
    rows = " | ".join("%+d : %+.3f" % (config[0], amplitude.real)
                      for config, amplitude in snapshot["rows"])
    norms = " / ".join("%.3f" % (abs(amplitude) ** 2)
                       for _, amplitude in snapshot["rows"])
    print("   HIDDEN (god view)  %s: [ %s ]  (norms %s)" % (label, rows, norms))


def log_chsh(name: str, order: str, es: dict, s: float, marginals: list) -> None:
    """One CHSH run: the four correlators, |S|, and the no-signal marginals."""
    print("%s / %s : E=%s  |S| = %.4f"
          % (name, order, {k: round(v, 3) for k, v in es.items()}, abs(s)))
    print("              Bob's marginal P(+) per setting: %s  (flat = no signal)"
          % [round(m, 3) for m in marginals])


def log_verdict(text: str) -> None:
    """The takeaway line after a test block."""
    print("   -> %s" % text)


def log_tsirelson() -> None:
    """The reference value the quantum plug should sit at."""
    log_verdict("the shared-wave mechanics sits at 2*sqrt(2) = %.4f" % (2 * math.sqrt(2)))
