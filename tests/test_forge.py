from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.anvil import pipeline as forge
from harness.anvil.dbc import load_dbc
from harness.anvil.generate import generate_cases
from harness.anvil.simulate import fault_check
from harness.anvil.validate import validate
from harness.models.fake_provider import FakeProvider
from tests.test_delta import _approved_run

DBC = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "icx100.dbc"


@pytest.fixture(scope="module")
def db():
    return load_dbc(DBC)


def spec(**k):
    base = {"req_id": "R", "template": None, "input_signal": None, "initial_value": None,
            "input_value": None, "threshold": None, "direction": None, "output_signal": None,
            "expected_value": None, "max_latency_ms": None, "hold_ms": None, "message": None,
            "timeout_ms": None, "period_ms": None, "track_low_factor": None,
            "track_low_offset": None, "track_high_factor": None, "track_high_offset": None,
            "track_bounds": [],
            "value_sources": [], "assumptions": [],
            "missing": [], "manual_test_idea": None, "rationale": "r"}
    base.update(k)
    return base


FUEL = "When the fuel level is below 10 percent, the low-fuel telltale shall be lit."


def test_validation_traces_every_value(db):
    ok = spec(template="threshold", input_signal="FuelLevel", threshold=10, direction="below",
              output_signal="TT_LowFuel", expected_value=1,
              value_sources=[{"param": "threshold", "quote": "below 10 percent"}])
    assert validate(ok, FUEL, db) == []
    assert "threshold 12 does not appear" in validate({**ok, "threshold": 12}, FUEL, db)[0]
    act = spec(template="event_response", input_signal="IGN", initial_value=0, input_value=1,
               output_signal="ClusterState", expected_value=1, max_latency_ms=1500)
    assert validate(act, "enter ACTIVE within 1.5 s of IGN ON", db) == []  # 1.5 s -> 1500 ms
    bad = validate({**ok, "input_signal": "TT_Brake", "output_signal": "FuelLow",
                    "value_sources": [{"param": "threshold", "quote": "under ten"}]}, FUEL, db)
    assert any("sent by the cluster" in p for p in bad)
    assert any("input to the cluster" in p for p in bad)
    assert any("source quote" in p for p in bad)
    assert any("outside" in p for p in validate({**ok, "threshold": 150}, "150", db))
    assert validate(spec(template="not_automatable"), FUEL, db) == [
        "not_automatable needs a manual test idea"]


@pytest.mark.parametrize("s", [
    spec(template="threshold", input_signal="FuelLevel", threshold=10, direction="below",
         output_signal="TT_LowFuel", expected_value=1),
    spec(template="threshold", input_signal="VehicleSpeed", threshold=20, direction="above",
         output_signal="TT_Belt", expected_value=1),
    spec(template="event_response", input_signal="IGN", initial_value=0, input_value=1,
         output_signal="TT_Brake", expected_value=1, hold_ms=2000),
    spec(template="timeout", message="Warnings", timeout_ms=500, output_signal="TT_Brake",
         expected_value=1),
    spec(template="periodic_tx", message="ClusterStatus", period_ms=100),
    spec(template="event_response", input_signal="IGN", initial_value=0, input_value=1,
         output_signal="ClusterState", expected_value=1, max_latency_ms=1500),
    spec(template="tracking", input_signal="VehicleSpeed", output_signal="DisplayedSpeed",
         track_low_factor=1, track_low_offset=0, track_high_factor=1.1, track_high_offset=4),
])
def test_generated_cases_pass_reference_and_catch_every_fault(db, s):
    cases = generate_cases(s, {"id": "R", "text": "t", "quote": "q"}, db)
    fc = fault_check(s, cases, db)
    assert fc["reference_passes"] is True
    assert fc["detected"] == fc["total"] > 0


def test_open_values_are_flagged_not_hidden(db):
    s = spec(template="threshold", input_signal="FuelLevel", threshold=10, direction="below",
             output_signal="TT_LowFuel", expected_value=1)
    cases = generate_cases(s, {"id": "R", "text": "t", "quote": "q"}, db)
    assert all("reaction time not stated" in c["open_values"][0] for c in cases)
    assert {c["kind"] for c in cases} == {"boundary", "range"}


