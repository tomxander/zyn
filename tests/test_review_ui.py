from __future__ import annotations

import json
from pathlib import Path

import yaml
from streamlit.testing.v1 import AppTest

from harness.audit.store import AuditStore
from harness.config import load_config
from harness.models.fake_provider import FakeProvider
from harness.smoke import run_smoke
from tests.test_skeleton import GOOD, REVIEW

APP = str(Path(__file__).resolve().parents[1] / "harness" / "review" / "app.py")


def _seed(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump({
        "db_path": str(tmp_path / "audit.sqlite"),
        "roles": {"generator": "g", "reviewer": "r"},
        "profiles": {"g": {"provider": "fake", "model": "a"},
                     "r": {"provider": "fake", "model": "b"}},
    }))
    monkeypatch.setenv("ZYN_CONFIG", str(cfg_path))
    cfg = load_config(cfg_path)
    audit = AuditStore(cfg.resolved_db_path())
    FakeProvider.queue[:] = [GOOD, REVIEW]
    return audit, run_smoke(cfg, audit)


def test_review_screen_renders_and_records_approval(tmp_path, monkeypatch):
    audit, summary = _seed(tmp_path, monkeypatch)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "Zyn prototype." in page
    assert "REQ-SMOKE-001" in page and "REQ-SMOKE-002" in page
    assert any("Ungrounded" in e.value for e in at.error)          # code check surfaced
    assert any("revise" in w.value for w in at.warning)            # AI verdict surfaced
    assert all(b.disabled for b in at.button if b.label == "Approve")  # no name, no decision

    at.sidebar.text_input("reviewer").set_value("Tom").run()
    next(b for b in at.button if b.key == "a-REQ-SMOKE-001").click().run()
    assert not at.exception
    assert audit.status("REQ-SMOKE-001") == "approved"
    assert audit.status("REQ-SMOKE-002") == "proposed"
    approvals = [e for e in audit.events(run_id=summary["run_id"]) if e["action"] == "approved"]
    assert [e["actor"] for e in approvals] == ["Tom"]

    # REQ-SMOKE-002 was flagged 'revise': approve is blocked until a reason is given,
    # and 'Apply AI suggestion' creates a new version that can be approved directly.
    assert next(b for b in at.button if b.key == "a-REQ-SMOKE-002").disabled
    next(b for b in at.button if b.key == "s-REQ-SMOKE-002").click().run()
    assert not at.exception
    item = audit.get_item("REQ-SMOKE-002")
    assert item["version"] == 2 and item["payload"]["text"] == "The telltale shall be visible."
    next(b for b in at.button if b.key == "a-REQ-SMOKE-002").click().run()
    assert audit.status("REQ-SMOKE-002") == "approved"


def test_sift_run_renders(tmp_path, monkeypatch):
    from harness.sift import pipeline
    from tests.test_sift import MD, _mapping

    audit, _ = _seed(tmp_path, monkeypatch)
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    cfg = load_config(tmp_path / "config.yaml")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"),
                                                      _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    assert not at.exception
    assert any("Mini spec" in s.value for s in at.markdown)
    assert len(at.tabs) == 4
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    next(b for b in at.button if b.key == "bulk").click().run()
    assert not at.exception
    assert {m["status"] for m in audit.list_items(run, "section_mapping")} == {"approved"}


def test_preset_reason_approves_and_note_suggestion_is_blocked(tmp_path, monkeypatch):
    from harness.sift import pipeline
    from tests.test_sift import MD, _mapping, _req

    audit, _ = _seed(tmp_path, monkeypatch)
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    cfg = load_config(tmp_path / "config.yaml")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"),
                                                      _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    for m in audit.list_items(run, "section_mapping"):
        audit.decide(m["item_id"], "approved", "Tom")
    FakeProvider.queue[:] = [
        json.dumps({"requirements": [
            _req("The cluster shall show fuel.", "The cluster shall show fuel.", "shall")]}),
        json.dumps({"reviews": [
            {"index": 0, "verdict": "revise", "objection_scope": "labels",
             "issues": ["flag missing"], "suggested_text": "The cluster shall show fuel. "
             "[Flags: ambiguous]", "suggested_req_type": None, "suggested_flags": None}],
            "missed": []})]
    pipeline.extract(cfg, audit, run, workers=1)
    iid = audit.list_items(run, "requirement")[0]["item_id"]

    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    assert not at.exception
    assert any("labels only" in w.value for w in at.warning)
    assert any("cannot be applied" in e.value for e in at.error)       # notes caught by code
    assert not [b for b in at.button if b.key == f"s-{iid}"]           # no one-click apply
    assert next(b for b in at.button if b.key == f"a-{iid}").disabled  # reason still required
    at.selectbox(key=f"o-{iid}").select(
        "Text is correct as written; the objection is only about type, flags or ASIL hint").run()
    next(b for b in at.button if b.key == f"a-{iid}").click().run()
    assert not at.exception
    assert audit.status(iid) == "approved"
    ev = [e for e in audit.events(object_id=iid) if e["action"] == "approved"][-1]
    assert ev["detail"]["ai_override"] is True
    assert "objection is only about" in ev["detail"]["comment"]


