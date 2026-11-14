"""Sift Review: check an existing requirement set.

Stage 1 (start): import the set with its own IDs and run deterministic code checks.
Stage 2 (ai_review): an AI reviewer reads the set in batches and reports findings. Each
  finding must quote the exact words it is about; code checks that the quote is really in
  the requirement. The AI never rewrites a requirement; it asks the author a question.
A named person confirms or dismisses every finding. A finding on unchanged text that was
decided in an earlier run shows that decision, so the same objection is not re-litigated.
"""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.prompts import load_prompt
from harness.schemas.check import QUALITY_FLAGS, SetReviewResult
from harness.sift import checks
from harness.sift.importer import load_requirement_set
from harness.sift.pipeline import StageReport
from harness.sift.rules import DEFAULT_CHECKS, RuleProfile, load_profile

WORKFLOW = "sift-check"
CODE_ACTOR = "code:sift-check"
REVIEW_PROMPT = "review_set_v1"
BATCH = 15

_PLACEHOLDER = re.compile(r"\b(TBD|TBC|TBA|XXX)\b|\?\?|<[^<>]{1,40}>", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9.]+")


def fingerprint(text: str, category: str, evidence: str) -> str:
    """Same requirement text, same category, same quoted words: the same finding."""
    key = "|".join((checks.normalise(text), category, checks.normalise(evidence)))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# ---- code checks --------------------------------------------------------------------


# EARS (Easy Approach to Requirements Syntax) sentence patterns, as commonly published:
# ubiquitous, event-driven (When), state-driven (While), optional feature (Where), unwanted
# behaviour (If ... then), and combinations. Our own regular expressions.
_EARS = [re.compile(x, re.IGNORECASE) for x in (
    r"^(the|an?)\s+[^,]+?\s+shall\s+\S",
    (r"^(when|while|where)\s+[^,]+(,\s*(when|while|where|if)\s+[^,]+)*,\s*(then\s+)?"
    r"(the|an?)\s+.+?\s+shall\s+\S"),
    r"^if\s+.+?,\s*(then\s+)?(the|an?)\s+.+?\s+shall\s+\S",
)]
_LEAD_NUMBER = re.compile(r"^\s*\d+(\.\d+)*\s+")


def is_ears(text: str) -> bool:
    t = _LEAD_NUMBER.sub("", text.strip())
    return any(p.search(t) for p in _EARS)


def code_findings(reqs: list[dict], style: str | None = None,
                  profile: RuleProfile | None = None) -> list[dict]:
    """Deterministic checks over the whole set. reqs: [{ext_id, text, heading}].
    profile chooses which checks run and tunes the weak-word list; without one, the
    built-in checks run, and style="ears" adds the EARS pattern check."""
    if profile is None:
        profile = RuleProfile(name="built-in", checks=[*DEFAULT_CHECKS, "not_ears"]
                              if style == "ears" else list(DEFAULT_CHECKS))
    out = []

    def add(r, category, evidence, explanation, question, related=()):
        out.append({"req_id": r["ext_id"], "category": category, "evidence": evidence,
                    "explanation": explanation, "question_for_author": question,
                    "related_ids": list(related)})

    seen_ids: dict[str, int] = {}
    for r in reqs:
        seen_ids[r["ext_id"]] = seen_ids.get(r["ext_id"], 0) + 1
    by_text: dict[str, list[str]] = {}
    for r in reqs:
        text = r["text"]
        for w in (profile.weak_words(text) if profile.on("weak_word") else []):
            add(r, "weak_word", w, f"'{w}' is vague; a tester cannot set a pass/fail limit "
                "from it.", f"What measurable criterion does '{w}' stand for?")
        for m in (_PLACEHOLDER.finditer(text) if profile.on("placeholder") else []):
            add(r, "placeholder", m.group(0), "The requirement contains an open placeholder.",
                "What is the value or wording that replaces the placeholder?")
        modals = checks._MODAL.findall(text)
        if not modals and profile.on("no_modal"):
            add(r, "no_modal", text[:60], "No modal verb (shall, should, must, will, may): "
                "it may be information rather than a requirement, or its obligation is "
                "unstated.", "Is this a requirement, and how binding is it?")
        elif len(modals) > 1 and profile.on("not_atomic"):
            add(r, "not_atomic", modals[1], f"More than one modal verb ({len(modals)}): it may "
                "state several independently testable behaviours.",
                "Should this be split into separate requirements?")
        if profile.on("not_ears") and not is_ears(text):
            add(r, "not_ears", " ".join(text.split()[:6]), "Does not follow an EARS pattern "
                "(The <system> shall ..., When/While/Where <condition>, the <system> shall "
                "..., If <condition>, then the <system> shall ...).",
                "Can this be written in one of the EARS patterns?")
        if seen_ids[r["ext_id"]] > 1 and profile.on("duplicate_id"):
            add(r, "duplicate_id", r["ext_id"], "This ID is used by more than one requirement.",
                "Which ID should each of these requirements carry?")
        by_text.setdefault(checks.normalise(text), []).append(r["ext_id"])
    if profile.custom_checks:
        from harness.sift.custom import findings as custom_findings
        out += custom_findings(profile.custom_checks, reqs)
    for ids in by_text.values():
        if len(ids) > 1 and profile.on("duplicate_text"):
            for r in reqs:
                if r["ext_id"] in ids:
                    add(r, "duplicate_text", r["text"][:60], "Identical text appears under "
                        "another ID.", "Is one of these redundant?",
                        [i for i in ids if i != r["ext_id"]])
    return out


