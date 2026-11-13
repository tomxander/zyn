"""Calibrated reviewer (people's past decisions per kind of finding) and custom checks."""

from __future__ import annotations

import json

import pytest
import yaml

from harness import calibration
from harness.models.fake_provider import FakeProvider
from harness.sift import check, custom
from harness.sift.rules import RuleProfile, load_profile, save_profile
from tests.test_api import env  # noqa: F401  (fixture)
from tests.test_check import _csv

TIMING = {"name": "timing_has_unit", "description": "Timing requirements state a unit",
          "when": r"\b(within|after|every)\b",
          "must_match": r"\b\d+(\.\d+)?\s*(ms|s|seconds?|milliseconds?)\b",
          "must_not_match": None, "explanation": "A time without a unit cannot be tested.",
          "question": "In which unit is this time given?",
          "examples_pass": ["The chime shall sound within 200 ms."],
          "examples_fail": ["The chime shall sound within 200."]}
REQS = [{"ext_id": "A", "text": "The telltale shall be lit within 300 ms."},
        {"ext_id": "B", "text": "The telltale shall be lit within 300."},
        {"ext_id": "C", "text": "The gauge shall be white."}]


def test_custom_check_runs_as_code():
    found = custom.findings([TIMING], REQS)
    assert [(f["req_id"], f["category"], f["evidence"]) for f in found] == [
        ("B", "custom:timing_has_unit", "within")]
    t = custom.trial(TIMING, REQS)
    assert t["examples_ok"] and t["hit_rate"] == "1 of 3"
    bad = {**TIMING, "must_match": "(unclosed"}
    assert custom.trial(bad, REQS)["problems"] and custom.findings([bad], REQS) == []


def test_profile_custom_checks_run_in_sift_review():
    p = RuleProfile(name="t", checks=[], custom_checks=[TIMING])
    found = check.code_findings([{**r, "heading": ""} for r in REQS], profile=p)
    assert {f["req_id"] for f in found} == {"B"}


def test_draft_try_and_accept_with_a_named_person(cfg, audit, tmp_path, monkeypatch):
    monkeypatch.setattr(custom, "PROPOSALS", tmp_path / "proposals")
    FakeProvider.queue[:] = [json.dumps({**TIMING, "name": "Timing Has Unit!"})]
    res = custom.draft(cfg, audit, "Timing requirements state a unit", REQS)
    assert res["check"]["name"] == "timing_has_unit" and res["trial"]["examples_ok"]
    assert (tmp_path / "proposals" / "timing_has_unit.yaml").is_file()
    save_profile(RuleProfile(name="house"), tmp_path)
    with pytest.raises(ValueError, match="name"):
        custom.accept("timing_has_unit", "house", " ", tmp_path)
    custom.accept("timing_has_unit", "house", "Tom", tmp_path)
    p = load_profile("house", tmp_path)
    assert p.custom_checks[0]["accepted_by"] == "Tom" and p.custom_checks[0]["drafted_by"]
    # a draft whose own examples fail is refused
    broken = {**TIMING, "examples_fail": ["The chime shall sound within 200 ms."]}
    (tmp_path / "proposals" / "broken.yaml").write_text(yaml.safe_dump(broken),
                                                         encoding="utf-8")
    with pytest.raises(ValueError, match="examples"):
        custom.accept("broken", "house", "Tom", tmp_path)


def test_calibration_counts_decisions_per_source_category_and_model(cfg, audit, tmp_path):
    run = check.start(cfg, audit, _csv(tmp_path)).run_id
    weak = [f for f in audit.list_items(run, "finding")
            if f["payload"]["category"] == "weak_word"]
    audit.decide(weak[0]["item_id"], "approved", "Tom")
    recs = calibration.records(audit)
    assert recs[("code", "weak_word", "code")] == {
        "confirmed": 1, "dismissed": 0, "decided": 1, "precision": 1.0, "enough": False}
    assert "too few to judge" in calibration.label(recs[("code", "weak_word", "code")],
                                                   "code check")
    assert calibration.label(None, "AI reviewer").startswith("No earlier decisions")


def test_check_view_shows_the_record(env, tmp_path):  # noqa: F811
    audit, cfg, _run, c = env
    run = check.start(cfg, audit, _csv(tmp_path)).run_id
    v = c.get(f"/api/runs/{run}").json()
    assert all("label" in f["record"] for f in v["findings"])


def test_batched_decisions_match_one_by_one(cfg, audit, tmp_path):
    """Calibration reads every decision in one query; it must agree with the per-item read,
    including a decision that was later reopened."""
    run = check.start(cfg, audit, _csv(tmp_path)).run_id
    fs = [f["item_id"] for f in audit.list_items(run, "finding")]
    assert len(fs) >= 3
    audit.decide(fs[0], "approved", "Tom")
    audit.decide(fs[1], "rejected", "Tom")
    audit.decide(fs[2], "approved", "Tom")
    audit.decide(fs[2], "reopened", "Tom")
    batch = audit.latest_decisions()
    for f in fs:
        one = audit.latest_decision(f)
        assert (one or {}).get("event_id") == (batch.get(f) or {}).get("event_id")
    assert fs[2] not in batch and batch[fs[1]]["action"] == "rejected"
