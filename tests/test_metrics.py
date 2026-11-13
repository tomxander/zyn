from __future__ import annotations

import json

from harness.config import Profile
from harness.metrics import run_metrics
from harness.models.fake_provider import FakeProvider
from harness.sift import check


def test_metrics_from_audit_log(cfg, audit, tmp_path):
    cfg.profiles["fake-rev"] = Profile(name="fake-rev", provider="fake", model="b",
                                       price_in=4.0, price_out=20.0)
    p = tmp_path / "s.csv"
    p.write_text("ID,Requirement\nR1,The gauge shall update quickly.\nR2,The lamp shall "
                 "be lit.\n", encoding="utf-8")
    run = check.start(cfg, audit, p).run_id
    FakeProvider.queue[:] = [json.dumps({"findings": [
        {"req_id": "R2", "category": "missing_condition", "evidence": "be lit",
         "explanation": "x", "question_for_author": "q", "related_ids": []}]}),
        json.dumps({"findings": []})]
    check.ai_review(cfg, audit, run, workers=1)
    fs = {f["payload"]["source"]: f["item_id"] for f in audit.list_items(run, "finding")}
    audit.decide(fs["code"], "approved", "Tom")
    audit.decide(fs["ai"], "rejected", "Tom")
    m = run_metrics(audit, run, cfg)
    assert m["model"]["calls"] == 2 and m["model"]["cost_complete"]
    assert m["review"]["finding"]["decided"] == 2
    assert m["review"]["finding"]["reviewers"] == ["Tom"]
    by = m["agreement"]["findings_by_source"]
    assert by["code"]["confirmed"] == 1 and by["ai"]["dismissed"] == 1
