"""Replay of stored answers and the project knowledge file.

Replay: the same profile, model, prompt and input reuse the stored answer, logged as
"replayed" with zero tokens; anything that must ask again uses cfg.fresh().
Knowledge: the file's text goes into every system prompt, so it changes the prompt hash
and an answer given under an older version is never replayed for a newer one.
"""

from __future__ import annotations

import json

import pytest

from harness.api.views import knowledge_used, knowledge_view
from harness.config import Profile
from harness.metrics import model_calls
from harness.models.fake_provider import FakeProvider
from harness.models.runner import (
    KNOWLEDGE_HEADER,
    StructuredOutputFailure,
    sha256,
    structured_call,
)
from harness.models.schema_tools import to_strict_schema
from harness.schemas.smoke import SmokeExtraction

ANSWER = json.dumps({"requirements": [
    {"text": "The cluster shall show the fuel level.", "source_quote": "fuel level",
     "req_type": "functional"}]})


def call(cfg, audit, run, user="spec text", system="extract", profile="generator"):
    return structured_call(cfg=cfg, audit=audit, run_id=run, role_or_profile=profile,
                           task="extract", prompt_version="v1", system=system, user=user,
                           output_model=SmokeExtraction)


@pytest.fixture
def on(cfg):
    return cfg.model_copy(update={"replay": True})


def test_replay_is_off_unless_configured(cfg, audit):
    FakeProvider.queue[:] = [ANSWER, ANSWER]
    run = audit.start_run("t")
    call(cfg, audit, run)
    call(cfg, audit, run)
    assert len(FakeProvider.calls) == 2


def test_same_model_prompt_and_input_reuse_the_stored_answer(on, audit):
    FakeProvider.queue[:] = [ANSWER]
    first_run, second_run = audit.start_run("t"), audit.start_run("t")
    first = call(on, audit, first_run)
    again = call(on, audit, second_run)  # a later run, same text
    assert len(FakeProvider.calls) == 1
    assert again.output == first.output and again.replayed_from == first.event_id
    ev = audit.events(run_id=second_run)[-1]
    assert ev["action"] == "replayed" and ev["tokens_in"] == 0 and ev["latency_ms"] == 0
    assert ev["detail"]["from_run"] == first_run and ev["detail"]["response"] == ANSWER
    mc = model_calls(audit, second_run)
    assert mc["calls"] == 0 and mc["replayed"] == 1 and mc["tokens_in"] == 0


def test_changed_input_prompt_or_model_asks_again(on, audit):
    on.profiles["other"] = Profile(name="other", provider="fake", model="fake-model-c")
    FakeProvider.queue[:] = [ANSWER] * 4
    run = audit.start_run("t")
    call(on, audit, run)
    call(on, audit, run, user="spec text, revised")
    call(on, audit, run, system="extract v2 wording")
    call(on, audit, run, profile="other")
    assert len(FakeProvider.calls) == 4
    assert not [e for e in audit.events(run_id=run) if e["action"] == "replayed"]


def test_fresh_config_always_asks_again(on, audit):
    FakeProvider.queue[:] = [ANSWER, ANSWER]
    run = audit.start_run("t")
    call(on, audit, run)
    res = call(on.fresh(), audit, run)
    assert len(FakeProvider.calls) == 2 and res.replayed_from is None
    assert on.replay and not on.fresh().replay


def test_a_replay_is_never_the_source_of_another_replay(on, audit):
    FakeProvider.queue[:] = [ANSWER]
    run = audit.start_run("t")
    first = call(on, audit, run)
    call(on, audit, run)
    third = call(on, audit, run)
    assert third.replayed_from == first.event_id


def test_a_stored_answer_that_no_longer_fits_the_schema_is_not_replayed(on, audit):
    run = audit.start_run("t")
    schema = to_strict_schema(SmokeExtraction)
    audit.log_event("model:fake-gen", "generated", run_id=run, object_type="extract",
                    model_profile="fake-gen", provider="fake", model_requested="fake-model-a",
                    prompt_version="v1",
                    prompt_sha256=sha256("extract\n" + json.dumps(schema, sort_keys=True)),
                    input_sha256=sha256("spec text"), detail={"response": '{"old": 1}'})
    FakeProvider.queue[:] = [ANSWER]
    res = call(on, audit, run)
    assert len(FakeProvider.calls) == 1 and res.replayed_from is None