# ---- stage 1: import and code checks ------------------------------------------------


def _prior_decisions(audit: AuditStore, run_id: str) -> dict[str, dict]:
    """fingerprint -> the latest human decision on that finding in an earlier run."""
    best: dict[str, dict] = {}
    for it in audit.items_of_type("finding"):
        if it["run_id"] == run_id:
            continue
        d = audit.latest_decision(it["item_id"])
        fp = it["payload"].get("fingerprint")
        if d and fp and (fp not in best or d["event_id"] > best[fp]["event_id"]):
            best[fp] = {"event_id": d["event_id"], "decision": d["action"], "by": d["actor"],
                        "run_id": it["run_id"], "at": d["ts"],
                        "comment": (d["detail"] or {}).get("comment")}
    return best


def _same_problem_key(f: dict) -> tuple:
    """Two reports describe the same problem: same requirement and category, or, for
    conflicts and duplicates, the same set of requirements involved."""
    if f["category"] in ("conflict", "duplicate", "duplicate_text"):
        return ("pair", "dup" if "duplicate" in f["category"] else "conflict",
                frozenset([f["req_id"], *f.get("related_ids", [])]))
    return ("one", f["req_id"], f["category"])


def _store_findings(audit: AuditStore, run_id: str, raw: list[dict], source: str,
                    created_by: str) -> int:
    texts = {it["payload"]["ext_id"]: it["payload"]["text"]
             for it in audit.list_items(run_id, "imported_requirement")}
    prior = _prior_decisions(audit, run_id)
    existing = audit.list_items(run_id, "finding")
    seen = {_same_problem_key(f["payload"]): f["item_id"] for f in existing}
    n = len(existing)
    added = 0
    for f in raw:
        text = texts.get(f["req_id"])
        if text is None:
            audit.log_event(CODE_ACTOR, "finding_dropped", run_id=run_id,
                            detail={"reason": "unknown requirement ID", **f})
            continue
        key = _same_problem_key(f)
        if key in seen:
            # Same problem already reported: record the second report as corroboration
            # instead of adding a second finding for the reviewer to decide.
            audit.log_event(created_by, "finding_corroborated", run_id=run_id,
                            object_type="finding", object_id=seen[key],
                            detail={"source": source, **f})
            continue
        fp = fingerprint(text, f["category"], f["evidence"])
        n += 1
        iid = f"FND-{n:04d}@{run_id}"
        audit.add_item(run_id, "finding", {
            **f, "source": source, "requirement_text": text,
            "evidence_found": checks.is_grounded(f["evidence"], text),
            "fingerprint": fp, "prior": prior.get(fp),
        }, created_by=created_by, item_id=iid)
        seen[key] = iid
        added += 1
    return added


