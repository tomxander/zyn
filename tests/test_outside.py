"""Checker mode: code checks on requirements and tests another tool produced."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from harness import evidence
from harness.outside import check_tests, ground_findings, split_tests, start_tests
from harness.sift import check
from harness.sift.importer import load_requirement_set
from harness.sift.ingest import load_document
from tests.test_api import env  # noqa: F401  (fixture)

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
SRS, DBC, SET = DATA / "icx100_srs.md", DATA / "icx100.dbc", DATA / "icx100_reqset.csv"

OUTSIDE = [
    {"ext_id": "X1", "text": "The cluster shall enter the ACTIVE state within 2.5 s of IGN "
                             "changing from OFF to ON."},                       # invented 2.5
    {"ext_id": "X2", "text": "The cluster shall support wireless phone charging at 15 W."},
    {"ext_id": "X3", "text": "The cluster should perform a display self-test at startup and "
                             "report the result."},                             # shall -> should
    {"ext_id": "X4", "text": "When FuelLow = 1, the cluster shall show the amber low fuel "
                             "telltale steady on."},                            # from a table row
]

TESTS = '''
import pytest

def test_low_fuel_on(bench):
    """REQ-1: low fuel telltale"""
    bench.set("FuelLevel", 9)
    assert bench.get("TT_LowFuel") == 1

def test_typo(bench):
    """REQ-1"""
    bench.set("FuelLvl", 9)
    assert bench.get("TT_LowFuel") == 1

def test_out_of_range(bench):
    """REQ-2"""
    bench.set("VehicleSpeed", 900)

def test_untraced(bench):
    """REQ-2"""
    assert bench.get("DisplayedSpeed") == 77

def test_no_reference(bench):
    bench.set("FuelLevel", 50)

def test_unknown_reference(bench):
    """REQ-9"""
    bench.set("FuelLevel", 50)
'''
REQS = {"REQ-1": "When the fuel level is below 10 percent, the low-fuel telltale shall be lit.",
        "REQ-2": "The displayed speed shall not be less than the vehicle speed.",
        "REQ-3": "The cluster shall chime when a door is open."}


def test_real_set_matches_its_source_and_outside_problems_are_caught():
    doc = load_document(SRS)
    rs = load_requirement_set(SET)
    found, matches = ground_findings([{"ext_id": r.ext_id, "text": r.text}
                                      for r in rs.requirements], doc)
    assert found == [] and all(m and m["score"] >= 0.5 for m in matches.values())
    found, _ = ground_findings(OUTSIDE, doc)
    got = {(f["req_id"], f["category"], f["evidence"]) for f in found}
    assert got == {("X1", "invented_value", "2.5"), ("X3", "modal_changed", "should"),
                   ("X2", "ungrounded", "The cluster shall support wireless phone")}


def test_a_quote_column_is_used_when_the_other_tool_exported_one():
    doc = load_document(SRS)
    found, matches = ground_findings([{
        "ext_id": "Q", "text": "Cluster goes to sleep after the goodbye screen.",
        "quote": "then enter the SLEEP state"}], doc)
    assert matches["Q"]["score"] == 1.0 and not [f for f in found if f["category"] ==
                                                 "ungrounded"]


def test_sift_review_with_source_records_it_and_adds_findings(cfg, audit, tmp_path):
    f = tmp_path / "outside.csv"
    f.write_text("ID,Text\n" + "".join(f'{r["ext_id"]},"{r["text"]}"\n' for r in OUTSIDE),
                 encoding="utf-8")
    run = check.start(cfg, audit, f, source=SRS).run_id
    meta = audit.get_item(f"SET-{run}")["payload"]
    assert meta["source"]["filename"] == "icx100_srs.md"
    cats = Counter(x["payload"]["category"] for x in audit.list_items(run, "finding"))
    assert cats["ungrounded"] == 1 and cats["invented_value"] == 1 and cats["modal_changed"] == 1


def test_tests_from_any_tool_are_checked_against_dbc_and_requirements(tmp_path):
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_outside.py"
    p.write_text(TESTS, encoding="utf-8")
    units = split_tests(p)
    assert [u.name for u in units][:2] == ["test_low_fuel_on", "test_typo"]
    found, cov = check_tests(units, load_dbc(DBC), REQS)
    by = {(f["req_id"], f["category"]) for f in found}
    assert ("test_typo", "unknown_signal") in by
    assert ("test_out_of_range", "out_of_range") in by
    assert ("test_untraced", "value_not_traced") in by
    assert ("test_no_reference", "no_requirement") in by
    assert ("test_unknown_reference", "unknown_requirement") in by
    assert not [f for f in found if f["req_id"] == "test_low_fuel_on"]  # 9 is a boundary of 10
    assert {k: cov[k] for k in ("requirements", "tested", "untested")} == {
        "requirements": 3, "tested": 2, "untested": ["REQ-3"]}
    assert ("test_untraced", "no_setup") in by and ("test_untraced", "no_tolerance") in by


MORE = '''
def test_speed_exact(bench):
    """REQ-2"""
    bench.set("VehicleSpeed", 50)
    assert bench.get("DisplayedSpeed") == 52.5

def test_speed_tolerant(bench):
    """REQ-2"""
    bench.set("VehicleSpeed", 50)
    assert bench.get("DisplayedSpeed") == pytest.approx(52.5, abs=0.5)

def test_speed_copy(bench):
    """REQ-2"""
    bench.set("VehicleSpeed", 50)
    assert bench.get("DisplayedSpeed") == 52.5

def test_speed_top(bench):
    """REQ-2"""
    bench.set("VehicleSpeed", 300)
    bench.set("FuelLevel", 0)
    assert bench.get("TT_LowFuel") == 1
'''


def test_tolerance_setup_duplicates_and_boundaries(tmp_path):
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_more.py"
    p.write_text(MORE, encoding="utf-8")
    found, cov = check_tests(split_tests(p), load_dbc(DBC), REQS)
    by = {(f["req_id"], f["category"]) for f in found}
    assert ("test_speed_exact", "no_tolerance") in by
    assert ("test_speed_tolerant", "no_tolerance") not in by
    assert ("test_speed_copy", "duplicate_test") in by
    dup = next(f for f in found if f["category"] == "duplicate_test")
    assert dup["related_ids"] == ["test_speed_exact"]
    assert not [f for f in found if f["category"] == "no_setup"]
    gaps = {b["signal"]: b["missing"] for b in cov["boundaries"]}
    assert gaps == {"VehicleSpeed": ["minimum"], "FuelLevel": ["maximum", "a value inside"]}
    assert cov["no_signal"] == []


def test_capl_and_robot_tests_split_into_units(tmp_path):
    capl = tmp_path / "t.can"
    capl.write_text("testcase TC_A()\n{\n  $FuelLevel = 9;\n}\ntestcase TC_B()\n{\n}\n",
                    encoding="utf-8")
    robot = tmp_path / "t.robot"
    robot.write_text("*** Settings ***\nLibrary  X\n*** Test Cases ***\nLow fuel\n    Set  "
                     "FuelLevel  9\nDoor chime\n    Set  DoorOpen  1\n*** Keywords ***\nX\n",
                     encoding="utf-8")
    assert [u.name for u in split_tests(capl)] == ["TC_A", "TC_B"]
    assert [u.name for u in split_tests(robot)] == ["Low fuel", "Door chime"]


def test_test_check_run_is_reviewed_like_sift_review(env, tmp_path):  # noqa: F811
    audit, _cfg, _run, c = env
    p = tmp_path / "test_outside.py"
    p.write_text(TESTS, encoding="utf-8")
    reqs = tmp_path / "reqs.csv"
    reqs.write_text("ID,Text\n" + "".join(f"{k},{v}\n" for k, v in REQS.items()),
                    encoding="utf-8")
    run = start_tests(audit, [p], DBC, reqs)
    v = c.get(f"/api/runs/{run}").json()
    assert v["tool"] == "Anvil Review" and v["kind"] == "check" and v["ai_available"] is False
    assert v["meta"]["coverage"]["untested"] == ["REQ-3"] and v["item_label"] == "Tests"
    r = c.post(f"/api/runs/{run}/actions/ai_review", json={"reviewer": "Tom"})
    assert r.status_code == 400 and "requirements" in r.json()["error"]
    fid = v["findings"][0]["item_id"]
    assert c.post("/api/decide", json={"item_id": fid, "decision": "approved",
                                       "reviewer": "Tom"}).status_code == 200
    assert evidence.verdicts(audit, run)["kind"] == "tests"


def test_api_new_test_check_run(env, tmp_path):  # noqa: F811
    _audit, _cfg, _run, c = env
    r = c.post("/api/new/tests", data={"reviewer": "Tom"},
               files={"file": ("test_x.py", TESTS.encode(), "text/plain")})
    assert r.status_code == 200, r.text
    assert c.get(f"/api/runs/{r.json()['run_id']}").json()["tool"] == "Anvil Review"


def test_tests_that_check_nothing_and_shared_names(tmp_path):
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_names.py"
    p.write_text('def test_a(bench):\n    bench.set("FuelLevel", 9)\n\n'
                 'def test_a(bench):\n    bench.set("FuelLevel", 9)\n'
                 '    assert bench.get("TT_LowFuel") == 1\n', encoding="utf-8")
    found, _ = check_tests(split_tests(p), load_dbc(DBC), {})
    cats = [f["category"] for f in found]
    assert cats.count("no_check") == 1 and cats.count("duplicate_name") == 1


def test_docstrings_are_not_steps_or_checks(tmp_path):
    """A docstring line "Expected: TT_LowFuel = 1" is neither a check nor a step."""
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_doc.py"
    p.write_text('def test_a(bench):\n    """REQ-1. Expected: TT_LowFuel = 1 within 300 ms."""\n'
                 '    bench.set("FuelLevel", 9)\n', encoding="utf-8")
    found, _ = check_tests(split_tests(p), load_dbc(DBC), REQS)
    assert "no_check" in {f["category"] for f in found}


def test_duplicates_compare_the_whole_body(tmp_path):
    from harness.anvil.dbc import load_dbc

    body = ('    bench.set("VehicleSpeed", 150)\n    v = bench.value_after("DisplayedSpeed", 220)\n')
    p = tmp_path / "test_dup.py"
    p.write_text(f'def test_a(bench):\n    """REQ-2"""\n{body}    assert v <= 4\n\n'
                 f'def test_b(bench):\n    """REQ-2"""\n{body}    assert v >= 0\n',
                 encoding="utf-8")
    found, _ = check_tests(split_tests(p), load_dbc(DBC), REQS)
    assert "duplicate_test" not in {f["category"] for f in found}


def test_stopping_a_message_is_setup(tmp_path):
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_stop.py"
    p.write_text('def test_a(bench):\n    """REQ-1"""\n    bench.stop("Fuel")\n'
                 '    assert bench.expect_within("TT_LowFuel", 1, 600)\n', encoding="utf-8")
    found, _ = check_tests(split_tests(p), load_dbc(DBC), REQS)
    assert "no_setup" not in {f["category"] for f in found}


def test_a_value_swapped_from_a_neighbouring_sentence_is_flagged():
    doc = load_document(SRS)
    found, _ = ground_findings([{"ext_id": "S", "text": "The cluster shall enter the ACTIVE "
                                 "state within 3 s of IGN changing from OFF to ON."}], doc)
    assert ("S", "invented_value", "3") in {(f["req_id"], f["category"], f["evidence"])
                                            for f in found}


def test_a_time_argument_is_not_read_as_a_value(tmp_path):
    """value_after('TT_MIL', 137) == 1: 137 is milliseconds, 1 is the value."""
    from harness.anvil.dbc import load_dbc

    p = tmp_path / "test_time.py"
    p.write_text('def test_a(bench):\n    """REQ-1"""\n    bench.set("FuelLevel", 9)\n'
                 '    assert bench.value_after("TT_LowFuel", 137) == 1\n'
                 '    assert bench.value_after("TT_LowFuel", 40) == 7\n', encoding="utf-8")
    found, _ = check_tests(split_tests(p), load_dbc(DBC), REQS)
    oor = [f["evidence"] for f in found if f["category"] == "out_of_range"]
    assert oor == ["7"]
