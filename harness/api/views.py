"""Read side of the API: one view model per run, built from the audit store.

All checks and rules the screen shows are computed here, in Python, so the web screen only
displays and sends decisions. Logic moved over from the Streamlit screen unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness.audit.store import AuditStore
from harness.config import HarnessConfig
from harness.sift import check as sift_check
from harness.sift import checks, pipeline
from harness.taxonomy import load_taxonomy

WORKFLOW_NAME = {"sift": "Sift", "sift-check": "Sift Review",
                 "sift-delta": "Sift Delta", "forge": "Anvil", "smoke": "Smoke test",
                 "test-check": "Anvil Review"}


# Mappings the model rated at least this high may be approved together, after a person reads them.
BULK_MAPPING_RATING = 0.9


def tool_name(workflow: str) -> str:
    """The name the screen shows for a workflow. Benchmark runs (eval-*) are Assay."""
    if workflow.startswith("eval-"):
        return "Assay"
    if workflow in pipeline.LEGACY_WORKFLOWS:
        return "Sift"
    return WORKFLOW_NAME.get(workflow, workflow.replace("-", " ").capitalize())
SIFT = {pipeline.WORKFLOW, *pipeline.LEGACY_WORKFLOWS}

LABELS_REASON = "Text is correct as written; the objection is only about type, flags or ASIL hint"
REASONS = [
    LABELS_REASON,
    "Text is faithful to the source; the source wording is binding as written",
    "Checked the AI's point against the source and disagree",
]
DISMISS_REASONS = ["Not a problem in this context", "Defined elsewhere in the project",
                   "Known and accepted", "Duplicate of another finding"]


def run_list(audit: AuditStore) -> list[dict]:
    out = []
    for r in audit.list_runs():
        note = (r.get("note") or "").split(" sha256=")[0]
        out.append({"run_id": r["run_id"], "workflow": r["workflow"],
                    "tool": tool_name(r["workflow"]),
                    "note": note, "created": r["run_id"][:15]})
    return out


def doc_order(item: dict) -> tuple:
    p = item["payload"]
    num = p.get("section_number", p.get("number")) or ""
    parts = tuple(int(x) for x in num.split(".") if x.isdigit()) if num else (-1,)
    tail = item["item_id"].split("@")[0].rsplit("-", 1)[-1]
    return parts, int(tail) if tail.isdigit() else 0


# ---- shared decision state ------------------------------------------------------------

def decision_state(
    audit: AuditStore,
    item: dict,
    scope: str | None = None,
    block_approve: str | None = None,
    block_decide: str | None = None,
) -> dict:
    """What the decision buttons may do for this item, and which reasons to offer."""
    iid = item["item_id"]
    status = audit.status(iid)
    out: dict[str, Any] = {
        "status": status,
        "block_approve": block_approve,
        "block_decide": block_decide,
        "needs_reason": False,
        "reasons": [],
        "earlier": None,
    }
    if block_decide or block_approve or status == "approved":
        return out
    if audit.needs_override_reason(iid):
        options = REASONS if scope != "text" else REASONS[1:]
        prior = (
            pipeline.earlier_override(audit, item)
            if item["item_type"] == "requirement"
            else None
        )
        if prior and prior.get("reason"):
            earlier = f"As before (run {prior['run_id']}): {prior['reason']}"
            options = [earlier, *[o for o in options if o != prior["reason"]]]
            out["earlier"] = {"by": prior["by"], "run_id": prior["run_id"]}
        out.update(needs_reason=True, reasons=options)
    return out


def _section_text(audit: AuditStore, item: dict) -> str:
    sec = audit.get_item(f"{item['run_id']}:{item['payload'].get('section_id')}")
    return sec["payload"]["text"] if sec else item["payload"].get("source_quote", "")


def support_states(audit: AuditStore, item: dict, review: dict | None) -> list[dict]:
    p = item["payload"]
    states = []
    if "grounded" in p:
        states.append(("Quote located in source" if p["grounded"] else "Quote NOT in source",
                       bool(p["grounded"])))
    if p.get("source_quote"):
        changed = checks.modal_changed(p["source_quote"], p.get("text", ""))
        states.append(("Modal verb kept" if not changed else "Modal verb changed", not changed))
        added = checks.new_numbers(p.get("text", ""), _section_text(audit, item))
        if not p.get("clarification"):
            states.append(("Values from source only" if not added
                           else "Adds values: " + ", ".join(added), not added))
    if p.get("weak_words_found") is not None:
        ok = not p.get("weak_word_unflagged")
        states.append(("Vague words flagged" if ok else "Vague words unflagged", ok))
    tbd = pipeline.open_placeholders(p)
    if tbd:
        states.append((f"{len(tbd)} placeholder(s) open", False))
    if review and review.get("detail"):
        v = review["detail"]["verdict"]
        states.append(("AI reviewer accepted" if v == "accept" else f"AI reviewer: {v}",
                       v == "accept"))
    return [{"label": label, "ok": ok} for label, ok in states]


# ---- Sift requirement and mapping cards --------------------------------------------------

def requirement_card(
    audit: AuditStore, item: dict, rights: Callable[[dict], Any] | None = None
) -> dict:
    from harness.sift.delta import word_diff

    iid, p = item["item_id"], item["payload"]
    review = audit.latest_ai_review(iid)
    d = review["detail"] if review else None
    flags = p.get("quality_flags") or []
    diff = None
    if item["version"] > 1:
        first = audit.get_item(iid, version=1)["payload"].get("text", "")
        if first != p.get("text", ""):
            diff = word_diff(first, p.get("text", ""))
    clar = pipeline.latest_clarification(audit, iid) if flags else None

    new = {**p}
    if d and d.get("suggested_text"):
        new["text"] = d["suggested_text"]
    if d and d.get("suggested_req_type"):
        new["req_type"] = d["suggested_req_type"]
    if d and d.get("suggested_flags") is not None:
        new["quality_flags"] = d["suggested_flags"]
    problems = (
        checks.suggestion_problems(
            d["suggested_text"], p.get("source_quote", ""), _section_text(audit, item)
        )
        if d and d.get("suggested_text") and new["text"] != p.get("text")
        else []
    )
    changes = any(new.get(k) != p.get(k) for k in ("text", "req_type", "quality_flags"))
    can_apply = bool(d) and d["verdict"] == "revise" and changes and not problems
    if item["version"] > 1 and p.get("clarification"):
        own = (
            [f"changes the modal verb from '{checks.modal_of(p['source_quote'])}'"]
            if checks.modal_changed(p.get("source_quote", ""), p.get("text", ""))
            else []
        )
    elif item["version"] > 1:
        own = checks.suggestion_problems(
            p.get("text", ""), p.get("source_quote", ""), _section_text(audit, item)
        )
    else:
        own = []
    states = support_states(audit, item, review)
    block_decide = None
    if rights:
        v = rights(item)
        if not v:
            block_decide = v.reason if hasattr(v, "reason") else str(v)
    return {
        "item_id": iid,
        "display_id": pipeline.display_id(iid),
        "version": item["version"],
        "status": item.get("status") or audit.status(iid),
        "payload": p,
        "diff": diff,
        "checks": states,
        "needs_attention": not all(s["ok"] for s in states),
        "flags": flags,
        "review": (
            {"actor": review["actor"], "on_version": review["object_version"], **d}
            if d
            else None
        ),
        "clarification": {"actor": clar["actor"], **clar["detail"]} if clar else None,
        "open_placeholders": pipeline.open_placeholders(p),
        "suggestion_problems": problems,
        "own_problems": own,
        "can_apply": can_apply,
        "decision": decision_state(
            audit,
            item,
            scope=(d or {}).get("objection_scope"),
            block_decide=block_decide,
        ),
    }


def mapping_card(
    audit: AuditStore, item: dict, rights: Callable[[dict], Any] | None = None
) -> dict:
    block_decide = None
    if rights:
        v = rights(item)
        if not v:
            block_decide = v.reason if hasattr(v, "reason") else str(v)
    return {
        "item_id": item["item_id"],
        "version": item["version"],
        "status": item["status"],
        "payload": item["payload"],
        "decision": decision_state(audit, item, block_decide=block_decide),
    }


def counts(items: list[dict]) -> dict[str, int]:
    return {
        s: sum(1 for i in items if i["status"] == s)
        for s in ("proposed", "edited", "approved", "rejected")
    }


def sift_view(
    audit: AuditStore,
    run_id: str,
    events: list[dict],
    rights: Callable[[dict], Any] | None = None,
) -> dict:
    tax = load_taxonomy()
    doc = audit.get_item(f"DOC-{run_id}")["payload"]
    maps = sorted(audit.list_items(run_id, "section_mapping"), key=doc_order)
    reqs = sorted(audit.list_items(run_id, "requirement"), key=doc_order)
    approved_maps = [
        m
        for m in maps
        if m["status"] == "approved" and m["payload"]["subsystem_id"] != "NONE"
    ]
    extracted = {r["payload"]["section_id"] for r in reqs} | {
        e["detail"]["section_id"]
        for e in events
        if e["action"] == "extracted_none" and e["detail"]
    }
    waiting = [m for m in approved_maps if m["payload"]["section_id"] not in extracted]
    cards = [requirement_card(audit, r, rights=rights) for r in reqs]
    clean = [
        c
        for c in cards
        if c["status"] in ("proposed", "edited") and c["review"] and not c["needs_attention"]
    ]
    missed = [
        {"section": e["detail"]["section_id"], "text": m}
        for e in events
        if e["action"] == "ai_review_missed"
        for m in e["detail"]["missed"]
    ]
    return {
        "doc": {k: doc.get(k) for k in ("title", "filename", "converter", "sha256")},
        "taxonomy": {
            "label": tax.label,
            "subsystems": [{"id": s.id, "name": s.name} for s in tax.subsystems],
        },
        "mappings": [mapping_card(audit, m, rights=rights) for m in maps],
        "mapping_counts": counts(maps),
        "bulk_mappings": [
            m["item_id"]
            for m in maps
            if m["status"] in ("proposed", "edited") and m["payload"]["confidence"] >= BULK_MAPPING_RATING
        ],
        "bulk_mapping_rating": BULK_MAPPING_RATING,
        "approved_sections": len(approved_maps),
        "waiting_sections": len(waiting),
        "requirements": cards,
        "requirement_counts": counts(reqs),
        "bulk_requirements": [c["item_id"] for c in cards if c in clean],
        "clarify_candidates": len(pipeline.clarify_candidates(audit, run_id)),
        "missed": missed,
        "approved_count": sum(1 for r in reqs if r["status"] == "approved"),
    }


def smoke_view(
    audit: AuditStore, run_id: str, rights: Callable[[dict], Any] | None = None
) -> dict:
    reqs = audit.list_items(run_id, "requirement")
    return {
        "requirements": [requirement_card(audit, r, rights=rights) for r in reqs],
        "requirement_counts": counts(reqs),
    }


# ---- Sift Review -------------------------------------------------------------------------

FINDING_STATE = {"proposed": "open", "edited": "open", "approved": "confirmed",
                 "rejected": "dismissed"}


def check_view(
    audit: AuditStore, run_id: str, rights: Callable[[dict], Any] | None = None
) -> dict:
    meta = audit.get_item(f"SET-{run_id}")["payload"]
    reqs_in = sorted(audit.list_items(run_id, "imported_requirement"),
                     key=lambda i: i["payload"]["order"])
    order = {r["payload"]["ext_id"]: r["payload"]["order"] for r in reqs_in}
    finds = sorted(audit.list_items(run_id, "finding"),
                   key=lambda f: (order.get(f["payload"]["req_id"], 10**9), f["item_id"]))
    stab = sift_check.stability(audit, run_id)
    all_b = sift_check.batches(audit, run_id)
    all_w = sift_check.conflict_windows(audit, run_id)
    per: dict[str, list] = {}
    for f in finds:
        per.setdefault(f["payload"]["req_id"], []).append(f)
    from harness import calibration

    recs = calibration.records(audit)
    findings = []
    for f in finds:
        p = f["payload"]
        also = sift_check.corroborations(audit, f["item_id"])
        rec = calibration.record_for(recs, p, f["created_by"])
        who = "code check" if p.get("source") == "code" else "AI reviewer"
        k, n = stab.get(f["item_id"], (0, 0))
        block_decide = None
        if rights:
            v = rights(f)
            if not v:
                block_decide = v.reason if hasattr(v, "reason") else str(v)
        findings.append({
            "item_id": f["item_id"], "status": f["status"], "state": FINDING_STATE[f["status"]],
            "block_decide": block_decide,
            "decision": decision_state(audit, f, block_decide=block_decide),
            "payload": p, "created_by": f["created_by"],
            "stability": {"seen": k, "passes": n} if n > 1 else None,
            "record": {**(rec or {"confirmed": 0, "dismissed": 0, "decided": 0,
                                  "precision": None, "enough": False}),
                       "label": calibration.label(rec, who)},
            "also": sorted({"code check" if c["source"] == "code" else "AI reviewer"
                            for c in also}),
        })
    passes = sift_check.passes_done(audit, run_id)
    tests = meta.get("kind") == "tests"
    return {
        "meta": meta,
        # The AI reviewer's prompt is written for requirements; tests get code checks only.
        "ai_available": not tests,
        "item_label": "Tests" if tests else "Requirements",
        "findings": findings,
        "requirements": [{
            "id": r["payload"]["ext_id"], "heading": r["payload"]["heading"],
            "text": r["payload"]["text"],
            "findings": sorted({f["payload"]["category"] for f in per.get(r["payload"]["ext_id"], [])}),
            "open": sum(1 for f in per.get(r["payload"]["ext_id"], [])
                        if f["status"] in ("proposed", "edited")),
        } for r in reqs_in],
        "ai": {"batches": len(all_b), "batches_left": len(all_b) - len(sift_check.ai_done(audit, run_id)),
               "conflicts": len(all_w),
               "conflicts_left": len(all_w) - len(sift_check.conflicts_done(audit, run_id)),
               "passes": len(passes), "first_pass_done": 1 in passes},
        "carry_over": len(sift_check.carry_over_candidates(audit, run_id)),
        "dismiss_reasons": DISMISS_REASONS,
        "answer_key_default": ("data/synthetic/icx100_answer_key.json"
                               if meta["filename"].startswith("icx100") else ""),
    }


# ---- Anvil -------------------------------------------------------------------------------

SPEC_FIELDS = ["input_signal", "initial_value", "input_value", "threshold", "direction",
               "output_signal", "expected_value", "max_latency_ms", "hold_ms", "message",
               "timeout_ms", "period_ms"]
TRACK_FIELDS = ["track_low_factor", "track_low_offset", "track_high_factor",
                "track_high_offset"]
NUM_FIELDS = ["initial_value", "input_value", "threshold", "expected_value",
              "max_latency_ms", "hold_ms", "timeout_ms", "period_ms", *TRACK_FIELDS]


def forge_view(
    audit: AuditStore, run_id: str, rights: Callable[[dict], Any] | None = None
) -> dict:
    from harness.anvil import impact as fimpact
    from harness.anvil import pipeline as forge
    from harness.anvil.dbc import load_dbc
    from harness.anvil.formal import run_check as formal_check
    from harness.anvil.formal import statement
    from harness.anvil.score import kill_score
    from harness.schemas.forge import Template

    meta = audit.get_item(f"FORGE-{run_id}")["payload"]
    db = load_dbc(meta["dbc_path"])
    specs = audit.list_items(run_id, "test_spec")
    cases = audit.list_items(run_id, "test_case")
    faults = forge.fault_results(audit, run_id)
    made = {(c["payload"]["spec_item"], c["payload"].get("spec_version", 1)) for c in cases}
    spec_cards = []
    for s in specs:
        p = s["payload"]
        rstate = fimpact.spec_requirement_state(audit, p)
        block_decide = None
        if rights:
            v = rights(s)
            if not v:
                block_decide = v.reason if hasattr(v, "reason") else str(v)
        spec_cards.append({
            "item_id": s["item_id"], "version": s["version"], "status": s["status"],
            "payload": p,
            "params": {k: p[k] for k in SPEC_FIELDS + TRACK_FIELDS if p.get(k) not in (None, "")},
            "requirement_state": rstate,
            "statement": statement(p),
            "requirement_now": (fimpact.requirement_now(audit, p)["text"]
                                if rstate != "current" else None),
            "decision": decision_state(audit, s, block_approve=(
                "Fails the code checks: edit the spec until they pass, or reject it."
                if p["problems"] else None), block_decide=block_decide),
        })
    formal = formal_check(audit, run_id)
    for card in spec_cards:
        card["formal_issues"] = [i["explanation"] for i in formal["issues"]
                                 if card["payload"]["req_id"] in i["requirements"]]
    ready = [s for s in specs if s["status"] == "approved" and not s["payload"]["problems"]
             and (s["item_id"], s["version"]) not in made
             and fimpact.spec_requirement_state(audit, s["payload"]) == "current"]
    spec_by_id = {s["item_id"]: s for s in specs}
    groups: dict[str, dict] = {}
    for c in cases:
        cp = c["payload"]
        g = groups.setdefault(cp["spec_item"], {"spec_item": cp["spec_item"],
                                                "requirement_id": cp["requirement_id"],
                                                "template": cp["template"], "cases": []})
        g["cases"].append({**cp, "state": fimpact.case_state(audit, c,
                                                             spec_by_id[cp["spec_item"]])})
    for sid, g in groups.items():
        g["faults"] = faults.get(sid, {})
    return {
        "meta": meta,
        "specs": spec_cards, "spec_counts": counts(specs),
        "templates": sorted({s["payload"]["template"] for s in specs}),
        "missing_specs": [pipeline.display_id(r["item_id"])
                          for r in forge.without_spec(audit, run_id)],
        "repropose": len(forge.repropose_candidates(audit, run_id)),
        "ready": len(ready),
        "case_groups": list(groups.values()), "case_count": len(cases),
        "faults_total": sum(f["total"] for f in faults.values()),
        "faults_detected": sum(f["detected"] for f in faults.values()),
        "fault_score": kill_score(audit, run_id),
        "formal": formal,
        "stale": sum(1 for g in groups.values() for c in g["cases"] if c["state"] != "current"),
        "edit_options": {
            "templates": [t.value for t in Template],
            "inputs": sorted(n for n, s in db.signals.items() if s.cluster_receives),
            "outputs": sorted(n for n, s in db.signals.items() if not s.cluster_receives),
            "messages": sorted(db.messages), "numbers": NUM_FIELDS,
        },
    }


# ---- Sift Delta --------------------------------------------------------------------------

DELTA_STATE = {"proposed": "open", "edited": "open", "approved": "needs action",
               "rejected": "no action"}
DELTA_LABEL = {"changed": "Source changed", "moved": "Moved to another section",
               "removed": "Removed from source", "new_text": "New text, not yet extracted",
               "added": "Added"}


def delta_view(
    audit: AuditStore, run_id: str, rights: Callable[[dict], Any] | None = None
) -> dict:
    from harness.anvil import impact as fimpact
    from harness.sift import delta as sift_delta

    meta = audit.get_item(f"DELTA-{run_id}")["payload"]
    entries = audit.list_items(run_id, "delta_entry")
    out_entries = [{"item_id": e["item_id"], "status": e["status"],
                    "state": DELTA_STATE[e["status"]], "payload": e["payload"],
                    "label": DELTA_LABEL.get(e["payload"]["kind"], e["payload"]["kind"]),
                    "summary": sift_delta.summary(e["payload"])} for e in entries]
    impact = None
    if meta.get("mode") == "spec":
        imp = fimpact.impact(audit, run_id)
        updates = []
        for e in entries:
            ep = e["payload"]
            if ep["kind"] != "changed" or not ep.get("requirement_item"):
                continue
            req = audit.get_item(ep["requirement_item"])
            from_here = req["payload"].get("delta_run") == run_id
            block_decide = None
            if rights and from_here:
                v = rights(req)
                if not v:
                    block_decide = v.reason if hasattr(v, "reason") else str(v)
            updates.append({
                "entry_id": e["item_id"], "requirement_id": ep["requirement_id"],
                "requirement_item": req["item_id"], "version": req["version"],
                "status": audit.status(req["item_id"]), "diff": ep["diff"],
                "current_text": req["payload"]["text"], "updated_here": from_here,
                "proposal": None if from_here else fimpact.proposed_requirement_text(ep, req),
                "decision": decision_state(audit, req, block_decide=block_decide) if from_here else None,
            })
        impact = {"forge_runs": imp["forge_runs"], "rows": [
            {"requirement_id": r["requirement_id"], "kind": r["kind"],
             "forge_run": r["forge_run"], "cases": len(r["cases"]),
             "stale": len(r["stale_cases"])} for r in imp["rows"]],
            "stale_total": sum(len(r["stale_cases"]) for r in imp["rows"]),
            "new_text": [e["payload"]["new_text"] for e in imp["new_text"]],
            "updates": updates}
    return {"meta": meta, "entries": out_entries, "labels": DELTA_LABEL, "impact": impact,
            "answer_key_default": ("data/synthetic/icx100_rev2_changes.json"
                                   if "icx100" in meta["new_file"] else "")}


# ---- audit -------------------------------------------------------------------------------

AUDIT_COLS = ("event_id", "ts", "actor", "action", "object_id", "object_version",
              "model_served", "tokens_in", "tokens_out", "latency_ms", "attempt")


def knowledge_view(cfg: HarnessConfig) -> dict:
    """What the sidebar says about the project knowledge file."""
    k = cfg.knowledge()
    if k is not None:
        return {"state": "in_use", "path": k.path, "lines": k.lines, "sha": k.sha256[:8]}
    if cfg.knowledge_file:
        return {"state": "empty", "path": cfg.knowledge_file}
    return {"state": "off"}


def knowledge_used(events: list[dict]) -> list[dict]:
    """Which versions of the knowledge file this run's model answers were given."""
    calls = [e for e in events if e["action"] in ("generated", "replayed")]
    seen: dict[str, dict] = {}
    for e in calls:
        k = (e.get("detail") or {}).get("knowledge")
        if k:
            row = seen.setdefault(k["sha256"], {"path": k["path"], "sha": k["sha256"][:8],
                                                "lines": k["lines"], "calls": 0})
            row["calls"] += 1
    return [{**r, "of_calls": len(calls)} for r in seen.values()]