def corroborations(audit: AuditStore, finding_id: str) -> list[dict]:
    return [e["detail"] for e in audit.events(object_id=finding_id)
            if e["action"] == "finding_corroborated" and e["detail"]]


def resolve_profile(rules: str | None = None, style: str | None = None) -> RuleProfile:
    """The rule profile for a new run: by name, else 'ears' for style='ears', else default."""
    if rules:
        return load_profile(rules)
    if style == "ears":
        try:
            return load_profile("ears")
        except FileNotFoundError:
            return RuleProfile(name="ears", checks=[*DEFAULT_CHECKS, "not_ears"])
    return load_profile("default")


def _quote_of(attrs: dict) -> str:
    """A source-quote column the other tool may have exported with each requirement."""
    for k, v in attrs.items():
        if re.search(r"quote|source.?text", k, re.IGNORECASE) and v:
            return v
    return ""


def start(cfg: HarnessConfig, audit: AuditStore, path: Path | str,
          style: str | None = None, rules: str | None = None,
          source: Path | str | None = None) -> StageReport:
    """Import and code-check a set. With source (the specification the set was drawn from,
    by Zyn or any other tool), each requirement is also matched to its source sentence and
    checked for invented values and changed modal verbs."""
    profile = resolve_profile(rules, style)
    style = "ears" if profile.on("not_ears") else None
    rs = load_requirement_set(path)
    run_id = audit.start_run(WORKFLOW, note=f"{rs.filename} sha256={rs.sha256[:12]}")
    src_meta = None
    if source:
        from harness.sift.ingest import file_sha256
        src_meta = {"filename": Path(source).name, "sha256": file_sha256(Path(source))}
    audit.add_item(run_id, "requirement_set", {**rs.to_payload(), "style": style,
                                               "path": str(Path(path).resolve()),
                                               "rules": profile.summary(),
                                               "source": src_meta},
                   created_by="code:import", item_id=f"SET-{run_id}")
    audit.log_event("code:import", "ingested", run_id=run_id, object_type="requirement_set",
                    input_sha256=rs.sha256, detail=rs.to_payload())
    for r in rs.requirements:
        audit.add_item(run_id, "imported_requirement",
                       {"ext_id": r.ext_id, "text": r.text, "heading": r.heading,
                        "order": r.order, "attrs": r.attrs},
                       created_by="code:import", item_id=f"IR-{r.order + 1:04d}@{run_id}")
    found = code_findings([{"ext_id": r.ext_id, "text": r.text, "heading": r.heading}
                           for r in rs.requirements], profile=profile)
    if source:
        from harness.outside import ground_findings
        from harness.sift.ingest import load_document

        doc = load_document(source)
        grounded, matches = ground_findings(
            [{"ext_id": r.ext_id, "text": r.text, "quote": _quote_of(r.attrs)}
             for r in rs.requirements], doc, profile)
        found += grounded
        audit.log_event("code:import", "ingested", run_id=run_id, object_type="source",
                        input_sha256=doc.sha256,
                        detail={"filename": doc.filename, "sha256": doc.sha256,
                                "matches": matches})
    _store_findings(audit, run_id, found, "code", CODE_ACTOR)
    return StageReport(run_id, [r.ext_id for r in rs.requirements], [], {})


# ---- stage 2: AI review -------------------------------------------------------------


def batches(audit: AuditStore, run_id: str, size: int = BATCH) -> list[list[dict]]:
    reqs = sorted(audit.list_items(run_id, "imported_requirement"),
                  key=lambda i: i["payload"]["order"])
    return [reqs[i:i + size] for i in range(0, len(reqs), size)]


def ai_done(audit: AuditStore, run_id: str) -> set[int]:
    return {e["detail"]["batch"] for e in audit.events(run_id=run_id)
            if e["action"] == "ai_batch_done" and e["detail"]}


def _review_batch(cfg, audit, run_id, n, batch, reviewer):
    lines = "\n".join(f"[{i['payload']['ext_id']}] ({i['payload']['heading'] or '-'}) "
                      f"{i['payload']['text']}" for i in batch)
    return structured_call(
        cfg=cfg, audit=audit, run_id=run_id, role_or_profile=reviewer,
        task="review_set", prompt_version=REVIEW_PROMPT, system=load_prompt(REVIEW_PROMPT),
        user=f"Requirements (batch {n + 1}):\n{lines}", output_model=SetReviewResult,
        actor=f"ai-reviewer:{cfg.profile(reviewer).name}")


