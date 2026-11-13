"""A simulated bench, so the exported pytest module can actually run.

It implements the bench interface the generated tests call, on top of the same simulated
cluster the fault check uses (built from each approved spec). With ZYN_SIM_FAULT set to a
fault name (for example "late" or "shift_up") the simulation misbehaves in that way, and
the tests that should catch it fail.

This runs the generated test code end to end. It says nothing about a real cluster: the
simulation is built from the specs themselves."""

from __future__ import annotations

import itertools

from harness.anvil.dbc import CanDb
from harness.anvil.simulate import TICK, Sim, check_case


class SimBench:
    def __init__(self, spec: dict, db: CanDb, fault: str | None = None):
        self.spec, self.db, self.fault = spec, db, fault
        self.now = 0
        self.steps: list[dict] = []

    def _run(self, until: int) -> dict:
        return Sim(self.spec, self.db, self.fault).run(self.steps, until + 2 * TICK)

    def _check(self, step: dict, span: int) -> bool:
        res = self._run(self.now + span)
        ok = check_case({"steps": [step]}, res)
        self.now += span
        return ok

    # ---- the interface the generated tests use ----

    def set(self, signal: str, value: float) -> None:
        self.steps.append({"at_ms": self.now, "do": "set", "signal": signal, "value": value})

    def stop(self, message: str) -> None:
        self.steps.append({"at_ms": self.now, "do": "stop", "message": message})

    def wait_ms(self, ms: int) -> None:
        self.now += int(ms)

    def expect_within(self, signal: str, value: float, ms: int) -> bool:
        return self._check({"at_ms": self.now, "do": "expect", "signal": signal,
                            "value": value, "within_ms": int(ms)}, int(ms))

    def expect_for(self, signal: str, value: float, ms: int) -> bool:
        return self._check({"at_ms": self.now, "do": "expect", "signal": signal,
                            "value": value, "for_ms": int(ms)}, int(ms))

    def value_after(self, signal: str, ms: int) -> float | None:
        res = self._run(self.now + int(ms))
        self.now += int(ms)
        return res["out"].get(int(self.now // TICK * TICK))

    def periods(self, message: str, count: int) -> list[float]:
        span = int(self.spec.get("period_ms") or 100) * (count + 3)
        res = self._run(self.now + span)
        times = [t for t in res["tx"] if t >= self.now][: count + 1]
        self.now += span
        return [b - a for a, b in itertools.pairwise(times)]


CONFTEST = '''"""Simulated bench for the generated tests (written by Zyn Anvil export).

Runs each test against a simulated cluster built from its approved spec:
    python -m pytest {folder}
Set ZYN_SIM_FAULT to a fault name (late, shift_up, shift_down, inclusive, no_response,
always, hold_short, early, never, slow, fast, under_read, over_read, frozen) to make the
simulation misbehave; the tests meant to catch that fault then fail. Replace this file
with your own bench fixture to run against real hardware.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, {root!r})

from harness.anvil.dbc import load_dbc  # noqa: E402
from harness.anvil.scripts import _name  # noqa: E402
from harness.anvil.simbench import SimBench  # noqa: E402

_DATA = json.loads((Path(__file__).parent / "test_cases.json").read_text(encoding="utf-8"))
_DB = load_dbc(_DATA["dbc_path"])
_BY_TEST = {{_name(c["case_id"]): c for c in _DATA["cases"]}}


@pytest.fixture
def bench(request):
    case = _BY_TEST[request.node.name]
    spec = _DATA["specs"][case["spec_item"]]
    return SimBench(spec, _DB, os.environ.get("ZYN_SIM_FAULT") or None)
'''
