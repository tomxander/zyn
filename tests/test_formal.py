"""Formal statements from Anvil specs, and set-level contradiction checks."""

from __future__ import annotations

from harness.anvil.dbc import load_dbc
from harness.anvil.formal import check_set, statement
from harness.mcp_server import handle
from tests.test_forge import DBC, spec

LOW_FUEL = spec(req_id="R1", template="threshold", input_signal="FuelLevel", threshold=10,
                direction="below", output_signal="TT_LowFuel", expected_value=1,
                max_latency_ms=300)
GOODBYE = spec(req_id="R2", template="event_response", input_signal="IGN", initial_value=1,
               input_value=0, output_signal="ClusterState", expected_value=2, hold_ms=5000)
SLEEP_NOW = spec(req_id="R3", template="event_response", input_signal="IGN", initial_value=1,
                 input_value=0, output_signal="ClusterState", expected_value=0)
SLEEP_AFTER = {**SLEEP_NOW, "req_id": "R4", "max_latency_ms": 6000}


def test_statements_read_like_ears():
    assert statement(LOW_FUEL) == "When FuelLevel < 10, TT_LowFuel shall be 1 within 300 ms."
    assert statement(GOODBYE) == ("When IGN changes from 1 to 0, ClusterState shall be 2 for "
                                  "5000 ms.")
    assert statement(spec(template="not_automatable")) is None


def test_a_spec_that_lost_its_after_conflicts_and_a_sequence_does_not():
    db = load_dbc(DBC)
    r = check_set([GOODBYE, SLEEP_NOW], db)
    assert [i["requirements"] for i in r["issues"]] == [["R2", "R3"]]
    assert "lost an 'after'" in r["issues"][0]["explanation"]
    assert check_set([GOODBYE, SLEEP_AFTER], db)["issues"] == []


def test_threshold_overlap_timeout_and_band_issues():
    db = load_dbc(DBC)
    off = {**LOW_FUEL, "req_id": "R5", "threshold": 15, "expected_value": 0}
    t1 = spec(req_id="T1", template="timeout", message="Warnings", timeout_ms=500,
              output_signal="TT_Brake", expected_value=1)
    t2 = {**t1, "req_id": "T2", "timeout_ms": 300}
    band = spec(req_id="B1", template="tracking", input_signal="VehicleSpeed",
                output_signal="DisplayedSpeed", track_low_factor=1.2, track_high_factor=1.1)
    kinds = sorted(i["kind"] for i in check_set([LOW_FUEL, off, t1, t2, band], db)["issues"])
    assert kinds == ["band", "conflict", "timeout"]
    assert "TT_Belt" in check_set([LOW_FUEL], db)["uncovered_outputs"]


def test_mcp_check_specs():
    r = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "check_specs", "arguments": {"specs": [GOODBYE, SLEEP_NOW]}}})
    assert r["result"]["structuredContent"]["issues"][0]["kind"] == "conflict"


def test_anvil_view_carries_statements_and_issues(cfg, audit, tmp_path):
    from harness.api import views
    from tests.test_forge import test_forge_pipeline_end_to_end

    test_forge_pipeline_end_to_end(cfg, audit, tmp_path)
    run = next(r["run_id"] for r in audit.list_runs() if r["workflow"] == "forge")
    v = views.run_view(audit, run)
    assert set(v["formal"]) == {"statements", "issues", "uncovered_outputs"}
    cards = {c["payload"]["req_id"]: c for c in v["specs"]}
    assert cards["REQ-GAUGE-001"]["statement"] == "The cluster shall send ClusterStatus every 100 ms."
    assert all("formal_issues" in c for c in cards.values())
