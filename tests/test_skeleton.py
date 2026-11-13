from __future__ import annotations

import json
import sqlite3

import pytest

from harness.config import load_config
from harness.models.fake_provider import FakeProvider
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.models.schema_tools import to_strict_schema
from harness.schemas.common import ReviewReport
from harness.schemas.smoke import SmokeExtraction
from harness.smoke import SMOKE_SOURCE, is_grounded, run_smoke

GOOD = json.dumps({"requirements": [
    {"text": "The cluster shall display fuel level as an eight-segment bar graph.",
     "source_quote": "The instrument cluster shall display the fuel level as a bar graph "
                     "with eight segments.",
     "req_type": "functional"},
    {"text": "The telltale shall be clearly visible.",
     "source_quote": "The telltale shall be bright.",  # not in source: ungrounded
     "req_type": "usability"},
]})
REVIEW = json.dumps({"reviews": [
    {"index": 0, "verdict": "accept", "issues": [], "suggested_text": None,
     "suggested_req_type": None},
    {"index": 1, "verdict": "revise", "issues": ["'clearly visible' is untestable"],
     "suggested_text": "The telltale shall be visible.", "suggested_req_type": None},
], "missed": ["DTC logging when fuel signal missing"]})


def test_project_config_loads_and_roles_resolve():
    cfg = load_config()
    assert cfg.profile("generator").provider == "anthropic"
    assert cfg.profile("claude-opus").model == "claude-opus-5-5"
    assert any(p.provider == "ollama" for p in cfg.profiles.values())


def test_strict_schema_is_closed_and_inlined():
    s = to_strict_schema(ReviewReport)
    text = json.dumps(s)
    assert "$ref" not in text and "$defs" not in text
    assert s["additionalProperties"] is False
    item = s["properties"]["reviews"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"index", "verdict", "issues", "suggested_text",
                                     "suggested_req_type"}
    assert item["properties"]["verdict"]["enum"] == ["accept", "revise", "reject"]


def test_invalid_output_is_retried_then_accepted(cfg, audit):
    FakeProvider.queue[:] = ['{"requirements": [{"text": "x"}]}', GOOD]
    run = audit.start_run("t")
    res = structured_call(cfg=cfg, audit=audit, run_id=run, role_or_profile="generator",
                          task="t", prompt_version="v", system="s", user="u",
                          output_model=SmokeExtraction)
    assert res.attempts == 2
    actions = [e["action"] for e in audit.events(run_id=run)]
    assert actions == ["validation_failed", "generated"]
    # the retry carried the validation errors back to the model
    assert "failed schema validation" in FakeProvider.calls[1]["messages"][-1]["content"]


def test_free_text_is_never_accepted(cfg, audit):
    FakeProvider.queue[:] = ["Sure! Here are the requirements..."] * 3
    run = audit.start_run("t")
    with pytest.raises(StructuredOutputFailure):
        structured_call(cfg=cfg, audit=audit, run_id=run, role_or_profile="generator",
                        task="t", prompt_version="v", system="s", user="u",
                        output_model=SmokeExtraction)
    actions = [e["action"] for e in audit.events(run_id=run)]
    assert actions == ["validation_failed"] * 3 + ["failed"]


def test_audit_store_is_append_only(audit):
    run = audit.start_run("t")
    iid = audit.add_item(run, "requirement", {"text": "a"}, created_by="model:x")
    audit.log_event("model:x", "generated", run_id=run)  # triggers are per-row: need a row
    with sqlite3.connect(audit.path) as con:
        for sql in ("UPDATE items SET payload_json='{}'", "DELETE FROM items",
                    "DELETE FROM events", "UPDATE runs SET note='x'"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                con.execute(sql)
    assert audit.get_item(iid)["payload"] == {"text": "a"}


def test_edit_versioning_and_decisions(audit):
    run = audit.start_run("t")
    iid = audit.add_item(run, "requirement", {"text": "a"}, created_by="model:x")
    assert audit.status(iid) == "proposed"
    audit.decide(iid, "approved", "Tom")
    assert audit.status(iid) == "approved"
    audit.edit_item(iid, {"text": "b"}, "Tom", comment="tighten")
    assert audit.status(iid) == "edited"  # approval was for v1, not v2
    assert audit.get_item(iid, version=1)["payload"] == {"text": "a"}  # history kept
    audit.decide(iid, "rejected", "Tom")
    assert audit.approved_items(run, "requirement") == []


def test_only_named_humans_can_decide(audit):
    run = audit.start_run("t")
    iid = audit.add_item(run, "requirement", {"text": "a"}, created_by="model:x")
    for actor in ("", "model", "ai-reviewer:claude-opus"):
        with pytest.raises(ValueError):
            audit.decide(iid, "approved", actor)


def test_grounding_check():
    assert is_grounded("the cluster shall illuminate  the LOW-FUEL telltale", SMOKE_SOURCE)
    assert not is_grounded("The telltale must be bright.", SMOKE_SOURCE)
    assert not is_grounded("   ", SMOKE_SOURCE)


def test_smoke_end_to_end_offline(cfg, audit):
    FakeProvider.queue[:] = [GOOD, REVIEW]
    summary = run_smoke(cfg, audit)
    assert summary["requirements"] == 2
    assert summary["ungrounded"] == ["REQ-SMOKE-002"]
    assert summary["ai_review"]["verdicts"] == {"accept": 1, "revise": 1, "reject": 0}
    items = audit.list_items(summary["run_id"], "requirement")
    assert {i["status"] for i in items} == {"proposed"}  # nothing auto-approved
    reviewed = [e for e in audit.events(run_id=summary["run_id"]) if e["action"] == "ai_reviewed"]
    assert {e["actor"] for e in reviewed} == {"ai-reviewer:fake-rev"}
    # the reviewer call used the reviewer profile, not the generator
    gen_events = [e for e in audit.events(run_id=summary["run_id"]) if e["action"] == "generated"]
    assert [e["model_profile"] for e in gen_events] == ["fake-gen", "fake-rev"]


def test_offline_mode_blocks_cloud_models_and_calls_are_kept_for_replay(cfg, audit,
                                                                        monkeypatch):
    from harness.config import Profile

    cfg.profiles["cloud"] = Profile(name="cloud", provider="anthropic", model="claude-x")
    run = audit.start_run("t")
    monkeypatch.setenv("ZYN_OFFLINE", "1")
    with pytest.raises(StructuredOutputFailure, match="offline"):
        structured_call(cfg=cfg, audit=audit, run_id=run, role_or_profile="cloud", task="t",
                        prompt_version="v", system="s", user="u", output_model=SmokeExtraction)
    assert any(e["action"] == "blocked_offline" for e in audit.events(run_id=run))
    FakeProvider.queue[:] = [GOOD]  # local providers still run offline
    structured_call(cfg=cfg, audit=audit, run_id=run, role_or_profile="generator", task="t",
                    prompt_version="v", system="sys", user="usr", output_model=SmokeExtraction)
    gen = next(e for e in audit.events(run_id=run) if e["action"] == "generated")
    assert (gen["detail"]["system"], gen["detail"]["user"], gen["detail"]["response"]) == (
        "sys", "usr", GOOD)
