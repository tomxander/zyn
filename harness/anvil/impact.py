"""Which generated tests a requirement change touches, and keeping them honest.

A Sift Delta run compares a new spec revision with an approved Sift run. Every Anvil run
built from that Sift run has test cases tracing to its requirements. From the Delta entries:
- changed or removed requirement: its cases are stale (marked by a person, one action);
- moved requirement: same words elsewhere, cases stay valid (noted);
- new text: no requirement and no test yet (listed as a coverage gap).
Updating a requirement is a new version of the Sift requirement, approved by a person.
A spec whose requirement changed is proposed again and regenerated; old cases stay in the
record as stale or superseded and are left out of the export.
"""

from __future__ import annotations

from harness.audit.store import AuditStore
from harness.sift import checks
from harness.sift.delta import key, strip_number

STALE_KINDS = ("changed", "removed")


def forge_runs_for(audit: AuditStore, sift_run: str) -> list[str]:
    return [r["run_id"] for r in audit.list_runs() if r["workflow"] == "forge"
            and (audit.get_item(f"FORGE-{r['run_id']}") or {}).get("payload", {})
            .get("sift_run") == sift_run]


def impact(audit: AuditStore, delta_run: str) -> dict:
    meta = audit.get_item(f"DELTA-{delta_run}")["payload"]
    base = meta.get("base_run")
    entries = audit.list_items(delta_run, "delta_entry")
    by_req = {e["payload"]["requirement_item"]: e for e in entries
              if e["payload"].get("requirement_item")}
    rows = []
    forge_runs = forge_runs_for(audit, base) if base else []
    for fr in forge_runs:
        cases = audit.list_items(fr, "test_case")
        for s in audit.list_items(fr, "test_spec"):
            e = by_req.get(s["payload"]["requirement_item"])
            if not e:
                continue
            own = [c for c in cases if c["payload"]["spec_item"] == s["item_id"]]
            rows.append({"forge_run": fr, "spec_item": s["item_id"],
                         "requirement_id": s["payload"]["req_id"],
                         "requirement_item": s["payload"]["requirement_item"],
                         "delta_item": e["item_id"], "kind": e["payload"]["kind"],
                         "cases": [c["item_id"] for c in own],
                         "stale_cases": [c["item_id"] for c in own]
                         if e["payload"]["kind"] in STALE_KINDS else []})
    return {"base_run": base, "forge_runs": forge_runs, "rows": rows,
            "new_text": [e for e in entries if e["payload"]["kind"] == "new_text"]}


def marked_stale(audit: AuditStore, case_item: str) -> list[dict]:
    return [e["detail"] for e in audit.events(object_id=case_item)
            if e["action"] == "case_stale" and e["detail"]]


def mark_stale(audit: AuditStore, delta_run: str, actor: str) -> int:
    """A named person marks every case behind a changed or removed requirement as stale."""
    n = 0
    for row in impact(audit, delta_run)["rows"]:
        for cid in row["stale_cases"]:
            if any(d.get("delta_run") == delta_run for d in marked_stale(audit, cid)):
                continue
            audit.log_event(actor, "case_stale", run_id=row["forge_run"],
                            object_type="test_case", object_id=cid,
                            detail={"delta_run": delta_run, "reason": row["kind"],
                                    "requirement_id": row["requirement_id"],
                                    "delta_item": row["delta_item"]})
            n += 1
    return n


def proposed_requirement_text(entry: dict, requirement: dict) -> str | None:
    """The new source sentence, when the approved requirement repeated the old source word for
    word. Otherwise None: rewording a rewritten requirement is for a person to do."""
    if entry["kind"] != "changed":
        return None
    if key(requirement["payload"].get("text", "")) == key(entry["old_text"]):
        return strip_number(entry["new_text"])
    return None


def update_requirement(audit: AuditStore, requirement_item: str, text: str, entry: dict,
                       actor: str, delta_run: str) -> int:
    """New version of the Sift requirement after a spec change; open until a person approves."""
    cur = audit.get_item(requirement_item)
    p = dict(cur["payload"])
    quote = strip_number(entry["new_text"]) if entry.get("new_text") else p.get("source_quote", "")
    p.update({"text": text, "source_quote": quote,
              "section_number": entry.get("new_section") or p.get("section_number"),
              "modal_changed": checks.modal_changed(quote, text),
              "weak_words_found": checks.weak_words(quote),
              "delta_run": delta_run})
    p["weak_word_unflagged"] = bool(p["weak_words_found"]) and "weak_word" not in p.get(
        "quality_flags", [])
    return audit.edit_item(requirement_item, p, actor,
                           comment=f"updated from Sift Delta {delta_run}", source="delta")


def requirement_now(audit: AuditStore, spec_payload: dict) -> dict:
    """Latest version and status of the requirement behind a spec."""
    item = audit.get_item(spec_payload["requirement_item"])
    return {"text": item["payload"]["text"], "version": item["version"],
            "status": audit.status(item["item_id"]), "payload": item["payload"]}


def spec_requirement_state(audit: AuditStore, spec_payload: dict) -> str:
    """current | changed (approved new text, propose again) | pending (update awaits
    approval) | dropped (requirement rejected)."""
    req = requirement_now(audit, spec_payload)
    if req["status"] == "rejected":
        return "dropped"
    if key(req["text"]) == key(spec_payload["requirement_text"]):
        return "current"
    return "changed" if req["status"] == "approved" else "pending"


def case_state(audit: AuditStore, case: dict, spec: dict) -> str:
    """current | superseded (the spec has a newer version) | stale (requirement changed or
    marked stale from a Delta)."""
    if case["payload"].get("spec_version", 1) != spec["version"]:
        return "superseded"
    if marked_stale(audit, case["item_id"]):
        return "stale"
    if spec_requirement_state(audit, spec["payload"]) != "current":
        return "stale"
    return "current"
