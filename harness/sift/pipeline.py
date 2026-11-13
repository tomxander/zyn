"""Sift pipeline. Each stage reads only what a human approved in the stage before.

  start()    document -> sections -> proposed subsystem mappings      (human reviews mappings)
  extract()  approved, non-NONE mappings -> requirements + code checks
             + AI review per section                                 (human reviews requirements)
  clarify()  optional: flagged requirements -> proposed testable wording
             with <TBD: ...> placeholders                             (human uses or ignores)
  export()   approved requirements -> JSON, XLSX, ReqIF               (see export.py)
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.audit.store import AuditStore
from harness.config import HarnessConfig
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.prompts import load_prompt
from harness.schemas.sift import (
    ClarificationReport,
    ExtractionResult,
    MappingResult,
    ReviewReportV3,
)
from harness.sift import checks
from harness.sift.ingest import load_document
from harness.taxonomy import load_taxonomy

WORKFLOW = "sift"


def _local_aliases() -> set[str]:
    """Workflow ids that older local runs were recorded under, read from
    runs/workflow_aliases.json ({"old id": "sift"}). The file lives with the runs, outside
    the repository; without it there are no aliases."""
    from harness.config import PROJECT_ROOT

    p = PROJECT_ROOT / "runs" / "workflow_aliases.json"
    try:
        return {k for k, v in json.loads(p.read_text(encoding="utf-8")).items() if v == WORKFLOW}
    except (OSError, ValueError, AttributeError):
        return set()


LEGACY_WORKFLOWS = _local_aliases()  # runs recorded before a rename
CODE_ACTOR = "code:sift"
REVIEW_PROMPT = "review_requirements_v3"
PREVIEW_CHARS = 600


@dataclass
class StageReport:
    run_id: str
    done: list[str]
    skipped: list[str]
    failed: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "done": self.done, "skipped": self.skipped,
                "failed": self.failed}


# ---- stage 1: ingest and map ------------------------------------------------------


def start(cfg: HarnessConfig, audit: AuditStore, path: Path | str,
          generator: str = "generator") -> StageReport:
    doc = load_document(path)
    run_id = audit.start_run(WORKFLOW, note=f"{doc.filename} sha256={doc.sha256[:12]}")
    audit.add_item(run_id, "document", doc.to_payload(), created_by="code:ingest",
                   item_id=f"DOC-{run_id}")
    audit.log_event("code:ingest", "ingested", run_id=run_id, object_type="document",
                    input_sha256=doc.sha256,
                    detail={"filename": doc.filename, "converter": doc.converter,
                            "sections": len(doc.sections)})
    for s in doc.sections:
        audit.add_item(run_id, "section", s.__dict__, created_by="code:ingest",
                       item_id=f"{run_id}:{s.section_id}")

    tax = load_taxonomy()
    listing = "\n\n".join(
        f"section_id: {s.section_id}\nheading: {s.number or ''} {s.heading}\n"
        f"text: {s.text[:PREVIEW_CHARS]}" for s in doc.sections
    )
    res = structured_call(
        cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator,
        task="map_sections", prompt_version="map_sections_v1",
        system=load_prompt("map_sections_v1").replace("{taxonomy}", tax.prompt_block()),
        user=f"Document: {doc.title}\n\nSections:\n\n{listing}",
        output_model=MappingResult,
    )
    by_id = {m.section_id: m for m in res.output.mappings}
    done, missing = [], []
    for s in doc.sections:
        m = by_id.get(s.section_id)
        if m is None:
            missing.append(s.section_id)
            continue
        audit.add_item(run_id, "section_mapping", {
            "section_id": s.section_id, "number": s.number, "heading": s.heading,
            "subsystem_id": m.subsystem_id.value, "confidence": m.confidence,
            "rationale": m.rationale, "text_preview": s.text[:PREVIEW_CHARS],
            "generated_by": res.profile_name,
        }, created_by=f"model:{res.profile_name}", item_id=f"MAP-{s.section_id}@{run_id}")
        done.append(s.section_id)
    if missing:
        audit.log_event("code:sift", "mapping_incomplete", run_id=run_id,
                        detail={"sections_without_mapping": missing})
    return StageReport(run_id, done, [], {sid: "model returned no mapping" for sid in missing})


# ---- stage 2: extract, check, AI review ------------------------------------------


def _section_text(audit: AuditStore, run_id: str, section_id: str) -> dict:
    return audit.get_item(f"{run_id}:{section_id}")["payload"]


def _doc_title(audit: AuditStore, run_id: str) -> str:
    return audit.get_item(f"DOC-{run_id}")["payload"]["title"]


def _extract_one(cfg: HarnessConfig, audit: AuditStore, run_id: str, mapping: dict,
                 generator: str, reviewer: str | None) -> dict:
    p = mapping["payload"]
    sec = _section_text(audit, run_id, p["section_id"])
    system = (load_prompt("extract_v2")
              .replace("{section_number}", sec["number"] or "-")
              .replace("{heading}", sec["heading"])
              .replace("{doc_title}", _doc_title(audit, run_id))
              .replace("{subsystem_id}", p["subsystem_id"]))
    gen = structured_call(
        cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator,
        task="extract_requirements", prompt_version="extract_v2", system=system,
        user=f"Section text:\n<section>\n{sec['text']}\n</section>",
        output_model=ExtractionResult,
    )
    review = None
    if reviewer and gen.output.requirements:
        numbered = "\n".join(
            f"[{i}] {json.dumps(r.model_dump(mode='json'), ensure_ascii=False)}"
            for i, r in enumerate(gen.output.requirements))
        review = structured_call(
            cfg=cfg, audit=audit, run_id=run_id, role_or_profile=reviewer,
            task="review_requirements", prompt_version=REVIEW_PROMPT,
            system=load_prompt(REVIEW_PROMPT),
            user=(f"Section {sec['number'] or ''} {sec['heading']}:\n<section>\n{sec['text']}\n"
                  f"</section>\n\nItems:\n{numbered}"),
            output_model=ReviewReportV3, actor=f"ai-reviewer:{cfg.profile(reviewer).name}",
        )
    return {"mapping": p, "section": sec, "gen": gen, "review": review}


def _next_numbers(audit: AuditStore, run_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for it in audit.list_items(run_id, "requirement"):
        sub = it["payload"]["subsystem_id"]
        counts[sub] = max(counts.get(sub, 0), int(it["item_id"].split("-")[2].split("@")[0]))
    return counts


def extract(cfg: HarnessConfig, audit: AuditStore, run_id: str, generator: str = "generator",
            reviewer: str | None = "reviewer", workers: int = 4) -> StageReport:
    """Runs on approved mappings only. Sections already extracted in this run are skipped,
    so it can be re-run after more mappings are approved."""
    mappings = audit.approved_items(run_id, "section_mapping")
    already = {it["payload"]["section_id"] for it in audit.list_items(run_id, "requirement")}
    already |= {e["detail"]["section_id"] for e in audit.events(run_id=run_id)
                if e["action"] == "extracted_none" and e["detail"]}
    todo = [m for m in mappings if m["payload"]["subsystem_id"] != "NONE"
            and m["payload"]["section_id"] not in already]
    skipped = [m["payload"]["section_id"] for m in mappings if m not in todo]
    # Claim each section so a second extraction started at the same time (another browser
    # tab, the CLI) skips it instead of producing a duplicate set.
    claimed = []
    for m in todo:
        if audit.claim(run_id, f"extract:{m['payload']['section_id']}", CODE_ACTOR):
            claimed.append(m)
        else:
            skipped.append(m["payload"]["section_id"])
    todo = claimed

    results, failed = [], {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_extract_one, cfg, audit, run_id, m, generator, reviewer):
                   m["payload"]["section_id"] for m in todo}
        for fut, sid in futures.items():
            try:
                results.append(fut.result())
            except StructuredOutputFailure as e:
                failed[sid] = str(e)
                audit.release(run_id, f"extract:{sid}", CODE_ACTOR)  # allow a retry
            except Exception:
                for s in futures.values():
                    audit.release(run_id, f"extract:{s}", CODE_ACTOR)
                raise

    # store in document order so IDs follow the document
    order = {it["payload"]["section_id"]: it["payload"]["order"]
             for it in audit.list_items(run_id, "section")}
    results.sort(key=lambda r: order.get(r["mapping"]["section_id"], 0))
    numbers = _next_numbers(audit, run_id)
    done = []
    for r in results:
        p, sec, gen, review = r["mapping"], r["section"], r["gen"], r["review"]
        sub = p["subsystem_id"]
        if not gen.output.requirements:
            audit.log_event("code:sift", "extracted_none", run_id=run_id,
                            detail={"section_id": p["section_id"]})
        ids = []
        for req in gen.output.requirements:
            numbers[sub] = numbers.get(sub, 0) + 1
            payload = req.model_dump(mode="json")
            found_weak = checks.weak_words(req.source_quote)
            payload.update({
                "subsystem_id": sub,
                "section_id": p["section_id"],
                "section_number": sec["number"],
                "section_heading": sec["heading"],
                "grounded": checks.is_grounded(req.source_quote, sec["text"]),
                "page": sec.get("page"),
                "quote_offset": quote_offset(req.source_quote, sec["text"]),
                "modal_changed": checks.modal_changed(req.source_quote, req.text),
                "weak_words_found": found_weak,
                "weak_word_unflagged": bool(found_weak) and "weak_word" not in payload[
                    "quality_flags"],
                "generated_by": gen.profile_name,
            })
            ids.append(audit.add_item(
                run_id, "requirement", payload, created_by=f"model:{gen.profile_name}",
                item_id=f"REQ-{sub}-{numbers[sub]:03d}@{run_id}"))
        if review:
            for rv in review.output.reviews:
                if 0 <= rv.index < len(ids):
                    detail = rv.model_dump(mode="json")
                    if rv.suggested_text:
                        req = gen.output.requirements[rv.index]
                        detail["suggestion_problems"] = checks.suggestion_problems(
                            rv.suggested_text, req.source_quote, sec["text"])
                    audit.log_event(f"ai-reviewer:{review.profile_name}", "ai_reviewed",
                                    run_id=run_id, object_type="requirement",
                                    object_id=ids[rv.index], object_version=1,
                                    detail=detail)
            if review.output.missed:
                audit.log_event(f"ai-reviewer:{review.profile_name}", "ai_review_missed",
                                run_id=run_id, object_type="section",
                                object_id=p["section_id"],
                                detail={"section_id": p["section_id"],
                                        "missed": review.output.missed})
        done.append(p["section_id"])
    return StageReport(run_id, done, skipped, failed)


# ---- stage 2b: clarification proposals for flagged source wording --------------------
#
# The extractor keeps vague source wording vague and flags it. This optional stage asks a
# model how the wording could be made testable, with <TBD: ...> placeholders where the
# source gives no value. Proposals are advice for the reviewer and the spec author; using
# one is a human edit that creates a new version.

CLARIFY_PROMPT = "clarify_v1"


def clarify_candidates(audit: AuditStore, run_id: str) -> list[dict]:
    """Flagged requirements still under review with no proposal for their current version."""
    proposed = {(e["object_id"], e["object_version"]) for e in audit.events(run_id=run_id)
                if e["action"] in ("clarification_proposed", "clarification_none")}
    return [it for it in audit.list_items(run_id, "requirement")
            if it["payload"].get("quality_flags")
            and it["status"] in ("proposed", "edited")
            and (it["item_id"], it["version"]) not in proposed]


def latest_clarification(audit: AuditStore, item_id: str) -> dict | None:
    """The most recent proposal for the item's CURRENT version, or None."""
    current = audit.get_item(item_id)
    evs = [e for e in audit.events(object_id=item_id)
           if e["action"] == "clarification_proposed"
           and e["object_version"] == current["version"]]
    return evs[-1] if evs else None


