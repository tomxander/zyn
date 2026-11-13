"""Proposed clarifications for flagged source wording (idea A in docs/02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.models.fake_provider import FakeProvider
from harness.sift import checks, pipeline
from harness.sift.export import export
from tests.test_sift import MD, _mapping, _req

SECTION = "2.1 The cluster shall show fuel. The gauge should update quickly."


# ---- code check ----------------------------------------------------------------------

def test_clarification_check_accepts_placeholders_and_catches_invention():
    quote = "The gauge should update quickly."
    good = "The gauge should update within <TBD: maximum update delay in ms> of a level change."
    assert checks.clarification_problems(good, quote, SECTION, ["weak_word"]) == []
    assert checks.placeholders(good) == ["<TBD: maximum update delay in ms>"]

    invented = "The gauge should update within 500 ms of a level change."
    assert any("invents values" in p for p in
               checks.clarification_problems(invented, quote, SECTION, ["weak_word"]))
    # numbers already in the section may be reused
    assert checks.clarification_problems("The gauge should update within 2.1 s.", quote,
                                         SECTION, ["weak_word"]) == []
    stronger = "The gauge shall update within <TBD: delay in ms>."
    assert any("modal" in p for p in
               checks.clarification_problems(stronger, quote, SECTION, ["weak_word"]))
    still_vague = "The gauge should update quickly after <TBD: event>."
    assert any("weak words" in p for p in
               checks.clarification_problems(still_vague, quote, SECTION, ["weak_word"]))
    noted = "The gauge should update within <TBD: delay>. [weak_word fixed]"
    assert any("notes" in p for p in
               checks.clarification_problems(noted, quote, SECTION, ["weak_word"]))
    assert any("missing_value" in p for p in checks.clarification_problems(
        "The gauge should update on every change.", quote, SECTION, ["missing_value"]))
    assert any("none of" in p for p in checks.clarification_problems(good, quote, SECTION, []))


# ---- pipeline ------------------------------------------------------------------------

def _run_with_flagged(cfg, audit, tmp_path) -> tuple[str, list[dict]]:
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"),
                                                      _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    for m in audit.list_items(run, "section_mapping"):
        audit.decide(m["item_id"], "approved", "Tom")
    FakeProvider.queue[:] = [json.dumps({"requirements": [
        _req("The cluster shall show fuel.", "The cluster shall show fuel.", "shall"),
        _req("The gauge should update quickly.", "The gauge should update quickly.", "should",
             flags=["weak_word", "missing_value"]),
    ]})]
    pipeline.extract(cfg, audit, run, reviewer=None, workers=1)
    return run, audit.list_items(run, "requirement")


def _proposal(index, text, resolves, questions=("What is the maximum delay?",)):
    return {"index": index, "proposed_text": text, "resolves": resolves,
            "open_questions": list(questions), "rationale": "quickly has no measure"}


def test_clarify_only_flagged_items_and_apply_creates_version(cfg, audit, tmp_path):
    run, reqs = _run_with_flagged(cfg, audit, tmp_path)
    flagged = reqs[1]["item_id"]
    assert [c["item_id"] for c in pipeline.clarify_candidates(audit, run)] == [flagged]

    FakeProvider.queue[:] = [json.dumps({"clarifications": [_proposal(
        0, "The gauge should update within <TBD: maximum update delay in ms>.",
        ["weak_word", "missing_value", "ambiguous"])]})]  # 'ambiguous' is not on the item
    calls = len(FakeProvider.calls)
    rep = pipeline.clarify(cfg, audit, run, workers=1)
    assert rep.done == ["S2"] and not rep.failed
    assert len(FakeProvider.calls) == calls + 1
    sent = FakeProvider.calls[-1]["messages"][-1]["content"]
    assert "The gauge should update quickly." in sent and "show fuel" not in sent.split(
        "Items:")[1]  # only the flagged item is sent

    ev = pipeline.latest_clarification(audit, flagged)
    assert ev["detail"]["resolves"] == ["weak_word", "missing_value"]
    assert ev["detail"]["problems"] == []
    assert pipeline.clarify_candidates(audit, run) == []  # not asked twice
    assert pipeline.clarify(cfg, audit, run, workers=1).done == []

    with pytest.raises(ValueError):
        audit.decide(flagged, "approved", "model")  # still a human-only decision
    v = pipeline.apply_clarification(audit, flagged, "Tom")
    item = audit.get_item(flagged)
    assert v == 2 and item["payload"]["quality_flags"] == []
    assert item["payload"]["source_quote"] == "The gauge should update quickly."  # source kept
    assert pipeline.open_placeholders(item["payload"]) == [
        "<TBD: maximum update delay in ms>"]
    edit = [e for e in audit.events(object_id=flagged) if e["action"] == "edited"][-1]
    assert edit["actor"] == "Tom" and edit["detail"]["source"] == "clarification"
    # the proposal was for v1; v2 has none of its own, so it cannot be applied again
    assert pipeline.latest_clarification(audit, flagged) is None

    audit.decide(flagged, "approved", "Tom")
    res = export(audit, run, "Tom", out_dir=tmp_path / "out")
    data = json.loads(Path(res["files"]["json"]).read_text(encoding="utf-8"))
    assert data["requirements"][0]["open_questions"] == "What is the maximum delay?"


def test_proposal_failing_code_check_cannot_be_applied(cfg, audit, tmp_path):
    run, reqs = _run_with_flagged(cfg, audit, tmp_path)
    flagged = reqs[1]["item_id"]
    FakeProvider.queue[:] = [json.dumps({"clarifications": [_proposal(
        0, "The gauge shall update within 500 ms.", ["weak_word", "missing_value"])]})]
    pipeline.clarify(cfg, audit, run, workers=1)
    problems = pipeline.latest_clarification(audit, flagged)["detail"]["problems"]
    assert any("modal" in p for p in problems) and any("500" in p for p in problems)
    with pytest.raises(ValueError, match="code check"):
        pipeline.apply_clarification(audit, flagged, "Tom")
    assert audit.get_item(flagged)["version"] == 1


def test_item_left_out_by_model_is_not_asked_again(cfg, audit, tmp_path):
    run, _ = _run_with_flagged(cfg, audit, tmp_path)
    FakeProvider.queue[:] = [json.dumps({"clarifications": []})]
    pipeline.clarify(cfg, audit, run, workers=1)
    assert pipeline.clarify_candidates(audit, run) == []


def test_failed_call_releases_claims_for_retry(cfg, audit, tmp_path):
    run, _ = _run_with_flagged(cfg, audit, tmp_path)
    FakeProvider.queue[:] = ["not json"] * cfg.max_attempts
    rep = pipeline.clarify(cfg, audit, run, workers=1)
    assert "S2" in rep.failed
    assert len(pipeline.clarify_candidates(audit, run)) == 1
    FakeProvider.queue[:] = [json.dumps({"clarifications": []})]
    assert pipeline.clarify(cfg, audit, run, workers=1).done == ["S2"]
