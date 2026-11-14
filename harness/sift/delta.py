"""Sift Delta: what changed between two revisions, and which approved requirements it touches.

Two modes, both deterministic (no model calls):
- spec: an approved Sift run against a new revision of its specification. Each approved
  requirement's source quote is looked up in the new revision: unchanged, moved to another
  section, changed (closest sentence shown as a word diff), or removed. Sentences with a
  modal verb that are new in the revision are listed as new text to extract.
- set: two exports of a requirement set (ReqIF, Excel, CSV), matched by ID: added,
  removed, changed (word diff) or unchanged.
A named person marks each entry "needs action" or "no action".
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig
from harness.sift import checks
from harness.sift.importer import load_requirement_set
from harness.sift.ingest import load_document
from harness.sift.pipeline import StageReport, display_id

WORKFLOW = "sift-delta"
CODE_ACTOR = "code:sift-delta"
MATCH_THRESHOLD = 0.6  # same section: below this similarity the quote counts as removed
CROSS_SECTION_THRESHOLD = 0.8  # another section: a much closer match is needed
_NUM_PREFIX = re.compile(r"^\s*\d+(?:\.\d+)*\s+")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def strip_number(s: str) -> str:
    return _NUM_PREFIX.sub("", s.strip())


def key(s: str) -> str:
    return checks.normalise(strip_number(s))


def sentences(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or set(line) <= set("|-: "):
            continue
        if line.startswith("|"):
            out.append(line)
        else:
            out += [p for p in _SPLIT.split(line) if p.strip()]
    return [strip_number(s) for s in out]


def word_diff(old: str, new: str) -> list[list[str]]:
    """[[op, text], ...] with op in equal/delete/insert, word level."""
    a, b = strip_number(old).split(), strip_number(new).split()
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            ops.append(["equal", " ".join(a[i1:i2])])
        else:
            if i2 > i1:
                ops.append(["delete", " ".join(a[i1:i2])])
            if j2 > j1:
                ops.append(["insert", " ".join(b[j1:j2])])
    return ops


def change_facts(old: str, new: str) -> dict:
    old, new = strip_number(old), strip_number(new)
    num_old = set(checks._NUMBER.findall(old))
    num_new = set(checks._NUMBER.findall(new))
    m_old, m_new = checks.modal_of(old), checks.modal_of(new)
    return {"values_removed": sorted(num_old - num_new), "values_added": sorted(num_new - num_old),
            "modal_old": m_old, "modal_new": m_new, "modal_changed": m_old != m_new,
            "weak_words_old": checks.weak_words(old), "weak_words_new": checks.weak_words(new)}


def _ratio(a: str, b: str) -> float:
    """Word-level similarity; character-level overstates it for short sentences."""
    return difflib.SequenceMatcher(a=key(a).split(), b=key(b).split(),
                                   autojunk=False).ratio()


def _add_entries(audit: AuditStore, run_id: str, entries: list[dict]) -> None:
    for n, e in enumerate(entries, start=1):
        audit.add_item(run_id, "delta_entry", e, created_by=CODE_ACTOR,
                       item_id=f"DLT-{n:04d}@{run_id}")


# ---- spec revision against an approved Sift run ---------------------------------------


def spec_delta(cfg: HarnessConfig, audit: AuditStore, base_run: str,
               new_path: Path | str) -> StageReport:
    base_doc = audit.get_item(f"DOC-{base_run}")
    if base_doc is None:
        raise ValueError(f"{base_run} is not a Sift extraction run.")
    approved = audit.approved_items(base_run, "requirement")
    if not approved:
        raise ValueError(f"Run {base_run} has no approved requirements to compare.")
    new_doc = load_document(new_path)
    old_secs = {s["payload"]["number"]: s["payload"]
                for s in audit.list_items(base_run, "section")}
    old_keys = {key(s) for p in old_secs.values() for s in sentences(p["text"])}
    new_sents = [(s.number, s.heading, sent) for s in new_doc.sections
                 for sent in sentences(s.text)]
    new_by_key: dict[str, list] = {}
    for num, head, sent in new_sents:
        new_by_key.setdefault(key(sent), []).append((num, head))

    run_id = audit.start_run(WORKFLOW, note=f"spec {base_doc['payload']['filename']} -> "
                                            f"{new_doc.filename}")
    entries, used_new, unchanged = [], set(), 0
    for r in sorted(approved, key=lambda i: i["item_id"]):
        p = r["payload"]
        quote, sec = p.get("source_quote", ""), p.get("section_number")
        base = {"requirement_id": display_id(r["item_id"]), "requirement_item": r["item_id"],
                "requirement_text": p.get("text", ""), "old_text": strip_number(quote),
                "old_section": sec}
        # a quote may be a table row or a clause inside a longer sentence
        hits = [(num, head, s) for num, head, s in new_sents
                if key(quote) and key(quote) in key(s)]
        same = [h for h in hits if h[0] == sec]
        if same:
            unchanged += 1
            used_new.add(key(same[0][2]))
            continue
        if hits:
            used_new.add(key(hits[0][2]))
            entries.append({**base, "kind": "moved", "new_text": hits[0][2],
                            "new_section": hits[0][0], "new_heading": hits[0][1],
                            "similarity": 1.0, "diff": [["equal", strip_number(quote)]],
                            "facts": change_facts(quote, hits[0][2])})
            continue
        scored = sorted(((_ratio(quote, s), num, head, s) for num, head, s in new_sents),
                        key=lambda t: t[0], reverse=True)
        here = [t for t in scored if t[1] == sec and t[0] >= MATCH_THRESHOLD]
        far = [t for t in scored if t[1] != sec and t[0] >= CROSS_SECTION_THRESHOLD]
        best = (here or far or scored or [None])[0]
        if best and (here or far):
            used_new.add(key(best[3]))
            entries.append({**base, "kind": "changed", "new_text": best[3],
                            "new_section": best[1], "new_heading": best[2],
                            "similarity": round(min(best[0], 1.0), 2),
                            "diff": word_diff(quote, best[3]),
                            "facts": change_facts(quote, best[3])})
        else:
            entries.append({**base, "kind": "removed", "new_text": "", "new_section": None,
                            "similarity": round(best[0], 2) if best else 0.0,
                            "diff": [["delete", strip_number(quote)]],
                            "facts": change_facts(quote, "")})
    for num, head, sent in new_sents:
        k = key(sent)
        if k in old_keys or k in used_new or not checks.modal_of(sent):
            continue
        used_new.add(k)
        entries.append({"kind": "new_text", "requirement_id": None, "old_text": "",
                        "new_text": sent, "new_section": num, "new_heading": head,
                        "diff": [["insert", sent]], "facts": change_facts("", sent),
                        "note": "New wording with a modal verb: extract it with Sift."})
    meta = {"mode": "spec", "base_run": base_run, "base_file": base_doc["payload"]["filename"],
            "new_file": new_doc.filename, "new_sha256": new_doc.sha256,
            "approved_requirements": len(approved), "unchanged": unchanged,
            "counts": _counts(entries)}
    audit.add_item(run_id, "delta", meta, created_by=CODE_ACTOR, item_id=f"DELTA-{run_id}")
    audit.log_event(CODE_ACTOR, "ingested", run_id=run_id, object_type="delta",
                    input_sha256=new_doc.sha256, detail=meta)
    _add_entries(audit, run_id, entries)
    return StageReport(run_id, [e["kind"] for e in entries], [], {})


# ---- two exports of a requirement set ---------------------------------------------------


def set_delta(cfg: HarnessConfig, audit: AuditStore, old_path: Path | str,
              new_path: Path | str) -> StageReport:
    old, new = load_requirement_set(old_path), load_requirement_set(new_path)
    o = {r.ext_id: r for r in old.requirements}
    n = {r.ext_id: r for r in new.requirements}
    run_id = audit.start_run(WORKFLOW, note=f"set {old.filename} -> {new.filename}")
    entries, unchanged = [], 0
    for rid in [*o, *[i for i in n if i not in o]]:
        a, b = o.get(rid), n.get(rid)
        if a and b and key(a.text) == key(b.text):
            unchanged += 1
            continue
        kind = "changed" if a and b else ("removed" if a else "added")
        old_t, new_t = (a.text if a else ""), (b.text if b else "")
        entries.append({"kind": kind, "requirement_id": rid, "old_text": old_t,
                        "new_text": new_t, "old_section": a.heading if a else None,
                        "new_section": b.heading if b else None,
                        "similarity": round(_ratio(old_t, new_t), 2) if a and b else None,
                        "diff": word_diff(old_t, new_t), "facts": change_facts(old_t, new_t)})
    meta = {"mode": "set", "base_file": old.filename, "new_file": new.filename,
            "base_sha256": old.sha256, "new_sha256": new.sha256, "unchanged": unchanged,
            # A set export carries no approvals: count what the old file holds, not "approved".
            "base_requirements": len(old.requirements), "counts": _counts(entries)}
    audit.add_item(run_id, "delta", meta, created_by=CODE_ACTOR, item_id=f"DELTA-{run_id}")
    audit.log_event(CODE_ACTOR, "ingested", run_id=run_id, object_type="delta",
                    input_sha256=new.sha256, detail=meta)
    _add_entries(audit, run_id, entries)
    return StageReport(run_id, [e["kind"] for e in entries], [], {})


def _counts(entries: list[dict]) -> dict:
    c: dict[str, int] = {}
    for e in entries:
        c[e["kind"]] = c.get(e["kind"], 0) + 1
    return c


# ---- export and scoring -------------------------------------------------------------

COLUMNS = [("kind", "Change"), ("requirement_id", "Requirement"), ("old_section", "Old section"),
           ("new_section", "New section"), ("old_text", "Old text"), ("new_text", "New text"),
           ("summary", "What changed"), ("status", "Decision"), ("decided_by", "Decided by"),
           ("comment", "Comment")]


def summary(e: dict) -> str:
    f, parts = e.get("facts") or {}, []
    if f.get("values_removed") or f.get("values_added"):
        parts.append(f"values {', '.join(f['values_removed']) or '-'} -> "
                     f"{', '.join(f['values_added']) or '-'}")
    if f.get("modal_changed") and f.get("modal_old") and f.get("modal_new"):
        parts.append(f"modal {f['modal_old']} -> {f['modal_new']}")
    if e["kind"] == "moved":
        parts.append(f"section {e.get('old_section')} -> {e.get('new_section')}")
    return "; ".join(parts)


def rows(audit: AuditStore, run_id: str) -> list[dict]:
    out = []
    for it in audit.list_items(run_id, "delta_entry"):
        d = audit.latest_decision(it["item_id"])
        out.append({**it["payload"], "id": it["item_id"].split("@")[0],
                    "summary": summary(it["payload"]),
                    "status": {"approved": "needs action", "rejected": "no action"}.get(
                        it["status"], "open"),
                    "decided_by": d["actor"] if d else "",
                    "comment": ((d or {}).get("detail") or {}).get("comment") or ""})
    return out


def export_delta(audit: AuditStore, run_id: str, actor: str, out_dir: Path | None = None) -> dict:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    data = rows(audit, run_id)
    meta = audit.get_item(f"DELTA-{run_id}")["payload"]
    out = out_dir or PROJECT_ROOT / "runs" / "exports" / run_id
    out.mkdir(parents=True, exist_ok=True)
    files = {"json": out / "delta.json", "xlsx": out / "delta.xlsx"}
    files["json"].write_text(json.dumps({"label": PROTOTYPE_LABEL, "run_id": run_id, **meta,
                                         "entries": data}, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = "Delta"
    ws.append([(f"{PROTOTYPE_LABEL} Run {run_id}. {meta['base_file']} -> {meta['new_file']}. "
               f"{meta['unchanged']} unchanged, not listed.")])
    ws["A1"].font = Font(bold=True)
    ws.append([h for _, h in COLUMNS])
    for c in ws[2]:
        c.font = Font(bold=True)
    for r in data:
        ws.append([str(r.get(k) or "") for k, _ in COLUMNS])
    for i, (_, h) in enumerate(COLUMNS, start=1):
        ws.column_dimensions[ws.cell(2, i).column_letter].width = (
            60 if h in ("Old text", "New text") else 16)
    wb.save(files["xlsx"])
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}
    audit.log_event(actor, "exported", run_id=run_id, object_type="delta_entry",
                    detail={"count": len(data), "files": {k: str(p) for k, p in files.items()},
                            "sha256": hashes})
    return {"count": len(data), "files": {k: str(p) for k, p in files.items()}}


def score(audit: AuditStore, run_id: str, key_path: Path | str) -> dict:
    """Expected changes ({kind, old?, new?} snippets) against the entries found.
    Removed or moved changes only count when the base run had that requirement approved;
    the key lists every change, so recall is over all of them."""
    expected = json.loads(Path(key_path).read_text(encoding="utf-8"))["changes"]
    entries = [it["payload"] for it in audit.list_items(run_id, "delta_entry")]
    found, missed = [], []
    for x in expected:
        def hit(e, x=x):
            return (e["kind"] == x["kind"]
                    and (not x.get("old") or x["old"].lower() in (e["old_text"] or "").lower())
                    and (not x.get("new") or x["new"].lower() in (e["new_text"] or "").lower()))
        (found if any(hit(e) for e in entries) else missed).append(x)
    return {"run_id": run_id, "expected": len(expected), "found": len(found),
            "missed": missed, "entries": len(entries)}
