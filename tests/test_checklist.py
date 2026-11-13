"""Anvil Review findings as a confirmation checklist (FC / LC / PC / NO / NA)."""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from harness import checklist
from harness.outside import start_tests
from harness.sift import check
from tests.test_outside import REQS, TESTS

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def _run(audit, tmp_path, reqs=True):
    p = tmp_path / "test_outside.py"
    p.write_text(TESTS, encoding="utf-8")
    rs = None
    if reqs:
        rs = tmp_path / "reqs.csv"
        rs.write_text("ID,Text\n" + "".join(f"{k},{v}\n" for k, v in REQS.items()),
                      encoding="utf-8")
    return start_tests(audit, [p], DATA / "icx100.dbc", rs)


def test_ratings_follow_the_findings_and_unchecked_is_na(audit, tmp_path):
    run = _run(audit, tmp_path)
    data = checklist.build(audit, run)
    by = {r["id"]: r for r in data["checklist"]}
    assert by["TC002"]["rating"] == "NA" and "person" in by["TC002"]["note"]
    assert by["TC009"]["rating"] == "LC"            # 2 of 3 requirements referenced
    assert by["TC007"]["rating"] == "LC"            # 5 of 6 tests carry a requirement ID
    assert by["TC007"]["provisional"] is True       # its finding is undecided
    assert by["TSA-01"]["rating"] == "FC"
    assert not [r for r in data["checklist"] if r["rating"] not in checklist.RATINGS]
    # Every Person check is NA; nothing is rated without a code check behind it.
    assert all(r["rating"] == "NA" for r in data["checklist"]
               if r["id"] in {c[0] for c in checklist.TEST_CHECKS if c[2] is None})


def test_dismissed_findings_lift_the_rating(audit, tmp_path):
    run = _run(audit, tmp_path)
    f = next(i for i in audit.list_items(run, "finding")
             if i["payload"]["category"] == "no_requirement")
    audit.decide(f["item_id"], "rejected", "Tom")
    by = {r["id"]: r for r in checklist.build(audit, run)["checklist"]}
    assert by["TC007"]["rating"] == "FC" and not by["TC007"]["provisional"]


def test_traceability_checks_need_a_requirement_set(audit, tmp_path):
    run = _run(audit, tmp_path, reqs=False)
    by = {r["id"]: r for r in checklist.build(audit, run)["checklist"]}
    assert by["TC007"]["rating"] == by["TC009"]["rating"] == "NA"


def test_export_writes_the_five_tabs(audit, tmp_path):
    run = _run(audit, tmp_path)
    res = check.export_findings(audit, run, "Tom", out_dir=tmp_path / "out")
    wb = load_workbook(res["files"]["checklist"])
    assert wb.sheetnames == ["Title", "Checklist", "Findings", "Dashboard", "Signoff"]
    assert "Provisional" in str(wb["Title"]["A7"].value)
