"""No silent pass: every checker, given empty or junk input, refuses or says it checked
nothing. It never comes back looking clean.

A public skill pack showed why this matters: its traceability reviewer rated an empty
matrix as broadly compliant. Each case here feeds a Zyn check something with nothing in it
and requires an error, a finding, or a "skipped" verdict, and no "pass".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import evidence
from harness.anvil.dbc_check import check_file
from harness.outside import start_tests
from harness.sift import check
from harness.sift.importer import load_requirement_set

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
DBC, SET = DATA / "icx100.dbc", DATA / "icx100_reqset.csv"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ---- inputs that must be refused --------------------------------------------------------


def test_empty_requirement_set_is_refused(tmp_path):
    with pytest.raises(ValueError):
        load_requirement_set(_write(tmp_path, "empty.csv", "ID,Text\n"))


def test_empty_test_file_is_refused(audit, tmp_path):
    with pytest.raises(ValueError, match="No tests found"):
        start_tests(audit, [_write(tmp_path, "test_empty.py", "\n\n")], DBC)


@pytest.mark.parametrize("text", ["", "this is not a CAN database", 'VERSION ""\nBU_: A\n'])
def test_empty_or_junk_dbc_is_refused(tmp_path, text):
    with pytest.raises(ValueError):
        check_file(_write(tmp_path, "bad.dbc", text))


def test_answer_key_that_matches_nothing_is_refused(cfg, audit, tmp_path):
    run = check.start(cfg, audit, SET).run_id
    key = _write(tmp_path, "key.json", json.dumps(
        {"requirements": [{"gold_id": "NOT-IN-RUN", "flags": ["weak_word"]}]}))
    with pytest.raises(ValueError, match="names no requirement"):
        check.score(audit, run, key)
    with pytest.raises(ValueError):
        check.score(audit, run, _write(tmp_path, "empty.json", '{"requirements": []}'))


# ---- inputs that run but must not pass ----------------------------------------------------


def test_junk_tests_are_skipped_not_passed(audit, tmp_path):
    junk = _write(tmp_path, "notes.txt", "Lorem ipsum dolor sit amet.\nNothing to see here.")
    run = start_tests(audit, [junk], DBC)
    v = evidence.verdicts(audit, run)
    assert v["counts"]["pass"] == 0 and v["counts"]["skipped"] == 1
    assert "Nothing to check" in v["rows"][0]["reason"]
    meta = audit.get_item(f"SET-{run}")["payload"]
    assert meta["coverage"]["no_signal"] == ["notes"]


def test_junk_tests_against_requirements_are_findings(audit, tmp_path):
    junk = _write(tmp_path, "notes.txt", "Lorem ipsum dolor sit amet.")
    run = start_tests(audit, [junk], DBC, SET)
    cats = {f["payload"]["category"] for f in audit.list_items(run, "finding")}
    assert "no_requirement" in cats
    assert evidence.verdicts(audit, run)["counts"]["pass"] == 0


def test_requirements_against_an_empty_source_are_all_ungrounded(cfg, audit, tmp_path):
    src = _write(tmp_path, "empty.md", "# Nothing\n")
    run = check.start(cfg, audit, SET, source=src).run_id
    ids = {i["payload"]["ext_id"] for i in audit.list_items(run, "imported_requirement")}
    ungrounded = {f["payload"]["req_id"] for f in audit.list_items(run, "finding")
                  if f["payload"]["category"] == "ungrounded"}
    assert ungrounded == ids


def test_dbc_with_no_ranges_does_not_flag_every_value(tmp_path):
    """[0|0] means 'not given'. Reading it as 'only zero' would fail every test value."""
    from harness.anvil.dbc import load_dbc

    dbc = _write(tmp_path, "norange.dbc", 'VERSION ""\nBU_: A B\nBO_ 100 M: 8 A\n'
                 ' SG_ Speed : 0|16@1+ (0.1,0) [0|0] "km/h" B\n')
    sig = load_dbc(dbc).signals["Speed"]
    assert sig.range_from_bits and (sig.minimum, sig.maximum) == (0.0, 6553.5)
    assert [f["category"] for f in check_file(dbc)] == ["range_missing"]
