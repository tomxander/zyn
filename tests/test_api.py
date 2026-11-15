"""The web API keeps the review rules: only a named person decides, an AI objection needs a
reason, failing specs cannot be approved, stages run as jobs, every run kind renders."""

from __future__ import annotations

import json
import time

import pytest
from starlette.testclient import TestClient

from harness.api.server import create_app
from harness.config import load_config
from harness.models.fake_provider import FakeProvider
from tests.test_review_ui import _seed


@pytest.fixture
def env(tmp_path, monkeypatch):
    audit, summary = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    return audit, cfg, summary["run_id"], TestClient(create_app(cfg, audit))


def test_runs_and_smoke_view(env):
    _audit, _cfg, run, c = env
    runs = c.get("/api/runs").json()
    assert runs[0]["run_id"] == run and runs[0]["tool"] == "Smoke test"
    v = c.get(f"/api/runs/{run}").json()
    assert v["kind"] == "smoke"
    cards = {r["item_id"]: r for r in v["requirements"]}
    assert cards["REQ-SMOKE-002"]["review"]["verdict"] == "revise"
    assert any(not ch["ok"] for c in cards.values() for ch in c["checks"])  # failed check shown
    assert c.get("/api/runs/nope").status_code == 404


def test_decide_needs_a_name_and_a_reason_over_an_ai_objection(env):
    audit, _cfg, run, c = env
    r = c.post("/api/decide", json={"item_id": "REQ-SMOKE-001", "decision": "approved"})
    assert r.status_code == 403
    assert c.post("/api/decide", json={"item_id": "REQ-SMOKE-001", "decision": "approved",
                                       "reviewer": "Tom"}).json()["status"] == "approved"
    r = c.post("/api/decide", json={"item_id": "REQ-SMOKE-002", "decision": "approved",
                                    "reviewer": "Tom"})
    assert r.status_code == 400 and "reason" in r.json()["error"]
    card = next(x for x in c.get(f"/api/runs/{run}").json()["requirements"]
                if x["item_id"] == "REQ-SMOKE-002")
    assert card["decision"]["needs_reason"] and card["decision"]["reasons"]
    assert c.post("/api/decide", json={"item_id": "REQ-SMOKE-002", "decision": "approved",
                                       "reviewer": "Tom",
                                       "comment": card["decision"]["reasons"][0]}).status_code == 200
    assert audit.latest_decision("REQ-SMOKE-002")["actor"] == "Tom"


def test_apply_ai_suggestion_makes_a_new_version(env):
    audit, _cfg, _run, c = env
    r = c.post("/api/edit", json={"item_id": "REQ-SMOKE-002", "kind": "apply_suggestion",
                                  "reviewer": "Tom"})
    assert r.status_code == 200 and r.json()["version"] == 2
    assert audit.get_item("REQ-SMOKE-002")["payload"]["text"] == "The telltale shall be visible."
    # applying again changes nothing, so the API refuses it
    assert c.post("/api/edit", json={"item_id": "REQ-SMOKE-002", "kind": "apply_suggestion",
                                     "reviewer": "Tom"}).status_code == 400


def test_edit_only_touches_allowed_fields(env):
    audit, _cfg, _run, c = env
    c.post("/api/edit", json={"item_id": "REQ-SMOKE-001", "kind": "edit", "reviewer": "Tom",
                              "fields": {"text": "New text.", "made_up": 1}})
    p = audit.get_item("REQ-SMOKE-001")["payload"]
    assert p["text"] == "New text." and "made_up" not in p


def test_failing_spec_cannot_be_approved(env, tmp_path):
    from harness.anvil import pipeline as forge
    from tests.test_delta import _approved_run
    from tests.test_forge import DBC, spec

    audit, cfg, _, c = env
    sift_run = _approved_run(cfg, audit, tmp_path)
    FakeProvider.queue[:] = [json.dumps({"specs": [spec(
        req_id="REQ-GAUGE-001", template="timeout", timeout_ms=100)]}), json.dumps({"specs": []})]
    run = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    v = c.get(f"/api/runs/{run}").json()
    assert v["kind"] == "forge" and v["specs"][0]["decision"]["block_approve"]
    r = c.post("/api/decide", json={"item_id": v["specs"][0]["item_id"], "decision": "approved",
                                    "reviewer": "Tom"})
    assert r.status_code == 400


