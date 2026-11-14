from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.models.fake_provider import FakeProvider
from harness.sift import check
from harness.sift.export import _reqif
from harness.sift.importer import load_requirement_set

KEY = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "icx100_answer_key.json"
CSV = ("ID,Section,Requirement\n"
       "R1,Fuel,The gauge shall update quickly.\n"
       "R2,Fuel,The low-fuel telltale shall be lit below 10 percent.\n"
       "R3,Chimes,The chime volume is set by the driver.\n"
       "R4,Chimes,The cluster shall play a chime and shall log a DTC within TBD ms.\n"
       "R4,Chimes,The low-fuel telltale shall be lit below 10 percent.\n")


def _csv(tmp_path, text=CSV, name="set.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_csv_xlsx_and_reqif_keep_ids(tmp_path):
    s = load_requirement_set(_csv(tmp_path))
    assert [r.ext_id for r in s.requirements] == ["R1", "R2", "R3", "R4", "R4"]
    assert s.columns_used["text"] == "Requirement" and s.requirements[0].heading == "Fuel"

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Some title row"])  # our own export starts with a label row
    ws.append(["Object Identifier", "Object Text"])
    ws.append(["DOORS-12", "The display shall be readable."])
    wb.save(tmp_path / "doors.xlsx")
    x = load_requirement_set(tmp_path / "doors.xlsx")
    assert (x.requirements[0].ext_id, x.requirements[0].text) == (
        "DOORS-12", "The display shall be readable.")

    rows = [{"id": "REQ-A-001", "text": "The cluster shall show fuel.", "section_number": "2"}]
    (tmp_path / "a.reqif").write_text(_reqif(rows, "T", "run"), encoding="utf-8")
    r = load_requirement_set(tmp_path / "a.reqif")
    assert (r.requirements[0].ext_id, r.requirements[0].text, r.requirements[0].heading) == (
        "REQ-A-001", "The cluster shall show fuel.", "2")

    with pytest.raises(ValueError, match="text"):
        load_requirement_set(_csv(tmp_path, "ID,Owner\nR1,Tom\n", "bad.csv"))


def test_code_checks():
    s = [{"ext_id": r.split(",")[0], "text": r.split(",", 2)[2], "heading": ""}
         for r in CSV.strip().splitlines()[1:]]
    got = {(f["req_id"], f["category"], f["evidence"]) for f in check.code_findings(s)}
    assert ("R1", "weak_word", "quickly") in got
    assert ("R3", "no_modal", "The chime volume is set by the driver.") in got
    assert ("R4", "not_atomic", "shall") in got
    assert ("R4", "placeholder", "TBD") in got
    assert ("R4", "duplicate_id", "R4") in got
    assert any(c == "duplicate_text" and r == "R2" for r, c, _ in got)


def _ai(findings):
    return json.dumps({"findings": [
        {"req_id": r, "category": c, "evidence": e, "explanation": "x",
         "question_for_author": "q?", "related_ids": []} for r, c, e in findings]})


def _ai_rel(findings):
    return json.dumps({"findings": [
        {"req_id": r, "category": c, "evidence": e, "explanation": "x",
         "question_for_author": "q?", "related_ids": rel} for r, c, e, rel in findings]})


def test_ai_review_grounds_evidence_and_decisions_carry_over(cfg, audit, tmp_path):
    path = _csv(tmp_path)
    run = check.start(cfg, audit, path).run_id
    FakeProvider.queue[:] = [_ai([
        ("R2", "missing_condition", "below 10 percent"),      # grounded
        ("R3", "unclear_reference", "the driver menu"),       # not in the text
        ("R9", "ambiguous", "anything"),                      # unknown ID: dropped
        ("R1", "weak_word", "quickly"),                       # code found it already
    ]), _ai_rel([("R1", "conflict", "update quickly", ["R2"]),
                 ("R2", "conflict", "below 10 percent", ["R1"])])]  # same pair twice
    rep = check.ai_review(cfg, audit, run, workers=1)
    assert rep.done == ["batch-0", "window-0"]
    finds = audit.list_items(run, "finding")
    weak = [f for f in finds if f["payload"]["category"] == "weak_word"]
    assert len(weak) == 1 and check.corroborations(audit, weak[0]["item_id"])[0]["source"] == "ai"
    assert len([f for f in finds if f["payload"]["category"] == "conflict"]) == 1
    ai = {f["payload"]["req_id"]: f["payload"] for f in audit.list_items(run, "finding")
          if f["payload"]["source"] == "ai"}
    assert ai["R2"]["evidence_found"] and not ai["R3"]["evidence_found"] and "R9" not in ai
    # second click does nothing: the batch is done
    assert check.ai_review(cfg, audit, run, workers=1).done == []

    fid = next(f["item_id"] for f in audit.list_items(run, "finding")
               if f["payload"]["req_id"] == "R2" and f["payload"]["source"] == "ai")
    audit.decide(fid, "rejected", "Tom", comment="Known and accepted")

    run2 = check.start(cfg, audit, path).run_id
    FakeProvider.queue[:] = [_ai([("R2", "missing_condition", "below 10 percent")]), _ai([])]
    check.ai_review(cfg, audit, run2, workers=1)
    carry = check.carry_over_candidates(audit, run2)
    assert len(carry) == 1 and carry[0]["payload"]["prior"]["by"] == "Tom"
    assert check.apply_prior(audit, run2, "Tom") == 1
    assert audit.status(carry[0]["item_id"]) == "rejected"
    assert check.apply_prior(audit, run2, "Tom") == 0  # nothing left to carry over
    with pytest.raises(ValueError):  # findings are decided by people, never by a model
        audit.decide(carry[0]["item_id"], "approved", "ai-reviewer")

    res = check.export_findings(audit, run2, "Tom", out_dir=tmp_path / "out")
    data = json.loads(Path(res["files"]["json"]).read_text(encoding="utf-8"))
    assert {r["status"] for r in data["findings"]} >= {"dismissed", "open"}


def test_score_against_answer_key(cfg, audit, tmp_path):
    key = json.loads(KEY.read_text(encoding="utf-8"))
    lines = ["ID,Requirement"] + [f'{g["gold_id"]},"{g["text"]}"' for g in key["requirements"]]
    run = check.start(cfg, audit, _csv(tmp_path, "\n".join(lines) + "\n", "icx.csv")).run_id
    s = check.score(audit, run, KEY, ("code",))
    weak = sum("weak_word" in g["flags"] for g in key["requirements"])
    assert s["found"] == weak and s["flags_not_in_key"] == 0  # code finds every weak word
    assert s["required_flags"] == sum(len(g["flags"]) for g in key["requirements"])


def test_score_lists_only_sources_that_ran(cfg, audit, tmp_path):
    key = json.loads(KEY.read_text(encoding="utf-8"))
    lines = ["ID,Requirement"] + [f'{g["gold_id"]},"{g["text"]}"' for g in key["requirements"]]
    run = check.start(cfg, audit, _csv(tmp_path, "\n".join(lines) + "\n", "icx.csv")).run_id
    s = check.score(audit, run, KEY)  # asks for code and ai; no AI review ran
    assert s["sources"] == ["code"] and s["ai_review"] == "not run"


def test_stability_passes_match_findings_and_filter_score(cfg, audit, tmp_path):
    cfg = cfg.model_copy(update={"replay": True})  # stability passes must ask again anyway
    run = check.start(cfg, audit, _csv(tmp_path)).run_id
    empty = _ai([])
    FakeProvider.queue[:] = [_ai([("R2", "missing_condition", "below 10 percent"),
                                  ("R3", "ambiguous", "volume")]), empty]
    with pytest.raises(ValueError):
        check.stability_check(cfg, audit, run, 3)  # needs pass 1 first
    check.ai_review(cfg, audit, run, workers=1)
    # pass 2 repeats R2 (other words), drops R3, adds R4; pass 3 repeats R2 only
    FakeProvider.queue[:] = [_ai([("R2", "missing_condition", "lit below"),
                                  ("R4", "ambiguous", "chime")]), empty,
                             _ai([("R2", "missing_condition", "10 percent")]), empty]
    rep = check.stability_check(cfg, audit, run, 3, workers=1)
    assert rep.done == ["pass-2", "pass-3"] and check.passes_done(audit, run) == [1, 2, 3]
    by = {f["payload"]["req_id"]: f["item_id"] for f in audit.list_items(run, "finding")
          if f["payload"]["source"] == "ai"}
    stab = check.stability(audit, run)
    assert stab[by["R2"]] == (3, 3) and stab[by["R3"]] == (1, 3) and stab[by["R4"]] == (1, 3)
    # running again does nothing; a failed pass is not recorded
    assert check.stability_check(cfg, audit, run, 3, workers=1).done == []
    FakeProvider.queue[:] = ["bad"] * 6
    assert check.stability_pass(cfg, audit, run, 4, workers=1).failed
    assert check.passes_done(audit, run) == [1, 2, 3]


def test_score_min_passes(cfg, audit, tmp_path):
    key = json.loads(KEY.read_text(encoding="utf-8"))
    g = key["requirements"][4]  # G05 carries not_testable in the key
    run = check.start(cfg, audit, _csv(tmp_path, f'ID,Requirement\n{g["gold_id"]},"{g["text"]}"\n',
                                       "one.csv")).run_id
    FakeProvider.queue[:] = [_ai([(g["gold_id"], "not_testable", "quickly")]), _ai([])]
    check.ai_review(cfg, audit, run, workers=1)
    FakeProvider.queue[:] = [_ai([]), _ai([])]
    check.stability_check(cfg, audit, run, 2, workers=1)
    assert "not_testable" in g["flags"]
    s1 = check.score(audit, run, KEY, ("ai",), min_passes=1)
    s2 = check.score(audit, run, KEY, ("ai",), min_passes=2)
    assert s1["found"] == 1 and s2["found"] == 0


def test_import_csv_with_long_quoted_and_multiline_cells(tmp_path):
    text = ('ID,Requirement\n'
            'A1,"In order to ensure that the severity, scope, and duration of this test, '
            'particular care must be taken, adequately, in accordance with ""SPEC 10""."\n'
            'A2,"Line one of the cell,\nline two of the same cell."\n')
    s = load_requirement_set(_csv(tmp_path, text, "quoted.csv"))
    assert [r.ext_id for r in s.requirements] == ["A1", "A2"]
    assert '"SPEC 10"' in s.requirements[0].text
    assert "line two" in s.requirements[1].text