def test_forge_pipeline_end_to_end(cfg, audit, tmp_path):
    sift_run = _approved_run(cfg, audit, tmp_path)
    s1 = {"specs": [
        spec(req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
             period_ms=100, value_sources=[{"param": "period_ms", "quote": "every 100 ms"}]),
        spec(req_id="REQ-GAUGE-002", template="not_automatable",
             manual_test_idea="Read the gauge in daylight."),
        spec(req_id="REQ-GAUGE-003", template="threshold", input_signal="FuelLevel",
             threshold=12, direction="below", output_signal="TT_LowFuel", expected_value=1),
        spec(req_id="REQ-NOPE-009", template="not_automatable", manual_test_idea="x")]}
    s2 = {"specs": [spec(req_id="REQ-AUD-001", template="event_response",
                         input_signal="DoorOpen", initial_value=0, input_value=1,
                         output_signal="ChimeActive", expected_value=1)]}
    FakeProvider.queue[:] = [json.dumps(s1), "not json", "not json", "not json"]
    rep = forge.start(cfg, audit, sift_run, DBC, workers=1)
    run = rep.run_id
    assert list(rep.failed) == ["2"]  # section 2's call failed three times
    assert [r["payload"]["text"] for r in forge.without_spec(audit, run)] == [
        "The chime shall sound when a door is open."]
    FakeProvider.queue[:] = [json.dumps(s2)]
    assert forge.resume(cfg, audit, run, workers=1).done == ["REQ-AUD-001"]
    assert forge.without_spec(audit, run) == []
    specs = {s["payload"]["req_id"]: s for s in audit.list_items(run, "test_spec")}
    assert set(specs) == {"REQ-GAUGE-001", "REQ-GAUGE-002", "REQ-GAUGE-003", "REQ-AUD-001"}
    assert specs["REQ-GAUGE-003"]["payload"]["problems"]  # invented threshold caught
    for s in specs.values():
        audit.decide(s["item_id"], "approved", "Tom")
    calls = len(FakeProvider.calls)
    res = forge.generate(audit, run, "Tom")
    assert len(FakeProvider.calls) == calls  # generation is code only
    assert [x["spec"] for x in res["skipped"]] == [specs["REQ-GAUGE-003"]["item_id"]]
    cases = audit.list_items(run, "test_case")
    assert {c["payload"]["requirement_id"] for c in cases} == {
        "REQ-GAUGE-001", "REQ-GAUGE-002", "REQ-AUD-001"}
    assert forge.generate(audit, run, "Tom")["cases"] == 0  # no duplicates on re-run
    faults = forge.fault_results(audit, run)
    assert all(f["reference_passes"] in (True, None) for f in faults.values())
    out = forge.export(audit, run, "Tom", out_dir=tmp_path / "out")
    assert out["lint"] == []
    compile(Path(out["files"]["pytest"]).read_text(encoding="utf-8"), "t.py", "exec")
    # fault-kill score: every injected fault caught, recorded in the exports
    from openpyxl import load_workbook

    from harness.anvil.score import kill_score
    ks = kill_score(audit, run)
    assert ks["faults"] > 0 and ks["detected"] == ks["faults"] and ks["score"] == 1.0
    assert ks["surviving"] == [] and ks["reference_failed"] == []
    assert set(ks["by_template"]) == {"periodic_tx", "event_response"}
    data = json.loads(Path(out["files"]["json"]).read_text(encoding="utf-8"))
    assert data["fault_score"]["detected"] == ks["detected"]
    sheet = load_workbook(out["files"]["xlsx"])["Fault check"]
    assert sheet.cell(2, 2).value == ks["detected"]
    assert "NOT DETECTED" not in [c.value for c in sheet["D"]]


def test_kill_score_lists_surviving_faults_and_idle_cases(cfg, audit):
    run = audit.start_run("forge")
    audit.add_item(run, "test_spec", {"req_id": "R1", "template": "threshold"},
                   created_by="t", item_id=f"S1@{run}")
    for cid in ("C1", "C2"):
        audit.add_item(run, "test_case", {"case_id": cid, "spec_item": f"S1@{run}",
                                          "spec_version": 1, "kind": "boundary"},
                       created_by="t", item_id=f"{cid}@{run}")
    audit.log_event("code", "fault_checked", run_id=run, object_id=f"S1@{run}",
                    object_version=1, detail={
                        "reference_passes": True, "detected": 1, "total": 2, "faults": {
                            "late": {"fault": "late", "detected_by": ["C1"]},
                            "inverted": {"fault": "wrong side", "detected_by": []}}})
    from harness.anvil.score import kill_score
    ks = kill_score(audit, run)
    assert ks["score"] == 0.5 and ks["cases_detecting_nothing"] == ["C2"]
    assert ks["surviving"] == [{"requirement_id": "R1", "spec_item": f"S1@{run}",
                                "fault": "inverted", "label": "wrong side"}]


