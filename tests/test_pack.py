"""Benchmark pack: manifest pins data, runner summarises repeats, export writes both formats."""

from __future__ import annotations

import csv
import json
import os

from harness import pack
from harness.config import load_config


def test_manifest_pins_every_file_and_marks_tasks_ready():
    m = pack.manifest()
    assert m["pack"] == pack.PACK_VERSION and set(m["tasks"]) == set(pack.TASKS)
    for t in m["tasks"].values():
        assert t["ready"] and all(len(h) == 64 for h in t["files"].values())


def test_run_summarises_repeats_without_replay_or_knowledge(tmp_path):
    seen_env = []

    def fake(profile):
        seen_env.append((os.environ.get("ZYN_NO_REPLAY"), load_config().replay,
                         load_config().knowledge_file))
        n = len(seen_env)
        if n == 3:
            raise RuntimeError("model down")
        return {"score": [0.5, 0.75][n - 1], "correct": [5, 6][n - 1], "cost_usd": 0.1,
                "answers": [["a", "b"], ["a", "c"]][n - 1]}

    res = pack.run_pack(["m"], ["icx-review"], repeat=3, runners={"icx-review": fake},
                        out_dir=tmp_path)
    s = res["results"]["m"]["icx-review"]
    assert s["errors"] == 1 and s["score_mean"] == 0.625 and s["score_spread"] == 0.25
    assert s["cost_per_correct_usd"] == round(0.2 / 11, 5)
    assert s["item_agreement"] == round(1 / 3, 2)
    assert all(e == ("1", False, None) for e in seen_env)
    assert os.environ.get("ZYN_NO_REPLAY") is None  # restored afterwards
    md = (tmp_path / "results.md").read_text(encoding="utf-8")
    assert "ICX-100 requirement review" in md and "sha256" in md


def test_export_writes_inspect_and_promptfoo_files(tmp_path):
    res = pack.export(tmp_path, ["promise-type", "icx-review"])
    assert res["tasks"] == {"promise-type": 625, "icx-review": 46}
    first = json.loads((tmp_path / "inspect" / "promise-type.jsonl").open(
        encoding="utf-8").readline())
    assert set(first) == {"id", "input", "target", "metadata"}
    assert first["target"] in ("functional", "non-functional")
    rows = list(csv.DictReader((tmp_path / "promptfoo" / "icx-review.csv").open(
        encoding="utf-8")))
    assert rows[0].keys() == {"id", "input", "__expected"} and len(rows) == 46
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["pack"]


def test_knowledge_ab_run_adds_the_file_and_says_so(tmp_path):
    k = tmp_path / "k.md"
    k.write_text("Speeds are km/h.", encoding="utf-8")
    seen = []

    def fake(profile):
        c = load_config()
        seen.append((c.replay, c.knowledge() and c.knowledge().text))
        return {"score": 1.0, "correct": 1, "cost_usd": 0.0}

    res = pack.run_pack(["m"], ["icx-review"], repeat=1, runners={"icx-review": fake},
                        out_dir=tmp_path / "out", knowledge=k)
    assert seen == [(False, "Speeds are km/h.")]
    assert res["knowledge"]["file"] == "k.md" and len(res["knowledge"]["sha256"]) == 64
    assert "A/B run" in (tmp_path / "out" / "results.md").read_text(encoding="utf-8")
    assert os.environ.get("ZYN_KNOWLEDGE_FILE") is None


def test_rtems_whole_scores_f1(monkeypatch):
    from evals import rtems

    monkeypatch.setattr(rtems, "run", lambda profiles, whole=False: {"profiles": {
        "m": {"recall": 1.0, "matched": 8, "extracted": 10, "extra": 2, "cost_usd": 0.1,
              "run_id": "r"}}})
    r = pack.RUNNERS["rtems-whole"]("m")
    assert r["precision"] == 0.8 and r["score"] == round(2 * 0.8 / 1.8, 3)