def audit_view(audit: AuditStore, cfg: HarnessConfig, run_id: str) -> dict:
    from harness.metrics import run_metrics

    events = audit.events(run_id=run_id)
    ev_list = []
    for e in events:
        row = {k: e.get(k) for k in AUDIT_COLS}
        # Runs recorded before a rename keep their old code actor in the log; the screen shows
        # today's name (the stored record is unchanged).
        old = (row.get("actor") or "").split(":", 1)
        if len(old) == 2 and old[0] == "code" and old[1] in pipeline.LEGACY_WORKFLOWS:
            row["actor"] = pipeline.CODE_ACTOR
        if cfg.is_team():
            actor = row.get("actor") or ""
            actor_id = e.get("actor_id")
            if (
                not actor_id
                and actor
                and actor.lower() not in {"model", "ai"}
                and not actor.startswith("ai-")
            ):
                row["actor"] = f"{actor} (name typed, not signed in)"
        ev_list.append(row)
    return {
        "metrics": run_metrics(audit, run_id, cfg),
        "knowledge": knowledge_used(events),
        "events": ev_list,
    }


READS = {"list_runs", "list_items", "items_of_type", "events", "status", "get_item",
         "latest_ai_review", "latest_decision", "latest_decisions", "needs_override_reason",
         "approved_items"}