def test_tracking_validation(db):
    t = spec(template="tracking", input_signal="VehicleSpeed", output_signal="DisplayedSpeed",
             track_high_factor=1.1, track_high_offset=4)
    text = "shall not exceed the actual vehicle speed by more than 10 percent plus 4 km/h."
    assert validate(t, text, db) == []
    bad = validate({**t, "track_high_factor": 1.2, "track_high_offset": 5}, text, db)
    assert len(bad) == 2
    assert validate({**t, "track_high_factor": None, "track_high_offset": None}, text, db) == [
        "tracking needs a lower or an upper bound"]


def test_repropose_only_touches_rejected_or_failing_specs(cfg, audit, tmp_path):
    sift_run = _approved_run(cfg, audit, tmp_path)
    wrong = spec(req_id="REQ-GAUGE-001", template="event_response", input_signal="VehicleSpeed",
                 output_signal="DisplayedSpeed")
    good = spec(req_id="REQ-GAUGE-002", template="not_automatable", manual_test_idea="Look.")
    FakeProvider.queue[:] = [json.dumps({"specs": [wrong, good]}), json.dumps({"specs": []})]
    run = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    items = {s["payload"]["req_id"]: s["item_id"] for s in audit.list_items(run, "test_spec")}
    audit.decide(items["REQ-GAUGE-002"], "approved", "Tom")
    assert [s["item_id"] for s in forge.repropose_candidates(audit, run)] == [
        items["REQ-GAUGE-001"]]
    fixed = spec(req_id="REQ-GAUGE-001", template="periodic_tx", message="ClusterStatus",
                 period_ms=100)
    FakeProvider.queue[:] = [json.dumps({"specs": [fixed]})]
    assert forge.repropose(cfg, audit, run).done == ["REQ-GAUGE-001"]
    new = audit.get_item(items["REQ-GAUGE-001"])
    assert new["version"] == 2 and new["payload"]["problems"] == []
    assert audit.status(items["REQ-GAUGE-001"]) == "edited"   # open for a person
    assert audit.status(items["REQ-GAUGE-002"]) == "approved"  # untouched


def test_spec_schema_stays_within_api_union_limit():
    """The API refuses structured-output schemas with more than 16 optional (union) fields."""
    import json as _json

    from harness.models.schema_tools import to_strict_schema
    from harness.schemas.forge import SpecBatch

    text = _json.dumps(to_strict_schema(SpecBatch))
    item = to_strict_schema(SpecBatch)["properties"]["specs"]["items"]["properties"]
    unions = [k for k, v in item.items() if "anyOf" in v or isinstance(v.get("type"), list)]
    assert len(unions) <= 16, unions
    assert "track_bounds" in text


def test_flatten_track_bounds():
    from harness.schemas.forge import flatten

    f = flatten({"track_bounds": [{"side": "upper", "factor": 1.1, "offset": 4}]})
    assert (f["track_high_factor"], f["track_high_offset"], f["track_low_factor"]) == (1.1, 4,
                                                                                      None)


def test_exported_tests_run_on_the_simulated_bench(cfg, audit, tmp_path):
    """The exported pytest module executes: all pass on the correct simulation, and a
    fault makes the tests meant to catch it fail."""
    import os
    import subprocess
    import sys

    sift_run = _approved_run(cfg, audit, tmp_path)
    s1 = {"specs": [spec(req_id="REQ-GAUGE-001", template="periodic_tx",
                         message="ClusterStatus", period_ms=100),
                    spec(req_id="REQ-GAUGE-002", template="not_automatable",
                         manual_test_idea="Read it.")]}
    s2 = {"specs": [spec(req_id="REQ-AUD-001", template="event_response",
                         input_signal="DoorOpen", initial_value=0, input_value=1,
                         output_signal="ChimeActive", expected_value=1)]}
    FakeProvider.queue[:] = [json.dumps(s1), json.dumps(s2)]
    run = forge.start(cfg, audit, sift_run, DBC, workers=1).run_id
    for s in audit.list_items(run, "test_spec"):
        audit.decide(s["item_id"], "approved", "Tom")
    forge.generate(audit, run, "Tom")
    out = tmp_path / "export"
    forge.export(audit, run, "Tom", out_dir=out)

    def pytest_run(fault=None):
        env = {**os.environ, "ZYN_SIM_FAULT": fault or ""}
        return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               str(out)], capture_output=True, text=True, env=env, check=False)

    ok = pytest_run()
    assert ok.returncode == 0, ok.stdout[-2000:]
    assert "passed" in ok.stdout and "skipped" in ok.stdout  # manual case is skipped
    bad = pytest_run("no_response")
    assert bad.returncode == 1 and "failed" in bad.stdout
    slow = pytest_run("slow")
    assert slow.returncode == 1
