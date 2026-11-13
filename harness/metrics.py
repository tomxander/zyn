"""Effort, cost and agreement figures for one run, computed only from the audit log.

These describe what happened in this run. They are not productivity claims: elapsed time
between a model output and a person's decision includes idle time, and nothing here is
compared against doing the work by hand."""

from __future__ import annotations

import statistics
from datetime import datetime

from harness.audit.store import AuditStore
from harness.config import HarnessConfig

DECIDED = ("approved", "rejected")
REVIEWABLE = ("requirement", "section_mapping", "finding", "delta_entry", "test_spec")


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def cost_usd(cfg: HarnessConfig | None, profile: str | None, tin: int, tout: int) -> float | None:
    if cfg is None or not profile or profile not in cfg.profiles:
        return None
    p = cfg.profiles[profile]
    pin, pout = p.setting("price_in"), p.setting("price_out")
    if pin is None or pout is None:
        return 0.0 if p.provider in ("ollama", "fake") else None
    return (tin * float(pin) + tout * float(pout)) / 1_000_000


def model_calls(audit: AuditStore, run_id: str, cfg: HarnessConfig | None = None) -> dict:
    ev = audit.events(run_id=run_id)
    gen = [e for e in ev if e["action"] == "generated"]
    by_task: dict[str, dict] = {}
    total_cost, unknown_cost = 0.0, False
    for e in gen:
        t = by_task.setdefault(e["object_type"] or "?", {"calls": 0, "tokens_in": 0,
                                                         "tokens_out": 0, "seconds": 0.0,
                                                         "cost_usd": 0.0, "models": set()})
        tin, tout = e["tokens_in"] or 0, e["tokens_out"] or 0
        t["calls"] += 1
        t["tokens_in"] += tin
        t["tokens_out"] += tout
        t["seconds"] += (e["latency_ms"] or 0) / 1000
        t["models"].add(e["model_served"] or e["model_requested"] or "?")
        c = cost_usd(cfg, e["model_profile"], tin, tout)
        if c is None:
            unknown_cost = True
        else:
            t["cost_usd"] += c
            total_cost += c
    for t in by_task.values():
        t["models"] = sorted(t["models"])
        t["cost_usd"] = round(t["cost_usd"], 4)
        t["seconds"] = round(t["seconds"], 1)
    return {
        "calls": len(gen),
        "tokens_in": sum(e["tokens_in"] or 0 for e in gen),
        "tokens_out": sum(e["tokens_out"] or 0 for e in gen),
        "model_seconds": round(sum((e["latency_ms"] or 0) for e in gen) / 1000, 1),
        "cost_usd": round(total_cost, 4),
        "cost_complete": not unknown_cost,
        "schema_retries": sum(1 for e in ev if e["action"] == "validation_failed"),
        "failed_calls": sum(1 for e in ev if e["action"] in ("failed", "provider_error")),
        "blocked_offline": sum(1 for e in ev if e["action"] == "blocked_offline"),
        # stored answers reused instead of a model call: no tokens, no cost, no model time
        "replayed": sum(1 for e in ev if e["action"] == "replayed"),
        "by_task": by_task,
    }


def review_effort(audit: AuditStore, run_id: str) -> dict:
    out = {}
    for kind in REVIEWABLE:
        items = audit.list_items(run_id, kind)
        if not items:
            continue
        waits, edited, decided, by_status, people = [], 0, 0, {}, set()
        for it in items:
            by_status[it["status"]] = by_status.get(it["status"], 0) + 1
            evs = audit.events(object_id=it["item_id"])
            decisions = [e for e in evs if e["action"] in DECIDED]
            edits = [e for e in evs if e["action"] == "edited"]
            edited += bool(edits)
            if decisions:
                decided += 1
                people.add(decisions[0]["actor"])
                first = audit.get_item(it["item_id"], version=1)
                waits.append((_ts(decisions[0]["ts"]) - _ts(first["created_at"])).total_seconds())
        out[kind] = {
            "items": len(items), "decided": decided, "open": len(items) - decided,
            "status": by_status, "edited_items": edited,
            "reviewers": sorted(people),
            "median_minutes_to_first_decision": round(statistics.median(waits) / 60, 1)
            if waits else None,
            "carried_over": sum(1 for e in audit.events(run_id=run_id)
                                if e["action"] in DECIDED and e["detail"]
                                and str(e["detail"].get("comment") or "").startswith(
                                    "carried over")) if kind == "finding" else None,
        }
    return out


def ai_agreement(audit: AuditStore, run_id: str) -> dict:
    """How the people deciding treated the AI reviewer's verdicts (Sift extraction runs)
    and the findings (Sift Review runs)."""
    res: dict = {}
    reqs = audit.list_items(run_id, "requirement")
    if reqs:
        tally = {"objection_upheld": 0, "objection_overruled": 0, "accept_confirmed": 0,
                 "accept_overruled": 0, "undecided": 0}
        for r in reqs:
            rv = audit.latest_ai_review(r["item_id"])
            if not rv or not rv["detail"]:
                continue
            verdict = rv["detail"].get("verdict")
            if r["status"] not in DECIDED:
                tally["undecided"] += 1
                continue
            changed = r["version"] > 1
            if verdict == "accept":
                ok = r["status"] == "approved" and not changed
                tally["accept_confirmed" if ok else "accept_overruled"] += 1
            else:
                upheld = r["status"] == "rejected" or changed
                tally["objection_upheld" if upheld else "objection_overruled"] += 1
        res["ai_reviewer_on_requirements"] = tally
    finds = audit.list_items(run_id, "finding")
    if finds:
        per: dict[str, dict] = {}
        for f in finds:
            src = f["payload"]["source"]
            t = per.setdefault(src, {"confirmed": 0, "dismissed": 0, "open": 0})
            t[{"approved": "confirmed", "rejected": "dismissed"}.get(f["status"], "open")] += 1
        for t in per.values():
            d = t["confirmed"] + t["dismissed"]
            t["confirmed_share_of_decided"] = round(t["confirmed"] / d, 2) if d else None
        res["findings_by_source"] = per
    return res


def run_metrics(audit: AuditStore, run_id: str, cfg: HarnessConfig | None = None) -> dict:
    return {"run_id": run_id, "model": model_calls(audit, run_id, cfg),
            "review": review_effort(audit, run_id), "agreement": ai_agreement(audit, run_id)}