def ai_review(cfg: HarnessConfig, audit: AuditStore, run_id: str, reviewer: str = "reviewer",
              workers: int = 4, size: int = BATCH, conflicts: bool = True) -> StageReport:
    all_b = batches(audit, run_id, size)
    done_before = ai_done(audit, run_id)
    todo, skipped = [], []
    for n, b in enumerate(all_b):
        if n in done_before or not audit.claim(run_id, f"check:batch-{n}", CODE_ACTOR):
            skipped.append(f"batch-{n}")
        else:
            todo.append((n, b))
    results, failed = {}, {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_review_batch, cfg, audit, run_id, n, b, reviewer): n
                for n, b in todo}
        for fut, n in futs.items():
            try:
                results[n] = fut.result()
            except StructuredOutputFailure as e:
                failed[f"batch-{n}"] = str(e)
                audit.release(run_id, f"check:batch-{n}", CODE_ACTOR)
            except Exception:
                for m in futs.values():
                    audit.release(run_id, f"check:batch-{m}", CODE_ACTOR)
                raise
    done = []
    for n in sorted(results):
        res = results[n]
        raw = [f.model_dump(mode="json") for f in res.output.findings]
        added = _store_findings(audit, run_id, raw, "ai", f"ai-reviewer:{res.profile_name}")
        audit.log_event(CODE_ACTOR, "ai_batch_done", run_id=run_id,
                        detail={"batch": n, "findings": added})
        done.append(f"batch-{n}")
    if conflicts:
        rep = conflict_pass(cfg, audit, run_id, reviewer)
        done += rep.done
        skipped += rep.skipped
        failed.update(rep.failed)
    return StageReport(run_id, done, skipped, failed)


# ---- set-wide conflict pass ---------------------------------------------------------

CONFLICT_PROMPT = "review_set_conflicts_v1"
CONFLICT_WINDOW = 200


def conflict_windows(audit: AuditStore, run_id: str) -> list[list[dict]]:
    reqs = sorted(audit.list_items(run_id, "imported_requirement"),
                  key=lambda i: i["payload"]["order"])
    return [reqs[i:i + CONFLICT_WINDOW] for i in range(0, len(reqs), CONFLICT_WINDOW)]


def conflicts_done(audit: AuditStore, run_id: str) -> set[int]:
    return {e["detail"]["window"] for e in audit.events(run_id=run_id)
            if e["action"] == "ai_conflicts_done" and e["detail"]}


def conflict_pass(cfg: HarnessConfig, audit: AuditStore, run_id: str,
                  reviewer: str = "reviewer") -> StageReport:
    """Reads the whole set (up to 200 requirements per call) for conflicts and duplicates,
    which the batch review cannot see across batch boundaries."""
    done, skipped, failed = [], [], {}
    finished = conflicts_done(audit, run_id)
    for n, window in enumerate(conflict_windows(audit, run_id)):
        if n in finished or not audit.claim(run_id, f"check:conflicts-{n}", CODE_ACTOR):
            skipped.append(f"window-{n}")
            continue
        lines = "\n".join(f"[{i['payload']['ext_id']}] ({i['payload']['heading'] or '-'}) "
                          f"{i['payload']['text']}" for i in window)
        try:
            res = structured_call(
                cfg=cfg, audit=audit, run_id=run_id, role_or_profile=reviewer,
                task="review_set_conflicts", prompt_version=CONFLICT_PROMPT,
                system=load_prompt(CONFLICT_PROMPT), user=f"Requirements:\n{lines}",
                output_model=SetReviewResult,
                actor=f"ai-reviewer:{cfg.profile(reviewer).name}")
        except StructuredOutputFailure as e:
            failed[f"window-{n}"] = str(e)
            audit.release(run_id, f"check:conflicts-{n}", CODE_ACTOR)
            continue
        raw = [f.model_dump(mode="json") for f in res.output.findings
               if f.category.value in ("conflict", "duplicate")]
        added = _store_findings(audit, run_id, raw, "ai", f"ai-reviewer:{res.profile_name}")
        audit.log_event(CODE_ACTOR, "ai_conflicts_done", run_id=run_id,
                        detail={"window": n, "findings": added})
        done.append(f"window-{n}")
    return StageReport(run_id, done, skipped, failed)


