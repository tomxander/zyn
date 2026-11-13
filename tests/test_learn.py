"""Reviewer learning: proposals from people's decisions, replayed before acceptance."""

from __future__ import annotations

import pytest

from harness import learn
from harness.sift import check
from harness.sift.rules import RuleProfile, load_profile, save_profile
from tests.test_check import _csv

SET = ("ID,Text\n"
       "A1,The gauge shall update quickly.\nA2,The chime shall be quickly audible.\n"
       "A3,The needle shall move quickly.\nA4,The display shall be sufficient.\n")


@pytest.fixture
def rules_tmp(tmp_path, monkeypatch):
    import harness.sift.rules as r
    monkeypatch.setattr(r, "RULES_DIR", tmp_path / "rules")
    save_profile(RuleProfile(name="default"), tmp_path / "rules")
    return tmp_path / "rules"


def _decide_all(audit, run, category, word, decision, comment=None):
    for f in audit.list_items(run, "finding"):
        if f["payload"]["category"] == category and f["payload"]["evidence"] == word:
            audit.decide(f["item_id"], decision, "Tom", comment=comment)


def test_word_dismissed_repeatedly_is_proposed_and_replayed(cfg, audit, tmp_path, rules_tmp):
    run = check.start(cfg, audit, _csv(tmp_path, SET)).run_id
    _decide_all(audit, run, "weak_word", "quickly", "rejected", "Not a problem in this context")
    _decide_all(audit, run, "weak_word", "sufficient", "approved")
    props = learn.proposals(audit)
    allow = [p for p in props if p["kind"] == "allow_word"]
    assert [p["change"] for p in allow] == [{"weak_words_allow": ["quickly"]}]
    assert allow[0]["effect"] == {"dismissed_removed": 3, "confirmed_removed": 0,
                                  "measured_on": 4}
    with pytest.raises(ValueError, match="name"):
        learn.accept(audit, allow[0], "")
    learn.accept(audit, allow[0], "Tom")
    assert load_profile("default").weak_words_allow == ["quickly"]
    assert any(e["action"] == "proposal_accepted" for e in audit.events())
    assert not [p for p in learn.proposals(audit) if p["kind"] == "allow_word"]  # applied


def test_a_change_that_would_hide_confirmed_findings_is_refused(cfg, audit, rules_tmp):
    p = {"id": "x", "kind": "check_off", "profile": "default",
         "change": {"checks_off": ["no_modal"]},
         "effect": {"dismissed_removed": 9, "confirmed_removed": 1}}
    with pytest.raises(ValueError, match="confirmed"):
        learn.accept(audit, p, "Tom")


def test_defined_elsewhere_dismissals_become_a_knowledge_proposal(cfg, audit, tmp_path,
                                                                    rules_tmp):
    run = check.start(cfg, audit, _csv(tmp_path, SET)).run_id
    _decide_all(audit, run, "weak_word", "quickly", "rejected", learn.DEFINED_ELSEWHERE)
    k = next(p for p in learn.proposals(audit) if p["kind"] == "knowledge")
    assert "quickly" in k["change"]["knowledge_lines"][0] and "not_measured" in k["effect"]
    kfile = tmp_path / "knowledge.md"
    learn.accept(audit, k, "Tom", cfg.model_copy(update={"knowledge_file": str(kfile)}))
    text = kfile.read_text(encoding="utf-8")
    assert "accepted by Tom" in text and "quickly" in text
