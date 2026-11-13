"""Evidence report: five verdicts per item, JUnit XML, and a hash-chained audit export."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from harness import evidence
from harness.sift import check
from tests.test_api import env  # noqa: F401  (fixture)
from tests.test_check import CSV, _csv


def test_smoke_run_verdicts_follow_checks_and_decisions(env):  # noqa: F811
    audit, _cfg, run, _c = env
    v = evidence.verdicts(audit, run)
    by = {r["id"]: r for r in v["rows"]}
    assert by["REQ-SMOKE-001"]["verdict"] == "warn"   # not decided yet
    assert "FAIL" in " ".join(by["REQ-SMOKE-002"]["checks"])  # ungrounded quote shown
    audit.decide("REQ-SMOKE-001", "approved", "Tom")
    audit.decide("REQ-SMOKE-002", "rejected", "Tom", comment="not in the spec")
    by = {r["id"]: r for r in evidence.verdicts(audit, run)["rows"]}
    assert by["REQ-SMOKE-001"]["verdict"] in ("pass", "warn")
    assert by["REQ-SMOKE-002"]["verdict"] == "fail"
    assert by["REQ-SMOKE-002"]["decision"]["comment"] == "not in the spec"


def test_check_run_separates_findings_from_broken_batches(cfg, audit, tmp_path):
    extra = "R5,Fuel,The gauge shall show the fuel level.\n"
    run = check.start(cfg, audit, _csv(tmp_path, CSV + extra)).run_id
    rows = {r["id"]: r for r in evidence.verdicts(audit, run)["rows"]}
    assert rows["R1"]["verdict"] == "warn"   # code found 'quickly', undecided
    assert rows["R5"]["verdict"] == "pass" and "AI review not run" in rows["R5"]["reason"]
    fid = next(f["item_id"] for f in audit.list_items(run, "finding")
               if f["payload"]["req_id"] == "R1")
    audit.decide(fid, "approved", "Tom")
    assert {r["id"]: r for r in evidence.verdicts(audit, run)["rows"]}["R1"]["verdict"] == "fail"
    # the AI review ran for one batch but not another: those requirements are broken
    audit.log_event("code", "ai_batch_done", run_id=run, detail={"batch": 99})
    rows = {r["id"]: r for r in evidence.verdicts(audit, run)["rows"]}
    assert rows["R5"]["verdict"] == "broken"


def test_export_writes_html_junit_and_a_verifiable_chain(env, tmp_path):  # noqa: F811
    audit, cfg, run, _c = env
    res = evidence.export_evidence(audit, run, "Tom", cfg, out_dir=tmp_path)
    html = Path(res["files"]["html"]).read_text(encoding="utf-8")
    assert "REQ-SMOKE-001" in html and "not an assessment" in html and chr(0x2014) not in html
    suite = ET.parse(res["files"]["junit"]).getroot()[0]
    assert int(suite.get("tests")) == res["count"] == 2
    chain = json.loads(Path(res["files"]["chain"]).read_text(encoding="utf-8"))
    assert evidence.verify_chain(chain) == (True, None) and chain["head"] == res["chain_head"]
    chain["events"][1]["actor"] = "someone else"
    assert evidence.verify_chain(chain) == (False, 1)
    assert audit.events(run_id=run)[-1]["object_type"] == "evidence"  # the export is logged


def test_api_evidence_action(env):  # noqa: F811
    _audit, _cfg, run, c = env
    r = c.post(f"/api/runs/{run}/actions/evidence", json={"reviewer": "Tom"})
    assert r.status_code == 200, r.text
    assert set(r.json()["files"]) == {"html", "junit", "chain"}
    assert c.post(f"/api/runs/{run}/actions/evidence", json={}).status_code == 403