def test_clarification_is_proposed_shown_and_used(tmp_path, monkeypatch):
    from harness.sift import pipeline
    from tests.test_sift import MD, _mapping, _req

    audit, _ = _seed(tmp_path, monkeypatch)
    spec = tmp_path / "mini.md"
    spec.write_text(MD, encoding="utf-8")
    cfg = load_config(tmp_path / "config.yaml")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "NONE"),
                                                      _mapping("S2", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    for m in audit.list_items(run, "section_mapping"):
        audit.decide(m["item_id"], "approved", "Tom")
    FakeProvider.queue[:] = [json.dumps({"requirements": [
        _req("The gauge should update quickly.", "The gauge should update quickly.", "should",
             flags=["weak_word"])]})]
    pipeline.extract(cfg, audit, run, reviewer=None, workers=1)
    iid = audit.list_items(run, "requirement")[0]["item_id"]

    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    btn = next(b for b in at.button if b.key == "clarify")
    assert "1 flagged" in btn.label and not btn.disabled
    FakeProvider.queue[:] = [json.dumps({"clarifications": [{
        "index": 0, "proposed_text": "The gauge should update within <TBD: delay in ms>.",
        "resolves": ["weak_word"], "open_questions": ["What delay is acceptable?"],
        "rationale": "quickly has no measure"}]})]
    btn.click().run()
    assert not at.exception
    assert any("Proposed clarification" in i.value for i in at.info)
    next(b for b in at.button if b.key == f"c-{iid}").click().run()
    assert not at.exception
    item = audit.get_item(iid)
    assert item["version"] == 2 and "<TBD: delay in ms>" in item["payload"]["text"]
    assert any("placeholder(s) still open" in w.value for w in at.warning)
    assert not any("fails the code check" in e.value for e in at.error)
    next(b for b in at.button if b.key == f"a-{iid}").click().run()
    assert audit.status(iid) == "approved"


def test_sift_review_run_renders_and_records_decisions(tmp_path, monkeypatch):
    from harness.sift import check

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    p = tmp_path / "set.csv"
    p.write_text("ID,Requirement\nR1,The gauge shall update quickly.\n", encoding="utf-8")
    run = check.start(cfg, audit, p).run_id
    fid = audit.list_items(run, "finding")[0]["item_id"]
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    assert not at.exception
    assert any("Sift Review" in s.value for s in at.markdown)
    assert any("<mark>quickly</mark>" in m.value for m in at.markdown)
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    next(b for b in at.button if b.key == f"r-{fid}").click().run()
    assert not at.exception
    assert audit.status(fid) == "rejected"


def test_sift_delta_run_renders(tmp_path, monkeypatch):
    from harness.sift import delta

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    (tmp_path / "a.csv").write_text("ID,Requirement\nR1,The lamp shall be lit in 1 s.\n",
                                    encoding="utf-8")
    (tmp_path / "b.csv").write_text("ID,Requirement\nR1,The lamp shall be lit in 2 s.\n",
                                    encoding="utf-8")
    run = delta.set_delta(cfg, audit, tmp_path / "a.csv", tmp_path / "b.csv").run_id
    iid = audit.list_items(run, "delta_entry")[0]["item_id"]
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    assert not at.exception
    assert any("Sift Delta" in s.value for s in at.markdown)
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    next(b for b in at.button if b.key == f"a-{iid}").click().run()
    assert not at.exception and audit.status(iid) == "approved"


def test_forge_run_renders(tmp_path, monkeypatch):
    from harness.anvil import pipeline as forge
    from tests.test_delta import _approved_run
    from tests.test_forge import DBC, spec

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    sift_run = _approved_run(cfg, audit, tmp_path)
    FakeProvider.queue[:] = [json.dumps({"specs": [spec(
        req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
        period_ms=100)]}), json.dumps({"specs": []})]
    run = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    sid = audit.list_items(run, "test_spec")[0]["item_id"]
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    assert not at.exception
    assert any("Anvil" in s.value for s in at.markdown)
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    next(b for b in at.button if b.key == f"a-{sid}").click().run()
    next(b for b in at.button if b.key == "fgen").click().run()
    assert not at.exception
    assert audit.list_items(run, "test_case")


def test_delta_impact_tab_marks_cases_stale(tmp_path, monkeypatch):
    from harness.anvil import impact
    from harness.anvil import pipeline as forge
    from harness.sift import delta
    from tests.test_delta import V2, _approved_run
    from tests.test_forge import DBC, spec

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    sift_run = _approved_run(cfg, audit, tmp_path)
    FakeProvider.queue[:] = [json.dumps({"specs": [spec(
        req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
        period_ms=100)]}), json.dumps({"specs": []})]
    frun = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    sid = audit.list_items(frun, "test_spec")[0]["item_id"]
    audit.decide(sid, "approved", "Tom")
    forge.generate(audit, frun, "Tom")
    (tmp_path / "v2.md").write_text(V2, encoding="utf-8")
    drun = delta.spec_delta(cfg, audit, sift_run, tmp_path / "v2.md").run_id
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = drun
    at.run()
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    assert not at.exception
    next(b for b in at.button if b.key == "mstale").click().run()
    assert not at.exception
    case = audit.list_items(frun, "test_case")[0]["item_id"]
    assert impact.marked_stale(audit, case)[0]["delta_run"] == drun


def test_spec_failing_checks_cannot_be_approved_on_screen(tmp_path, monkeypatch):
    from harness.anvil import pipeline as forge
    from tests.test_delta import _approved_run
    from tests.test_forge import DBC, spec

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    sift_run = _approved_run(cfg, audit, tmp_path)
    FakeProvider.queue[:] = [json.dumps({"specs": [spec(
        req_id="REQ-GAUGE-001", template="timeout", timeout_ms=100)]}),
        json.dumps({"specs": []})]
    run = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    sid = audit.list_items(run, "test_spec")[0]["item_id"]
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    assert next(b for b in at.button if b.key == f"a-{sid}").disabled
    assert not next(b for b in at.button if b.key == f"r-{sid}").disabled


def test_bulk_approval_needs_the_read_box_and_clean_checks(tmp_path, monkeypatch):
    from harness.sift import pipeline
    from tests.test_sift import _mapping, _req

    audit, _ = _seed(tmp_path, monkeypatch)
    cfg = load_config(tmp_path / "config.yaml")
    spec = tmp_path / "m.md"
    spec.write_text("# Mini\n\n## 1 Fuel\n1.1 The gauge shall update every 100 ms.\n"
                    "1.2 The gauge should update quickly.\n", encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "GAUGE")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    audit.decide(audit.list_items(run, "section_mapping")[0]["item_id"], "approved", "Tom")
    ok = {"index": 0, "verdict": "accept", "objection_scope": "none", "issues": [],
          "suggested_text": None, "suggested_req_type": None, "suggested_flags": None}
    FakeProvider.queue[:] = [
        json.dumps({"requirements": [
            _req("The gauge shall update every 100 ms.", "The gauge shall update every 100 ms.",
                 "shall"),
            _req("The gauge shall update quickly.", "The gauge should update quickly.",
                 "should")]}),
        json.dumps({"reviews": [ok, {**ok, "index": 1}], "missed": []})]
    pipeline.extract(cfg, audit, run, workers=1)
    good, bad = (r["item_id"] for r in audit.list_items(run, "requirement"))
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pick_run"] = run
    at.run()
    at.sidebar.text_input("reviewer").set_value("Tom").run()
    assert next(b for b in at.button if b.key == "bulkreq").disabled  # box not ticked
    at.checkbox(key="bulkread").check().run()
    next(b for b in at.button if b.key == "bulkreq").click().run()
    assert not at.exception
    assert audit.status(good) == "approved"
    assert audit.status(bad) == "proposed"  # modal changed: a check failed, not bulk-approved
