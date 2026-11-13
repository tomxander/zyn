from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.config import PROJECT_ROOT
from harness.models.fake_provider import FakeProvider
from harness.sift import checks, pipeline
from harness.sift.export import export
from harness.sift.ingest import load_document, split_sections

SPEC = PROJECT_ROOT / "data" / "synthetic" / "icx100_srs.md"
KEY = PROJECT_ROOT / "data" / "synthetic" / "icx100_answer_key.json"


# ---- ingest --------------------------------------------------------------------------

def test_synthetic_spec_sections():
    doc = load_document(SPEC)
    numbers = [s.number for s in doc.sections if s.number]
    assert numbers == [str(n) for n in range(1, 16)]
    assert doc.title.startswith("ICX-100")
    tt = next(s for s in doc.sections if s.number == "7")
    assert "| Seat belt reminder |" in tt.text  # tables stay with their section


def test_numbered_heading_levels_and_duplicates():
    title, secs = split_sections("# T\n\n## 1 A\nx\n## 1.2 B\ny\n## 1.2 B\nz\n")
    assert title == "T"
    assert [(s.section_id, s.level) for s in secs] == [("S1", 1), ("S1.2", 2), ("S1.2-2", 2)]


def test_docx_goes_through_docling(tmp_path):
    from docx import Document

    d = Document()
    d.add_heading("Test spec", 0)
    d.add_heading("3 Power modes", 1)
    d.add_paragraph("3.1 The cluster shall enter the ACTIVE state within 1.5 s.")
    path = tmp_path / "spec.docx"
    d.save(path)
    doc = load_document(path)
    assert doc.converter == "docling"
    sec = next(s for s in doc.sections if s.number == "3")
    assert "ACTIVE state within 1.5 s" in sec.text


# ---- code checks -----------------------------------------------------------------------

def test_answer_key_quotes_are_grounded_in_spec():
    key = json.loads(KEY.read_text(encoding="utf-8"))
    text = SPEC.read_text(encoding="utf-8")
    for r in key["requirements"] + key["optional"] + key["not_requirements"]:
        assert checks.is_grounded(r["quote"], text), r["quote"]
    assert len(key["requirements"]) == 46


def test_table_row_grounding_tolerates_cell_spacing():
    src = "| Low fuel | FuelLow = 1 | Amber | Steady on |"
    assert checks.is_grounded("Low fuel | FuelLow = 1 | Amber | Steady on", src)
    assert checks.is_grounded("|Low fuel|FuelLow = 1|Amber|Steady on|", src)


def test_modal_and_weak_words():
    assert checks.modal_changed("The telltale should be visible.", "The telltale shall be visible.")
    assert not checks.modal_changed("X shall do Y and shall do Z.", "X shall do Z.")
    assert not checks.modal_changed("| Low fuel | Amber |", "The cluster shall light it.")
    assert checks.weak_words("should wake up quickly and adequately") == ["adequately", "quickly"]
    assert checks.weak_words("The cluster shall display speed.") == []


# ---- override rule -----------------------------------------------------------------------

def test_override_needs_reason_unless_ai_fix_applied(audit):
    run = audit.start_run("t")
    iid = audit.add_item(run, "requirement", {"text": "a"}, created_by="model:x")
    audit.log_event("ai-reviewer:x", "ai_reviewed", run_id=run, object_id=iid, object_version=1,
                    detail={"verdict": "revise", "suggested_text": "b"})
    with pytest.raises(ValueError, match="needs a reason"):
        audit.decide(iid, "approved", "Tom")
    audit.decide(iid, "rejected", "Tom")  # rejecting never needs a reason
    audit.decide(iid, "approved", "Tom", comment="source wording is binding as written")
    ev = [e for e in audit.events(object_id=iid) if e["action"] == "approved"][-1]
    assert ev["detail"]["ai_override"] is True

    audit.edit_item(iid, {"text": "b"}, "Tom", source="ai_suggestion")
    audit.decide(iid, "approved", "Tom")  # AI's own fix: no override reason needed
    audit.edit_item(iid, {"text": "c"}, "Tom")  # manual edit away from it: reason needed again
    with pytest.raises(ValueError):
        audit.decide(iid, "approved", "Tom")
    # an "AI fix" that changes nothing does not clear the objection
    audit.edit_item(iid, {"text": "c"}, "Tom", source="ai_suggestion")
    with pytest.raises(ValueError, match="needs a reason"):
        audit.decide(iid, "approved", "Tom")


# ---- pipeline offline --------------------------------------------------------------------

MD = """# Mini spec

## 1 Introduction
This is an introduction.

## 2 Fuel
2.1 The cluster shall show fuel. The gauge should update quickly.
"""


def _mapping(sid, sub, conf=0.95):
    return {"section_id": sid, "subsystem_id": sub, "confidence": conf, "rationale": "r"}


