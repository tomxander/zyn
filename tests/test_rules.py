"""Rule profiles choose Sift Review's code checks and tune the weak-word list."""

from __future__ import annotations

import pytest

from harness.sift import check
from harness.sift.rules import (
    CODE_CHECKS,
    RuleProfile,
    list_profiles,
    load_profile,
    save_profile,
)

REQS = [
    {"ext_id": "R1", "text": "The cluster shall show the speed quickly.", "heading": ""},
    {"ext_id": "R2", "text": "Speed display update rate TBD.", "heading": ""},
    {"ext_id": "R3", "text": "The cluster shall show the speed quickly.", "heading": ""},
    {"ext_id": "R4", "text": "The gauge shall be legible at night.", "heading": ""},
]


def cats(found, req=None):
    return sorted({f["category"] for f in found if req is None or f["req_id"] == req})


def test_shipped_profiles_load_and_match_the_old_behaviour():
    default, ears = load_profile("default"), load_profile("ears")
    assert "not_ears" not in default.checks and "not_ears" in ears.checks
    assert check.code_findings(REQS, profile=default) == check.code_findings(REQS)
    assert check.code_findings(REQS, profile=ears) == check.code_findings(REQS, style="ears")
    assert {p["name"] for p in list_profiles()} >= {"default", "ears"}


def test_checks_can_be_switched_off():
    only_weak = RuleProfile(name="t", checks=["weak_word"])
    assert cats(check.code_findings(REQS, profile=only_weak)) == ["weak_word"]


def test_weak_word_list_can_be_extended_and_relaxed():
    p = RuleProfile(name="t", checks=["weak_word"], weak_words_add=["legible"],
                    weak_words_allow=["quickly"])
    found = check.code_findings(REQS, profile=p)
    assert [f["evidence"] for f in found] == ["legible"]


def test_unknown_check_and_bad_name_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown checks"):
        RuleProfile(name="t", checks=["spelling"])
    with pytest.raises(ValueError):
        load_profile("../etc", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_profile("missing", tmp_path)


def test_save_and_reload_round_trip(tmp_path):
    p = RuleProfile(name="house", description="Ours", checks=list(CODE_CHECKS),
                    weak_words_add=["legible"])
    save_profile(p, tmp_path)
    back = load_profile("house", tmp_path)
    assert back == p and back.sha256 == p.sha256
    assert [x["name"] for x in list_profiles(tmp_path)] == ["default", "house"]


def test_run_records_the_profile_it_used(cfg, audit, tmp_path):
    f = tmp_path / "set.csv"
    f.write_text("ID,Text\nR1,The cluster shall show the speed quickly.\n", encoding="utf-8")
    run = check.start(cfg, audit, f, rules="ears").run_id
    meta = audit.get_item(f"SET-{run}")["payload"]
    assert meta["rules"]["name"] == "ears" and meta["style"] == "ears"
    assert meta["rules"]["sha256"] == load_profile("ears").sha256