# ---- stability: repeat the AI review and see which findings recur ----------------------
#
# Pass 1 is the normal AI review. Each extra pass reads the same set again with the same
# prompts. A reported problem that matches an existing finding (same requirement and
# category, or the same requirements for a conflict) is recorded as seen in that pass; a
# new one becomes a finding first seen in that pass. Code findings are deterministic and
# are not counted.


def passes_done(audit: AuditStore, run_id: str) -> list[int]:
    """Completed AI passes. Pass 1 counts once every batch and conflict window is done."""
    done = []
    if (len(ai_done(audit, run_id)) == len(batches(audit, run_id))
            and len(conflicts_done(audit, run_id)) == len(conflict_windows(audit, run_id))):
        done.append(1)
    done += sorted({e["detail"]["pass"] for e in audit.events(run_id=run_id)
                    if e["action"] == "stability_pass_done" and e["detail"]})
    return done


def seen_in(audit: AuditStore, finding: dict) -> set[int]:
    """AI passes that reported this finding."""
    first = finding["payload"].get("first_pass", 1)
    return {first} | {e["detail"]["pass"] for e in audit.events(object_id=finding["item_id"])
                      if e["action"] == "finding_seen" and e["detail"]}


def stability(audit: AuditStore, run_id: str) -> dict[str, tuple[int, int]]:
    """finding item id -> (passes that reported it, passes completed), AI findings only."""
    total = len(passes_done(audit, run_id))
    return {f["item_id"]: (len(seen_in(audit, f)), total)
            for f in audit.list_items(run_id, "finding") if f["payload"]["source"] == "ai"}


def _record_pass(audit: AuditStore, run_id: str, raw: list[dict], pass_no: int,
                 created_by: str) -> dict:
    texts = {it["payload"]["ext_id"]: it["payload"]["text"]
             for it in audit.list_items(run_id, "imported_requirement")}
    existing = [f for f in audit.list_items(run_id, "finding")]
    seen = {_same_problem_key(f["payload"]): f["item_id"] for f in existing}
    marked, new = set(), []
    for f in raw:
        if f["req_id"] not in texts:
            continue
        key = _same_problem_key(f)
        if key in seen:
            if seen[key] not in marked:
                marked.add(seen[key])
                audit.log_event(created_by, "finding_seen", run_id=run_id,
                                object_type="finding", object_id=seen[key],
                                detail={"pass": pass_no, **f})
        elif key not in {_same_problem_key(x) for x in new}:
            new.append({**f, "first_pass": pass_no})
    added = _store_findings(audit, run_id, new, "ai", created_by)
    return {"matched": len(marked), "new": added}


