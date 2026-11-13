"""Page and position pinning, EARS, earlier override reasons, bulk approval, edit diff."""
from __future__ import annotations

import json
from types import SimpleNamespace

from harness.models.fake_provider import FakeProvider
from harness.sift import check, pipeline
from harness.sift.ingest import heading_pages
from tests.test_sift import _mapping, _req


def test_heading_pages_from_docling_provenance():
    item = SimpleNamespace(label="section_header", text="3 Power modes",
                           prov=[SimpleNamespace(page_no=4)])
    body = SimpleNamespace(label="text", text="The cluster shall ...",
                           prov=[SimpleNamespace(page_no=4)])
    doc = SimpleNamespace(iterate_items=lambda: [(item, 1), (body, 2)])
    assert heading_pages(doc) == {"3 power modes": 4}
    assert heading_pages(object()) == {}


def test_quote_offset_tolerates_whitespace():
    text = "3.1 The cluster  shall enter" + chr(10) + "the ACTIVE state."
    off = pipeline.quote_offset("The cluster shall enter the ACTIVE state.", text)
    assert off and text[off[0]:off[1]].startswith("The cluster")
    assert pipeline.quote_offset("not there", text) is None


def test_ears_check_only_when_asked():
    reqs = [{"ext_id": "A", "text": "When IGN is ON, the cluster shall show the logo.",
             "heading": ""},
            {"ext_id": "B", "text": "In the SLEEP state, the cluster shall draw 0.1 mA.",
             "heading": ""}]
    assert not [f for f in check.code_findings(reqs) if f["category"] == "not_ears"]
    got = [f["req_id"] for f in check.code_findings(reqs, "ears") if f["category"] == "not_ears"]
    assert got == ["B"]


def _run_with_objection(cfg, audit, tmp_path, name):
    from harness.sift import pipeline as sp
    spec = tmp_path / name
    spec.write_text("# Mini\n\n## 1 Fuel\n1.1 The gauge should update quickly.\n",
                    encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "GAUGE")]})]
    run = sp.start(cfg, audit, spec).run_id
    audit.decide(audit.list_items(run, "section_mapping")[0]["item_id"], "approved", "Tom")
    FakeProvider.queue[:] = [
        json.dumps({"requirements": [_req("The gauge should update quickly.",
                                          "The gauge should update quickly.", "should",
                                          ["weak_word"])]}),
        json.dumps({"reviews": [{"index": 0, "verdict": "revise", "objection_scope": "labels",
                                 "issues": ["x"], "suggested_text": None,
                                 "suggested_req_type": None, "suggested_flags": None}],
                    "missed": []})]
    sp.extract(cfg, audit, run, workers=1)
    return run, audit.list_items(run, "requirement")[0]


def test_earlier_override_reason_is_found_for_same_wording(cfg, audit, tmp_path):
    run1, r1 = _run_with_objection(cfg, audit, tmp_path, "a.md")
    audit.decide(r1["item_id"], "approved", "Tom", comment="vague on purpose, tracked")
    _, r2 = _run_with_objection(cfg, audit, tmp_path, "b.md")
    prior = pipeline.earlier_override(audit, r2)
    assert prior["reason"] == "vague on purpose, tracked" and prior["run_id"] == run1
    assert pipeline.earlier_override(audit, r1) is None  # nothing earlier for the first