def _clarify_section(cfg: HarnessConfig, audit: AuditStore, run_id: str, section_id: str,
                     items: list[dict], model: str) -> None:
    sec = _section_text(audit, run_id, section_id)
    system = (load_prompt(CLARIFY_PROMPT)
              .replace("{section_number}", sec["number"] or "-")
              .replace("{heading}", sec["heading"])
              .replace("{doc_title}", _doc_title(audit, run_id)))
    numbered = "\n".join(
        f"[{i}] " + json.dumps({k: it["payload"].get(k) for k in
                                ("text", "source_quote", "modal", "quality_flags")},
                               ensure_ascii=False)
        for i, it in enumerate(items))
    res = structured_call(
        cfg=cfg, audit=audit, run_id=run_id, role_or_profile=model,
        task="propose_clarifications", prompt_version=CLARIFY_PROMPT, system=system,
        user=(f"Section {sec['number'] or ''} {sec['heading']}:\n<section>\n{sec['text']}\n"
              f"</section>\n\nItems:\n{numbered}"),
        output_model=ClarificationReport,
    )
    actor = f"model:{res.profile_name}"
    answered = set()
    for c in res.output.clarifications:
        if not 0 <= c.index < len(items) or c.index in answered:
            continue
        answered.add(c.index)
        it = items[c.index]
        p = it["payload"]
        # A proposal can only resolve flags the requirement actually carries.
        resolves = [f.value for f in c.resolves if f.value in p["quality_flags"]]
        detail = {**c.model_dump(mode="json"), "resolves": resolves,
                  "placeholders": checks.placeholders(c.proposed_text),
                  "problems": checks.clarification_problems(
                      c.proposed_text, p.get("source_quote", ""), sec["text"], resolves)}
        audit.log_event(actor, "clarification_proposed", run_id=run_id,
                        object_type="requirement", object_id=it["item_id"],
                        object_version=it["version"], detail=detail)
    for i, it in enumerate(items):
        if i not in answered:  # model judged the wording testable already; do not ask again
            audit.log_event(actor, "clarification_none", run_id=run_id,
                            object_type="requirement", object_id=it["item_id"],
                            object_version=it["version"])