def stability_pass(cfg: HarnessConfig, audit: AuditStore, run_id: str, pass_no: int,
                   reviewer: str = "reviewer", workers: int = 4) -> StageReport:
    """One extra AI pass over the whole set (batches and the conflict pass). Always asks
    the model again: a replayed answer would make every pass agree."""
    cfg = cfg.fresh()
    if pass_no < 2:
        raise ValueError("Pass 1 is the normal AI review.")
    if pass_no in passes_done(audit, run_id):
        return StageReport(run_id, [], [f"pass-{pass_no}"], {})
    key = f"check:stability-{pass_no}"
    if not audit.claim(run_id, key, CODE_ACTOR):
        return StageReport(run_id, [], [f"pass-{pass_no}"], {})
    jobs = [("batch", n, b) for n, b in enumerate(batches(audit, run_id))]
    jobs += [("window", n, w) for n, w in enumerate(conflict_windows(audit, run_id))]

    def one(kind, n, items):
        if kind == "batch":
            return _review_batch(cfg, audit, run_id, n, items, reviewer)
        lines = "\n".join(f"[{i['payload']['ext_id']}] ({i['payload']['heading'] or '-'}) "
                          f"{i['payload']['text']}" for i in items)
        return structured_call(
            cfg=cfg, audit=audit, run_id=run_id, role_or_profile=reviewer,
            task="review_set_conflicts", prompt_version=CONFLICT_PROMPT,
            system=load_prompt(CONFLICT_PROMPT), user=f"Requirements:\n{lines}",
            output_model=SetReviewResult, actor=f"ai-reviewer:{cfg.profile(reviewer).name}")

    raw, failed, profile = [], {}, cfg.profile(reviewer).name
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, k, n, it): (k, n) for k, n, it in jobs}
        for fut, (k, n) in futs.items():
            try:
                res = fut.result()
            except StructuredOutputFailure as e:
                failed[f"{k}-{n}"] = str(e)
                continue
            profile = res.profile_name
            found = [f.model_dump(mode="json") for f in res.output.findings]
            if k == "window":
                found = [f for f in found if f["category"] in ("conflict", "duplicate")]
            raw += found
    if failed:
        # An incomplete pass would undercount recurrence; record nothing and allow a retry.
        audit.release(run_id, key, CODE_ACTOR)
        return StageReport(run_id, [], [], failed)
    counts = _record_pass(audit, run_id, raw, pass_no, f"ai-reviewer:{profile}")
    audit.log_event(CODE_ACTOR, "stability_pass_done", run_id=run_id,
                    detail={"pass": pass_no, **counts})
    return StageReport(run_id, [f"pass-{pass_no}"], [], {})


def stability_check(cfg: HarnessConfig, audit: AuditStore, run_id: str, total_passes: int = 3,
                    reviewer: str = "reviewer", workers: int = 4) -> StageReport:
    """Brings the run up to total_passes AI passes. Pass 1 must be complete."""
    if 1 not in passes_done(audit, run_id):
        raise ValueError("Run the AI review first; the stability check repeats it.")
    done, skipped, failed = [], [], {}
    for p in range(2, total_passes + 1):
        rep = stability_pass(cfg, audit, run_id, p, reviewer, workers)
        done += rep.done
        skipped += rep.skipped
        failed.update(rep.failed)
        if rep.failed:
            break
    return StageReport(run_id, done, skipped, failed)


# ---- carrying earlier decisions over ------------------------------------------------


def carry_over_candidates(audit: AuditStore, run_id: str) -> list[dict]:
    return [f for f in audit.list_items(run_id, "finding")
            if f["status"] == "proposed" and f["payload"].get("prior")]


def apply_prior(audit: AuditStore, run_id: str, actor: str) -> int:
    """A named person applies earlier decisions on identical findings, in one action."""
    n = 0
    for f in carry_over_candidates(audit, run_id):
        p = f["payload"]["prior"]
        audit.decide(f["item_id"], p["decision"], actor,
                     comment=f"carried over: {p['decision']} by {p['by']} in run {p['run_id']}"
                             + (f" ({p['comment']})" if p.get("comment") else ""))
        n += 1
    return n


# ---- export and scoring -------------------------------------------------------------

FINDING_COLUMNS = [
    ("req_id", "Requirement ID"), ("requirement_text", "Requirement"),
    ("category", "Finding"), ("source", "Found by"), ("evidence", "Quoted words"),
    ("evidence_found", "Quote located in text"), ("explanation", "Explanation"),
    ("question_for_author", "Question for author"), ("related_ids", "Related IDs"),
    ("status", "Status"), ("decided_by", "Decided by"), ("comment", "Comment"),
]


def finding_rows(audit: AuditStore, run_id: str) -> list[dict]:
    rows = []
    for f in audit.list_items(run_id, "finding"):
        d = audit.latest_decision(f["item_id"])
        p = f["payload"]
        rows.append({**p, "id": f["item_id"].split("@")[0],
                     "related_ids": ", ".join(p.get("related_ids", [])),
                     "status": {"approved": "confirmed", "rejected": "dismissed"}.get(
                         f["status"], "open"),
                     "decided_by": d["actor"] if d else "",
                     "comment": ((d or {}).get("detail") or {}).get("comment") or ""})
    return rows


