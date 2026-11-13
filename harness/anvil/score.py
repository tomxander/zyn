"""The fault-kill score: how many injected faults the generated cases catch.

Per run, from the fault checks code already records when it generates cases. Counts only
current case sets (the latest version of each spec that has cases). It measures the tests
against a simulated cluster and a fixed list of faults per template; it says nothing about
faults outside that list or about the real cluster.
"""

from __future__ import annotations

from harness.anvil.simulate import FAULTS
from harness.audit.store import AuditStore


def current_checks(audit: AuditStore, run_id: str) -> dict[str, dict]:
    """spec item -> the fault check of its newest case set."""
    latest: dict[str, dict] = {}
    for e in audit.events(run_id=run_id):
        if e["action"] == "fault_checked" and e["detail"]:
            prev = latest.get(e["object_id"])
            if prev is None or (e["object_version"] or 1) >= prev["_version"]:
                latest[e["object_id"]] = {**e["detail"], "_version": e["object_version"] or 1}
    return latest


def kill_score(audit: AuditStore, run_id: str) -> dict:
    checks = current_checks(audit, run_id)
    specs = {s["item_id"]: s["payload"] for s in audit.list_items(run_id, "test_spec")}
    cases = audit.list_items(run_id, "test_case")
    by_template: dict[str, dict] = {}
    surviving, reference_failed, killers = [], [], set()
    total = detected = 0
    for sid, fc in checks.items():
        if not fc.get("total"):
            continue  # manual or not automatable: nothing was injected
        p = specs.get(sid, {})
        t = by_template.setdefault(p.get("template", "?"), {"specs": 0, "faults": 0,
                                                             "detected": 0})
        t["specs"] += 1
        t["faults"] += fc["total"]
        t["detected"] += fc["detected"]
        total += fc["total"]
        detected += fc["detected"]
        if fc.get("reference_passes") is False:
            reference_failed.append(p.get("req_id", sid))
        for key, f in fc.get("faults", {}).items():
            killers.update(f["detected_by"])
            if not f["detected_by"]:
                surviving.append({"requirement_id": p.get("req_id", sid), "spec_item": sid,
                                  "fault": key, "label": f["fault"]})
    checked_specs = {sid for sid, fc in checks.items() if fc.get("total")}
    idle = sorted(c["payload"]["case_id"] for c in cases
                  if c["payload"]["spec_item"] in checked_specs
                  and c["payload"].get("spec_version", 1) == checks[c["payload"]["spec_item"]][
                      "_version"]
                  and c["payload"]["kind"] != "manual"
                  and c["payload"]["case_id"] not in killers)
    return {
        "faults": total, "detected": detected,
        "score": round(detected / total, 3) if total else None,
        "specs_checked": len(checked_specs),
        "by_template": by_template,
        "surviving": surviving,
        "reference_failed": reference_failed,
        "cases_detecting_nothing": idle,
        "fault_list": {t: list(f) for t, f in FAULTS.items()},
        "note": ("Faults are injected into a simulated cluster built from each spec. The "
                 "score measures the generated tests against this fixed fault list only, "
                 "not the real cluster."),
    }
