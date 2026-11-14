from __future__ import annotations

import json
from pathlib import Path

from harness.models.fake_provider import FakeProvider
from harness.sift import delta, pipeline
from tests.test_sift import _mapping, _req

KEY = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "icx100_rev2_changes.json"

V1 = """# Mini spec

## 1 Fuel
1.1 The gauge shall update every 100 ms. The gauge should be readable.
1.2 The cluster may offer a theme menu.

## 2 Chimes
2.1 The chime shall sound when a door is open.
"""
V2 = """# Mini spec rev 2

## 1 Fuel
1.1 The gauge shall update every 50 ms. The gauge should be readable.
1.3 The cluster shall show the remaining range.

## 2 Chimes
2.2 Placeholder heading text.

## 3 Doors
3.1 The chime shall sound when a door is open.
"""


def _approved_run(cfg, audit, tmp_path):
    spec = tmp_path / "v1.md"
    spec.write_text(V1, encoding="utf-8")
    FakeProvider.queue[:] = [json.dumps({"mappings": [_mapping("S1", "GAUGE"),
                                                      _mapping("S2", "AUD")]})]
    run = pipeline.start(cfg, audit, spec).run_id
    for m in audit.list_items(run, "section_mapping"):
        audit.decide(m["item_id"], "approved", "Tom")
    none = json.dumps({"reviews": [], "missed": []})
    FakeProvider.queue[:] = [
        json.dumps({"requirements": [
            _req("The gauge shall update every 100 ms.", "The gauge shall update every 100 ms.",
                 "shall"),
            _req("The gauge should be readable.", "The gauge should be readable.", "should"),
            _req("The cluster may offer a theme menu.", "1.2 The cluster may offer a theme menu.",
                 "may")]}), none,
        json.dumps({"requirements": [
            _req("The chime shall sound when a door is open.",
                 "2.1 The chime shall sound when a door is open.", "shall")]}), none]
    pipeline.extract(cfg, audit, run, workers=1)
    for r in audit.list_items(run, "requirement"):
        audit.decide(r["item_id"], "approved", "Tom")
    return run


def test_spec_delta_finds_changed_moved_removed_and_new(cfg, audit, tmp_path):
    run = _approved_run(cfg, audit, tmp_path)
    new = tmp_path / "v2.md"
    new.write_text(V2, encoding="utf-8")
    calls = len(FakeProvider.calls)
    d = delta.spec_delta(cfg, audit, run, new).run_id
    assert len(FakeProvider.calls) == calls  # deterministic: no model calls
    got = {(e["payload"]["kind"], e["payload"].get("requirement_id")): e["payload"]
           for e in audit.list_items(d, "delta_entry")}
    changed = got[("changed", "REQ-GAUGE-001")]
    assert changed["facts"]["values_removed"] == ["100"]
    assert changed["facts"]["values_added"] == ["50"]
    assert ["delete", "100"] in changed["diff"] and ["insert", "50"] in changed["diff"]
    assert ("removed", "REQ-GAUGE-003") in got
    assert got[("moved", "REQ-AUD-001")]["new_section"] == "3"
    assert any(k == "new_text" and "remaining range" in p["new_text"] for (k, _), p in got.items())
    meta = audit.get_item(f"DELTA-{d}")["payload"]
    assert meta["unchanged"] == 1  # "should be readable" is untouched
    item = audit.list_items(d, "delta_entry")[0]["item_id"]
    audit.decide(item, "approved", "Tom")
    res = delta.export_delta(audit, d, "Tom", out_dir=tmp_path / "out")
    rows = json.loads(Path(res["files"]["json"]).read_text(encoding="utf-8"))["entries"]
    assert any(r["status"] == "needs action" for r in rows)


def test_set_delta_by_id(cfg, audit, tmp_path):
    (tmp_path / "a.csv").write_text("ID,Requirement\nR1,The lamp shall be lit.\n"
                                    "R2,The chime shall sound within 1 s.\nR3,Old text.\n",
                                    encoding="utf-8")
    (tmp_path / "b.csv").write_text("ID,Requirement\nR1,The lamp shall be lit.\n"
                                    "R2,The chime should sound within 2 s.\nR4,New text.\n",
                                    encoding="utf-8")
    d = delta.set_delta(cfg, audit, tmp_path / "a.csv", tmp_path / "b.csv").run_id
    got = {e["payload"]["requirement_id"]: e["payload"] for e in audit.list_items(d, "delta_entry")}
    assert got["R2"]["kind"] == "changed" and got["R2"]["facts"]["modal_changed"]
    assert got["R3"]["kind"] == "removed" and got["R4"]["kind"] == "added"
    meta = audit.get_item(f"DELTA-{d}")["payload"]
    assert "R1" not in got and meta["unchanged"] == 1
    # a set export carries no approvals, so Delta must not call its requirements approved
    assert meta["base_requirements"] == 3 and "approved_requirements" not in meta


def test_icx100_rev2_key_is_consistent_with_the_documents():
    root = KEY.parents[0]
    v1 = (root / "icx100_srs.md").read_text(encoding="utf-8")
    v2 = (root / "icx100_srs_rev2.md").read_text(encoding="utf-8")
    for c in json.loads(KEY.read_text(encoding="utf-8"))["changes"]:
        if c.get("old"):
            assert c["old"] in v1, c
        if c.get("new"):
            assert c["new"] in v2, c
        if c["kind"] == "removed":
            assert c["old"] not in v2, c