def export_findings(audit: AuditStore, run_id: str, actor: str,
                    out_dir: Path | None = None) -> dict:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    rows = finding_rows(audit, run_id)
    out = out_dir or PROJECT_ROOT / "runs" / "exports" / run_id
    out.mkdir(parents=True, exist_ok=True)
    meta = audit.get_item(f"SET-{run_id}")["payload"]
    files = {"json": out / "findings.json", "xlsx": out / "findings.xlsx"}
    if meta.get("kind") != "tests":
        from harness.sift.roundtrip import export_reqif
        rt = export_reqif(audit, run_id, actor, out)
        files["reqif"] = Path(rt["file"])
    else:
        from harness import checklist
        files["checklist"] = checklist.write(audit, run_id, out / "checklist.xlsx")
    files["json"].write_text(json.dumps(
        {"label": PROTOTYPE_LABEL, "run_id": run_id, "requirement_set": meta["filename"],
         "findings": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = "Findings"
    ws.append([(f"{PROTOTYPE_LABEL} Run {run_id}. Findings on {meta['filename']}. "
               "Open findings are unreviewed.")])
    ws["A1"].font = Font(bold=True)
    ws.append([h for _, h in FINDING_COLUMNS])
    for c in ws[2]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([str(r.get(k, "")) for k, _ in FINDING_COLUMNS])
    for i, (_, h) in enumerate(FINDING_COLUMNS, start=1):
        ws.column_dimensions[ws.cell(2, i).column_letter].width = (
            60 if h in ("Requirement", "Explanation", "Question for author") else 18)
    ws.freeze_panes = "B3"
    wb.save(files["xlsx"])
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}
    audit.log_event(actor, "exported", run_id=run_id, object_type="finding",
                    detail={"count": len(rows), "files": {k: str(p) for k, p in files.items()},
                            "sha256": hashes})
    return {"count": len(rows), "files": {k: str(p) for k, p in files.items()}}


def score(audit: AuditStore, run_id: str, key_path: Path | str,
          sources: tuple[str, ...] = ("code", "ai"), min_passes: int = 1) -> dict:
    """Quality-flag findings against an answer key keyed by requirement ID (gold_id).
    Counts what the tool reported before human review. Only the seven quality-flag
    categories are scored; set-level categories are listed separately."""
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    gold = {g["gold_id"]: g for g in key["requirements"]}
    ids = {i["payload"]["ext_id"] for i in audit.list_items(run_id, "imported_requirement")}
    if not gold or not ids & set(gold):
        raise ValueError(f"The answer key {Path(key_path).name} names no requirement in run "
                         f"{run_id}, so nothing can be scored.")
    found: dict[str, set[str]] = {}
    other: dict[str, int] = {}
    for f in audit.list_items(run_id, "finding"):
        p = f["payload"]
        if p["source"] not in sources:
            continue
        if p["source"] == "ai" and min_passes > 1 and len(seen_in(audit, f)) < min_passes:
            continue
        if p["category"] in QUALITY_FLAGS:
            found.setdefault(p["req_id"], set()).add(p["category"])
        else:
            other[p["category"]] = other.get(p["category"], 0) + 1
    hit = need = fp = 0
    misses, extras = [], []
    for gid, g in gold.items():
        want, ok = set(g["flags"]), set(g["flags"]) | set(g.get("acceptable_flags", []))
        got = found.get(gid, set())
        need += len(want)
        hit += len(want & got)
        misses += [f"{gid}:{c}" for c in sorted(want - got)]
        extras += [f"{gid}:{c}" for c in sorted(got - ok)]
        fp += len(got - ok)
    flagged = sum(1 for gid in gold if found.get(gid))
    # Report only the sources that actually ran, so a code-only run never reads as AI-reviewed.
    ai_ran = bool(ai_done(audit, run_id))
    ran = [s for s in sources if s != "ai" or ai_ran]
    return {"run_id": run_id, "sources": ran,
            "ai_review": "run" if ai_ran else "not run",
            "required_flags": need, "found": hit,
            "recall": round(hit / need, 3) if need else None, "flags_not_in_key": fp,
            "requirements_with_findings": flagged, "requirements": len(gold),
            "missed": misses, "not_in_key": extras, "other_categories": other}