def test_check_and_delta_views_and_decisions(env, tmp_path):
    from harness.sift import check, delta

    audit, cfg, _, c = env
    p = tmp_path / "set.csv"
    p.write_text("ID,Requirement\nR1,The gauge shall update quickly.\n", encoding="utf-8")
    run = check.start(cfg, audit, p).run_id
    v = c.get(f"/api/runs/{run}").json()
    assert v["kind"] == "check" and v["findings"][0]["state"] == "open"
    fid = v["findings"][0]["item_id"]
    c.post("/api/decide", json={"item_id": fid, "decision": "rejected", "reviewer": "Tom",
                                "comment": "Known and accepted"})
    assert audit.status(fid) == "rejected"
    (tmp_path / "a.csv").write_text("ID,Requirement\nR1,The lamp shall be lit in 1 s.\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("ID,Requirement\nR1,The lamp shall be lit in 2 s.\n", encoding="utf-8")
    drun = delta.set_delta(cfg, audit, tmp_path / "a.csv", tmp_path / "b.csv").run_id
    d = c.get(f"/api/runs/{drun}").json()
    assert d["kind"] == "delta" and d["entries"][0]["state"] == "open"


def test_stage_runs_as_a_job_with_a_trace(env, tmp_path):
    from harness.sift import pipeline
    from tests.test_sift import MD, _mapping

    audit, cfg, _, c = env
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"), _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    v = c.get(f"/api/runs/{run}").json()
    assert v["kind"] == "sift" and v["bulk_mappings"]
    assert c.post("/api/bulk", json={"kind": "mappings", "run_id": run, "reviewer": "Tom"}).json()["count"] == 2
    FakeProvider.queue[:] = []  # no answers queued: the extract stage fails and says so
    r = c.post(f"/api/runs/{run}/actions/extract", json={"reviewer": "Tom"})
    assert r.status_code == 202
    job = r.json()["job"]
    for _ in range(100):
        job = c.get(f"/api/jobs/{job['id']}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] in ("done", "failed") and job["elapsed"] >= 0
    assert "trace" in job and "label" in job


def test_downloads_only_from_runs_folder(env):
    _, _, _, c = env
    assert c.get("/api/download", params={"path": "config.yaml"}).status_code == 404


def test_config_and_audit_report_replay_and_knowledge(env):
    _audit, _cfg, run, c = env
    conf = c.get("/api/config").json()
    assert conf["replay"] is False and conf["knowledge"] == {"state": "off"}
    a = c.get(f"/api/runs/{run}/audit").json()
    assert a["knowledge"] == [] and a["metrics"]["model"]["replayed"] == 0


def test_undo_reopens_and_keeps_the_record(env):
    audit, _cfg, _run, c = env
    c.post("/api/decide", json={"item_id": "REQ-SMOKE-001", "decision": "approved", "reviewer": "Tom"})
    r = c.post("/api/decide", json={"item_id": "REQ-SMOKE-001", "decision": "reopened",
                                    "reviewer": "Tom"})
    assert r.json()["status"] == "proposed"
    assert audit.latest_decision("REQ-SMOKE-001") is None
    actions = [e["action"] for e in audit.events(object_id="REQ-SMOKE-001")]
    assert actions[-2:] == ["approved", "reopened"]
    # reopening something not decided records nothing
    c.post("/api/decide", json={"item_id": "REQ-SMOKE-001", "decision": "reopened", "reviewer": "Tom"})
    assert [e["action"] for e in audit.events(object_id="REQ-SMOKE-001")] == actions


def test_unknown_or_team_only_api_address_is_a_json_404_not_the_page(env):
    # The tokens drawer once got the web page back here in local mode and blanked the screen.
    _, _, _, c = env
    for path in ("/api/tokens", "/api/team-settings", "/api/no-such-thing"):
        r = c.get(path)
        assert r.status_code == 404 and r.json() == {"error": "Not found"}, path