def clarify(cfg: HarnessConfig, audit: AuditStore, run_id: str, model: str = "generator",
            workers: int = 4) -> StageReport:
    """One model call per section, covering that section's flagged requirements."""
    by_section: dict[str, list[dict]] = {}
    skipped = []
    for it in clarify_candidates(audit, run_id):
        key = f"clarify:{it['item_id']}@v{it['version']}"
        if audit.claim(run_id, key, CODE_ACTOR):
            by_section.setdefault(it["payload"]["section_id"], []).append(it)
        else:
            skipped.append(it["item_id"])
    done, failed = [], {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_clarify_section, cfg, audit, run_id, sid, items, model): sid
                   for sid, items in by_section.items()}
        for fut, sid in futures.items():
            try:
                fut.result()
                done.append(sid)
            except StructuredOutputFailure as e:
                failed[sid] = str(e)
                for it in by_section[sid]:  # allow a retry
                    audit.release(run_id, f"clarify:{it['item_id']}@v{it['version']}",
                                  CODE_ACTOR)
    return StageReport(run_id, done, skipped, failed)


def apply_clarification(audit: AuditStore, item_id: str, actor: str) -> int:
    """Human uses the proposal: new version with the proposed text and the resolved flags
    removed. Refused when the code check found problems or the item moved on."""
    ev = latest_clarification(audit, item_id)
    if ev is None:
        raise ValueError("No clarification proposal for the current version of this item.")
    d = ev["detail"]
    if d["problems"]:
        raise ValueError("Proposal failed the code check: " + "; ".join(d["problems"]))
    p = audit.get_item(item_id)["payload"]
    new = {**p, "text": d["proposed_text"],
           "quality_flags": [f for f in p["quality_flags"] if f not in d["resolves"]],
           "clarification": {"from_event": ev["event_id"], "resolved_flags": d["resolves"],
                             "open_questions": d["open_questions"],
                             "proposed_text": d["proposed_text"]}}
    return audit.edit_item(item_id, new, actor, comment="used clarification proposal",
                           source="clarification")