def test_offline_mode_still_replays_but_never_calls_a_cloud_model(on, audit, monkeypatch):
    on.profiles["cloud"] = Profile(name="cloud", provider="anthropic", model="claude-x")
    run = audit.start_run("t")
    schema = to_strict_schema(SmokeExtraction)
    audit.log_event("model:cloud", "generated", run_id=run, object_type="extract",
                    model_profile="cloud", provider="anthropic", model_requested="claude-x",
                    model_served="claude-x", prompt_version="v1",
                    prompt_sha256=sha256("extract\n" + json.dumps(schema, sort_keys=True)),
                    input_sha256=sha256("spec text"), detail={"response": ANSWER})
    monkeypatch.setenv("ZYN_OFFLINE", "1")
    assert call(on, audit, run, profile="cloud").replayed_from is not None
    with pytest.raises(StructuredOutputFailure, match="offline"):
        call(on, audit, run, user="new text", profile="cloud")


def test_knowledge_file_goes_into_every_call_and_the_record(cfg, audit, tmp_path):
    kfile = tmp_path / "knowledge.md"
    kfile.write_text("KL15 means ignition on.\nSpeeds are km/h.\n", encoding="utf-8")
    k_cfg = cfg.model_copy(update={"knowledge_file": str(kfile)})
    FakeProvider.queue[:] = [ANSWER]
    run = audit.start_run("t")
    call(k_cfg, audit, run)
    sent = FakeProvider.calls[0]["system"]
    assert sent.startswith("extract" + KNOWLEDGE_HEADER) and "KL15 means ignition on." in sent
    ev = next(e for e in audit.events(run_id=run) if e["action"] == "generated")
    assert ev["detail"]["knowledge"]["lines"] == 2
    assert ev["detail"]["system"] == sent
    used = knowledge_used(audit.events(run_id=run))
    assert used == [{"path": str(kfile), "sha": ev["detail"]["knowledge"]["sha256"][:8],
                     "lines": 2, "calls": 1, "of_calls": 1}]


def test_editing_the_knowledge_file_stops_replay_of_older_answers(cfg, audit, tmp_path):
    kfile = tmp_path / "knowledge.md"
    kfile.write_text("Speeds are km/h.", encoding="utf-8")
    k_cfg = cfg.model_copy(update={"knowledge_file": str(kfile), "replay": True})
    FakeProvider.queue[:] = [ANSWER, ANSWER]
    run = audit.start_run("t")
    call(k_cfg, audit, run)
    assert call(k_cfg, audit, run).replayed_from is not None  # unchanged file: reused
    kfile.write_text("Speeds are mph.", encoding="utf-8")
    assert call(k_cfg, audit, run).replayed_from is None      # edited: asked again
    assert len(FakeProvider.calls) == 2


def test_knowledge_view_states(cfg, tmp_path):
    assert knowledge_view(cfg) == {"state": "off"}
    missing = cfg.model_copy(update={"knowledge_file": str(tmp_path / "none.md")})
    assert knowledge_view(missing)["state"] == "empty" and missing.knowledge() is None
    (tmp_path / "blank.md").write_text("  \n", encoding="utf-8")
    blank = cfg.model_copy(update={"knowledge_file": str(tmp_path / "blank.md")})
    assert knowledge_view(blank)["state"] == "empty"
    (tmp_path / "k.md").write_text("a\nb\nc", encoding="utf-8")
    full = cfg.model_copy(update={"knowledge_file": str(tmp_path / "k.md")})
    v = knowledge_view(full)
    assert v["state"] == "in_use" and v["lines"] == 3 and len(v["sha"]) == 8


def test_repo_config_turns_both_on():
    from harness.config import load_config

    real = load_config()
    assert real.replay and real.knowledge_file == "knowledge.md"