class ReadCache:
    """Wraps the audit store for one view build: each read runs once per argument set.
    The store opens a connection per call and checks status per item, so a 400-finding
    run otherwise makes thousands of queries. Writes are not allowed through it."""

    def __init__(self, audit: AuditStore):
        self._audit, self._memo = audit, {}

    def __getattr__(self, name):
        fn = getattr(self._audit, name)
        if name not in READS:
            raise AttributeError(f"{name} is not a read; views must not write")

        def cached(*args, **kwargs):
            if name == "events" and not args and set(kwargs) == {"object_id"}:
                # one query for every object's events instead of one per object
                return [e for e in self.events() if e.get("object_id") == kwargs["object_id"]]
            key = (name, args, tuple(sorted(kwargs.items())))
            if key not in self._memo:
                self._memo[key] = fn(*args, **kwargs)
            return self._memo[key]
        return cached


def run_view(
    audit: AuditStore, run_id: str, rights: Callable[[dict], Any] | None = None
) -> dict:
    audit = ReadCache(audit)  # type: ignore[assignment]
    runs = {r["run_id"]: r for r in audit.list_runs()}
    if run_id not in runs:
        raise KeyError(run_id)
    wf = runs[run_id]["workflow"]
    base = {"run_id": run_id, "workflow": wf, "tool": tool_name(wf),
            "note": (runs[run_id].get("note") or "").split(" sha256=")[0]}
    if wf in (sift_check.WORKFLOW, "test-check"):
        return {**base, "kind": "check", **check_view(audit, run_id, rights=rights)}
    if wf == "forge":
        return {**base, "kind": "forge", **forge_view(audit, run_id, rights=rights)}
    if wf == "sift-delta":
        return {**base, "kind": "delta", **delta_view(audit, run_id, rights=rights)}
    if wf in SIFT:
        return {**base, "kind": "sift", **sift_view(audit, run_id, audit.events(run_id=run_id), rights=rights)}
    return {**base, "kind": "smoke", **smoke_view(audit, run_id, rights=rights)}