def open_placeholders(payload: dict) -> list[str]:
    return checks.placeholders(payload.get("text", ""))


def display_id(item_id: str) -> str:
    """REQ-TT-003@run -> REQ-TT-003 for people; the @run suffix keeps IDs unique per run."""
    return item_id.split("@")[0]


def quote_offset(quote: str, text: str) -> list[int] | None:
    """[start, end) of the quote in the section text, ignoring differences in whitespace.
    None if the quote is not there verbatim."""
    import re as _re

    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(_re.escape(w) for w in words)
    m = _re.search(pattern, text, _re.IGNORECASE)
    return [m.start(), m.end()] if m else None


def earlier_override(audit: AuditStore, item: dict) -> dict | None:
    """The latest approval over an AI objection, in another run, of a requirement with the same
    wording. Lets a reviewer reuse their own earlier reason instead of arguing it again."""
    key = checks.normalise(item["payload"].get("text", ""))
    best = None
    for other in audit.items_of_type("requirement"):
        if other["run_id"] == item["run_id"] or checks.normalise(
                other["payload"].get("text", "")) != key:
            continue
        d = audit.latest_decision(other["item_id"])
        if (d and d["action"] == "approved" and (d["detail"] or {}).get("ai_override")
                and (best is None or d["event_id"] > best["event_id"])):
            best = {"event_id": d["event_id"], "by": d["actor"], "run_id": other["run_id"],
                    "reason": d["detail"].get("comment")}
    return best