def _req(text, quote, modal, flags=()):
    return {"text": text, "source_quote": quote, "req_type": "functional", "modal": modal,
            "verification_method": "test", "quality_flags": list(flags), "asil_hint": "none"}


def test_pipeline_gates_on_approval_and_exports(cfg, audit, tmp_path):
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [
        _mapping("S-mini-spec", "NONE"), _mapping("S1", "NONE"), _mapping("S2", "GAUGE")]})]
    rep = pipeline.start(cfg, audit, spec)
    run = rep.run_id
    assert set(rep.done) == {"S1", "S2"}  # empty title section is dropped by the parser

    # nothing approved yet: extract does no model calls
    assert pipeline.extract(cfg, audit, run, workers=1).done == []
    assert FakeProvider.queue == []

    for m in audit.list_items(run, "section_mapping"):
        audit.decide(m["item_id"], "approved", "Tom")
    FakeProvider.queue[:] = [
        json.dumps({"requirements": [
            _req("The cluster shall show fuel.", "The cluster shall show fuel.", "shall"),
            _req("The gauge shall update quickly.", "The gauge should update quickly.",
                 "should"),  # modal strengthened and weak word unflagged: code must catch both
        ]}),
        json.dumps({"reviews": [
            {"index": 0, "verdict": "accept", "objection_scope": "none", "issues": [],
             "suggested_text": None, "suggested_req_type": None, "suggested_flags": None},
            {"index": 1, "verdict": "revise", "objection_scope": "text",
             "issues": ["should became shall"], "suggested_text": "The gauge should update "
             "quickly. [Flags: weak_word]", "suggested_req_type": None,
             "suggested_flags": ["weak_word"]}],
            "missed": []}),
    ]
    rep2 = pipeline.extract(cfg, audit, run, workers=1)
    assert rep2.done == ["S2"] and rep2.skipped == ["S1"]
    reqs = audit.list_items(run, "requirement")
    assert [pipeline.display_id(r["item_id"]) for r in reqs] == ["REQ-GAUGE-001", "REQ-GAUGE-002"]
    bad = reqs[1]["payload"]
    assert bad["grounded"] and bad["modal_changed"] and bad["weak_word_unflagged"]
    # reviewer v3: scope recorded, and a suggestion carrying notes is caught by the code check
    rv = audit.latest_ai_review(reqs[1]["item_id"])["detail"]
    assert rv["objection_scope"] == "text"
    assert any("notes" in x for x in rv["suggestion_problems"])

    # re-running extract is a no-op for sections already done
    assert pipeline.extract(cfg, audit, run, workers=1).done == []

    with pytest.raises(ValueError):
        export(audit, run, "Tom", out_dir=tmp_path / "out")  # nothing approved
    audit.decide(reqs[0]["item_id"], "approved", "Tom")
    audit.decide(reqs[1]["item_id"], "approved", "Tom", comment="kept for demo")
    res = export(audit, run, "Tom", out_dir=tmp_path / "out")
    assert res["count"] == 2

    data = json.loads(Path(res["files"]["json"]).read_text(encoding="utf-8"))
    assert data["requirements"][1]["override_reason"] == "kept for demo"

    from openpyxl import load_workbook
    ws = load_workbook(res["files"]["xlsx"]).active
    assert ws.cell(3, 1).value == "REQ-GAUGE-001"

    from reqif.parser import ReqIFParser
    bundle = ReqIFParser.parse(res["files"]["reqif"])
    objs = bundle.core_content.req_if_content.spec_objects
    assert [o.long_name for o in objs] == ["REQ-GAUGE-001", "REQ-GAUGE-002"]
    assert any(e["action"] == "exported" for e in audit.events(run_id=run))


def test_concurrent_extraction_is_blocked_and_repeat_clicks_are_ignored(cfg, audit, tmp_path):
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"),
                                                      _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    maps = audit.list_items(run, "section_mapping")
    for m in maps:
        audit.decide(m["item_id"], "approved", "Tom")
    # a double click on Approve records one decision, not two
    audit.decide(maps[0]["item_id"], "approved", "Tom")
    assert len([e for e in audit.events(object_id=maps[0]["item_id"])
                if e["action"] == "approved"]) == 1

    # another process (second tab, CLI) already holds S2: this run skips it, no model calls
    assert audit.claim(run, "extract:S2", "other")
    assert not audit.claim(run, "extract:S2", "again")
    calls_before = len(FakeProvider.calls)
    rep = pipeline.extract(cfg, audit, run, workers=1)
    assert rep.done == [] and "S2" in rep.skipped
    assert len(FakeProvider.calls) == calls_before

    # a released claim (the holder failed) can be taken again
    audit.release(run, "extract:S2", "other")
    assert audit.claim(run, "extract:S2", "retry")
