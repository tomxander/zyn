"""Anvil cases for other benches: Robot Framework, CAPL, step table."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pytest

from harness.anvil import formats
from harness.anvil.dbc import load_dbc
from harness.anvil.generate import generate_cases
from tests.test_forge import DBC, spec

SPECS = [
    spec(template="threshold", input_signal="FuelLevel", threshold=10, direction="below",
         output_signal="TT_LowFuel", expected_value=1),
    spec(template="timeout", message="Warnings", timeout_ms=500, output_signal="TT_Brake",
         expected_value=1),
    spec(template="periodic_tx", message="ClusterStatus", period_ms=100),
    spec(template="tracking", input_signal="VehicleSpeed", output_signal="DisplayedSpeed",
         track_low_factor=1, track_low_offset=0, track_high_factor=1.1, track_high_offset=4),
]


@pytest.fixture(scope="module")
def cases():
    db = load_dbc(DBC)
    out = []
    for i, s in enumerate(SPECS):
        out += generate_cases({**s, "req_id": f"REQ-{i}"},
                              {"id": f"REQ-{i}", "text": "t", "quote": "q"}, db)
    out.append({**out[0], "case_id": "TC-MANUAL-1", "kind": "manual", "steps": []})
    return out


def test_robot_suite_has_every_case_and_only_declared_keywords(cases):
    suite, resource = formats.robot(cases, "R1")
    names = re.findall(r"^(\S.*)$", suite.split("*** Test Cases ***")[1], re.MULTILINE)
    assert len(names) == len(cases)
    declared = set(re.findall(r"^(\S[^\n]*)$", resource.split("*** Keywords ***")[1], re.MULTILINE))
    used = {line.strip().split("    ")[0] for line in suite.splitlines()
            if line.startswith("    ") and not line.strip().startswith("[")}
    assert used - declared <= {"Sleep", "Skip"}
    assert "Fail    Not mapped to a bench" in resource  # nothing passes by accident
    assert "[Tags]    REQ-0" in suite and "Skip    Manual check" in suite


def test_capl_is_structurally_sound_and_names_are_unique(cases):
    src = formats.capl(cases, "R1")
    assert formats.capl_problems(src) == []
    assert src.count("testcase ") == len(cases)
    assert "testWaitForSignalMatch(TT_LowFuel" in src and "ZynCheckPeriod(" in src
    assert formats.capl_problems(src + "\ntestcase X()\n{\n") != []


def test_step_table_has_a_row_per_step(cases):
    rows = list(csv.DictReader(io.StringIO(formats.steps_csv(cases))))
    assert len(rows) == sum(len(c["steps"]) for c in cases)
    assert set(rows[0]) == set(formats.STEP_COLUMNS)


def test_export_writes_the_new_files(cfg, audit, tmp_path):
    from tests.test_forge import test_forge_pipeline_end_to_end

    test_forge_pipeline_end_to_end(cfg, audit, tmp_path)
    out = tmp_path / "out"
    for name in ("zyn_generated.robot", "zyn_keywords.resource", "zyn_generated.can",
                 "test_steps.csv"):
        assert (out / name).is_file(), name
    assert "testcase" in Path(out / "zyn_generated.can").read_text(encoding="cp1252")
