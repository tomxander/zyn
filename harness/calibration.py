"""How often people agreed with each kind of finding, measured from their own decisions.

For every Sift Review finding a named person confirmed or dismissed, in any run, count it by
source (code check or AI reviewer), category, and for the AI the model profile. Precision is
confirmed / (confirmed + dismissed). Shown next to new findings of the same kind, so a
reviewer sees "people confirmed 3 of 14 'ambiguous' findings from this model" instead of a
model's confidence. Open findings do not count. Small numbers are labelled as such.
"""

from __future__ import annotations

from collections import defaultdict

from harness.audit.store import AuditStore

MIN_DECIDED = 5  # below this the record is shown as too few to judge


def _key(payload: dict, created_by: str) -> tuple[str, str, str]:
    src = payload.get("source", "?")
    prof = created_by.split(":", 1)[1] if src == "ai" and ":" in created_by else src
    return src, payload.get("category", "?"), prof


def records(audit: AuditStore, exclude_run: str | None = None) -> dict[tuple, dict]:
    """(source, category, profile) -> {confirmed, dismissed, decided, precision}."""
    tally: dict[tuple, dict] = defaultdict(lambda: {"confirmed": 0, "dismissed": 0})
    decided = audit.latest_decisions()
    for f in audit.items_of_type("finding"):
        if f["run_id"] == exclude_run:
            continue
        d = decided.get(f["item_id"])
        if not d:
            continue
        t = tally[_key(f["payload"], f["created_by"])]
        t["confirmed" if d["action"] == "approved" else "dismissed"] += 1
    out = {}
    for k, t in tally.items():
        n = t["confirmed"] + t["dismissed"]
        out[k] = {**t, "decided": n, "precision": round(t["confirmed"] / n, 2) if n else None,
                  "enough": n >= MIN_DECIDED}
    return out


def record_for(recs: dict[tuple, dict], payload: dict, created_by: str) -> dict | None:
    return recs.get(_key(payload, created_by))


def label(rec: dict | None, who: str) -> str:
    if not rec or not rec["decided"]:
        return f"No earlier decisions on this kind of finding from the {who}."
    s = (f"People confirmed {rec['confirmed']} of {rec['decided']} earlier findings of this "
         f"kind from the {who}")
    return s + (f" ({rec['precision']:.0%})." if rec["enough"] else ", too few to judge.")


def table(audit: AuditStore) -> list[dict]:
    return sorted(({"source": k[0], "category": k[1], "profile": k[2], **v}
                   for k, v in records(audit).items()),
                  key=lambda r: (r["source"], r["profile"], -r["decided"], r["category"]))
