"""Simulated bench for the generated tests (written by Zyn Anvil export).

Runs each test against a simulated cluster built from its approved spec:
    python -m pytest E:/Claude/Zyn/runs/demo-home/runs/exports/20261113-182131-30ee1c
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

sys.path.insert(0, 'E:\\Claude\\Zyn\\runs\\demo-home')

from harness.anvil.dbc import load_dbc  # noqa: E402
from harness.anvil.scripts import _name  # noqa: E402
from harness.anvil.simbench import SimBench  # noqa: E402

_DATA = json.loads((Path(__file__).parent / "test_cases.json").read_text(encoding="utf-8"))
_DB = load_dbc(_DATA["dbc_path"])
_BY_TEST = {_name(c["case_id"]): c for c in _DATA["cases"]}


@pytest.fixture
def bench(request):
    case = _BY_TEST[request.node.name]
    spec = _DATA["specs"][case["spec_item"]]
    return SimBench(spec, _DB, os.environ.get("ZYN_SIM_FAULT") or None)
