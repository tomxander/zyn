from __future__ import annotations

import json

from harness.bench import benchmark
from harness.config import Profile
from harness.models.fake_provider import FakeProvider

SPEC = "# Mini\n\n## 1 Fuel\n1.1 The gauge shall update quickly.\n"
KEY = {"sections": {"1": ["GAUGE"], "_title": ["NONE"]},
       "requirements": [{"gold_id": "R1", "text": "The gauge shall update quickly.",
                         "flags": ["weak_word", "not_testable"], "acceptable_flags": []}]}


def _map(sub):
    return json.dumps({"mappings": [{"section_id": "S1", "subsystem_id": sub,
                                     "confidence": 0.9, "rationale": "r"}]})


def _check(cat):
    return json.dumps({"findings": [{"req_id": "R1", "category": cat, "evidence": "quickly",
                                     "explanation": "x", "question_for_author": "q",
                                     "related_ids": []}]})


def test_benchmark_scores_stability_and_skips_unavailable(cfg, audit, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    cfg.profiles["cloud"] = Profile(name="cloud", provider="anthropic", model="x")
    spec, rs, key = tmp_path / "s.md", tmp_path / "r.csv", tmp_path / "k.json"
    spec.write_text(SPEC, encoding="utf-8")
    rs.write_text("ID,Requirement\nR1,The gauge shall update quickly.\n", encoding="utf-8")
    key.write_text(json.dumps(KEY), encoding="utf-8")
    empty = json.dumps({"findings": []})
    # map x2 (one wrong), then check x2 (batch + conflict pass each)
    FakeProvider.queue[:] = [_map("GAUGE"), _map("TT"),
                             _check("not_testable"), empty, _check("ambiguous"), empty]
    res = benchmark(cfg, audit, ["fake-rev", "cloud"], repeat=2, spec=spec, reqset=rs,
                    key_path=key, out_dir=tmp_path / "out")
    fr = res["profiles"]["fake-rev"]["tasks"]
    assert fr["map"]["correct_mean"] == 0.5 and fr["map"]["stability"] < 1.0
    # code finds the weak word both times; the AI adds not_testable once
    assert fr["check"]["found_mean"] == 1.5 and fr["check"]["of"] == 2
    assert fr["check"]["stability"] == 0.0
    assert res["profiles"]["cloud"]["status"] == "no API key"
    assert "| cloud | no API key" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
