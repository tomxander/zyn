from __future__ import annotations

import json
from pathlib import Path

from harness.anvil import impact
from harness.anvil import pipeline as forge
from harness.models.fake_provider import FakeProvider
from harness.sift import delta
from tests.test_delta import V2, _approved_run
from tests.test_forge import DBC, spec


def test_requirement_change_flows_from_delta_to_regenerated_tests(cfg, audit, tmp_path):
    sift_run = _approved_run(cfg, audit, tmp_path)
    s1 = {"specs": [
        spec(req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
             period_ms=100),
        spec(req_id="REQ-GAUGE-002", template="not_automatable", manual_test_idea="Read it."),
        spec(req_id="REQ-GAUGE-003", template="not_automatable", manual_test_idea="Open menu.")]}
    s2 = {"specs": [spec(req_id="REQ-AUD-001", template="event_response",
                         input_signal="DoorOpen", initial_value=0, input_value=1,
                         output_signal="ChimeActive", expected_value=1)]}
    FakeProvider.queue[:] = [json.dumps(s1), json.dumps(s2)]
    frun = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    specs = {s["payload"]["req_id"]: s["item_id"] for s in audit.list_items(frun, "test_spec")}
    for sid in specs.values():
        audit.decide(sid, "approved", "Tom")
    forge.generate(audit, frun, "Tom")
    before = len(audit.list_items(frun, "test_case"))

    new = tmp_path / "v2.md"
    new.write_text(V2, encoding="utf-8")
    drun = delta.spec_delta(cfg, audit, sift_run, new).run_id
    imp = impact.impact(audit, drun)
    assert imp["forge_runs"] == [frun]
    rows = {r["requirement_id"]: r for r in imp["rows"]}
    assert rows["REQ-GAUGE-001"]["kind"] == "changed" and rows["REQ-GAUGE-001"]["stale_cases"]
    assert rows["REQ-GAUGE-003"]["kind"] == "removed" and rows["REQ-GAUGE-003"]["stale_cases"]
    assert rows["REQ-AUD-001"]["kind"] == "moved" and not rows["REQ-AUD-001"]["stale_cases"]
    assert any("remaining range" in e["payload"]["new_text"] for e in imp["new_text"])

    n = impact.mark_stale(audit, drun, "Tom")
    assert n == len(rows["REQ-GAUGE-001"]["cases"]) + len(rows["REQ-GAUGE-003"]["cases"])
    assert impact.mark_stale(audit, drun, "Tom") == 0  # once per Delta

    # update the changed requirement from the Delta: proposal is the new source sentence
    entry = audit.get_item(rows["REQ-GAUGE-001"]["delta_item"])["payload"]
    req_item = rows["REQ-GAUGE-001"]["requirement_item"]
    text = impact.proposed_requirement_text(entry, audit.get_item(req_item))
    assert text == "The gauge shall update every 50 ms."
    impact.update_requirement(audit, req_item, text, entry, "Tom", drun)
    spec_now = audit.get_item(specs["REQ-GAUGE-001"])
    assert impact.spec_requirement_state(audit, spec_now["payload"]) == "pending"
    audit.decide(req_item, "approved", "Tom")
    assert impact.spec_requirement_state(audit, spec_now["payload"]) == "changed"
    assert forge.generate(audit, frun, "Tom")["cases"] == 0  # nothing until the spec is redone

    cands = [s["item_id"] for s in forge.repropose_candidates(audit, frun)]
    assert cands == [specs["REQ-GAUGE-001"]]
    FakeProvider.queue[:] = [json.dumps({"specs": [spec(
        req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
        period_ms=50)]})]
    forge.repropose(cfg, audit, frun)
    v2 = audit.get_item(specs["REQ-GAUGE-001"])
    assert v2["version"] == 2 and v2["payload"]["requirement_text"] == text
    assert v2["payload"]["problems"] == []
    audit.decide(specs["REQ-GAUGE-001"], "approved", "Tom")
    made = forge.generate(audit, frun, "Tom")["cases"]
    assert made >= 1
    cases = audit.list_items(frun, "test_case")
    assert len(cases) == before + made
    assert any(c["payload"]["case_id"].endswith("-v2") for c in cases)

    spec_items = {s["item_id"]: s for s in audit.list_items(frun, "test_spec")}
    states = {c["payload"]["case_id"]: impact.case_state(audit, c,
                                                         spec_items[c["payload"]["spec_item"]])
              for c in cases}
    assert states["TC-REQ-GAUGE-001-01"] == "superseded"
    assert states["TC-REQ-GAUGE-001-01-v2"] == "current"
    assert states["TC-REQ-GAUGE-003-01"] == "stale"
    out = forge.export(audit, frun, "Tom", out_dir=tmp_path / "out")
    exported = {c["case_id"] for c in json.loads(
        Path(out["files"]["json"]).read_text(encoding="utf-8"))["cases"]}
    assert "TC-REQ-GAUGE-001-01-v2" in exported
    assert not exported & {"TC-REQ-GAUGE-001-01", "TC-REQ-GAUGE-003-01"}
    assert out["left_out"] == 2 and out["lint"] == []
