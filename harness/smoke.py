"""P0 smoke workflow: proves the skeleton end to end on a tiny synthetic paragraph.

generate (generator role) -> grounding check (code) -> AI review (reviewer role)
-> items stored as 'proposed' -> human approves or rejects in the review UI.
"""

from __future__ import annotations

import json

from harness.audit.store import AuditStore
from harness.config import HarnessConfig
from harness.models.runner import structured_call
from harness.prompts import load_prompt
from harness.schemas.common import ReviewReport
from harness.schemas.smoke import SmokeExtraction

# Synthetic text written for this project. Fictional; not from any OEM or supplier document.
SMOKE_SOURCE = """3.1 Fuel level display
The instrument cluster shall display the fuel level as a bar graph with eight segments. \
When the fuel level falls below 12 percent of tank capacity, the cluster shall illuminate \
the low-fuel telltale within 500 ms. The telltale should be clearly visible. If the fuel \
level signal is missing for more than 2 seconds, the cluster shall show dashes in place of \
the bar graph and log a diagnostic trouble code."""


def normalise(text: str) -> str:
    return " ".join(text.split()).lower()


def is_grounded(quote: str, source: str) -> bool:
    """Code check, not a model judgement: the quote must appear in the source
    (whitespace and case normalised)."""
    return bool(quote.strip()) and normalise(quote) in normalise(source)


def run_smoke(
    cfg: HarnessConfig,
    audit: AuditStore,
    generator: str = "generator",
    reviewer: str | None = "reviewer",
    source: str = SMOKE_SOURCE,
) -> dict:
    cfg = cfg.fresh()  # the smoke test exists to call the model
    run_id = audit.start_run("smoke", note=f"generator={generator} reviewer={reviewer}")

    gen = structured_call(
        cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator,
        task="smoke_extract", prompt_version="smoke_extract_v1",
        system=load_prompt("smoke_extract_v1"),
        user=f"Source text:\n<source>\n{source}\n</source>",
        output_model=SmokeExtraction,
    )

    # the source as a section item, so review-time code checks can compare against it
    audit.add_item(run_id, "section", {"section_id": "SMOKE", "number": None,
                                       "heading": "Smoke source", "text": source},
                   created_by="code:smoke", item_id=f"{run_id}:SMOKE")
    item_ids: list[str] = []
    for n, req in enumerate(gen.output.requirements, start=1):
        payload = req.model_dump(mode="json")
        payload["section_id"] = "SMOKE"
        payload["grounded"] = is_grounded(req.source_quote, source)
        payload["generated_by"] = gen.profile_name
        item_ids.append(audit.add_item(
            run_id, "requirement", payload, created_by=f"model:{gen.profile_name}",
            item_id=f"REQ-SMOKE-{n:03d}",
        ))

    review_summary = None
    if reviewer:
        numbered = "\n".join(
            f"[{i}] {json.dumps(r.model_dump(mode='json'), ensure_ascii=False)}"
            for i, r in enumerate(gen.output.requirements)
        )
        rev = structured_call(
            cfg=cfg, audit=audit, run_id=run_id, role_or_profile=reviewer,
            task="ai_review", prompt_version="ai_review_v1",
            system=load_prompt("ai_review_v1"),
            user=f"Source text:\n<source>\n{source}\n</source>\n\nItems:\n{numbered}",
            output_model=ReviewReport,
            actor=f"ai-reviewer:{cfg.profile(reviewer).name}",
        )
        for r in rev.output.reviews:
            if 0 <= r.index < len(item_ids):
                audit.log_event(
                    f"ai-reviewer:{rev.profile_name}", "ai_reviewed", run_id=run_id,
                    object_type="requirement", object_id=item_ids[r.index], object_version=1,
                    detail=r.model_dump(mode="json"),
                )
        audit.log_event(f"ai-reviewer:{rev.profile_name}", "ai_review_missed", run_id=run_id,
                        detail={"missed": rev.output.missed})
        review_summary = {
            "verdicts": {v: sum(1 for r in rev.output.reviews if r.verdict.value == v)
                         for v in ("accept", "revise", "reject")},
            "missed": rev.output.missed,
        }

    return {
        "run_id": run_id,
        "generator": gen.profile_name,
        "model_served": gen.provider_result.model_served,
        "attempts": gen.attempts,
        "requirements": len(item_ids),
        "ungrounded": [i for i in item_ids if not audit.get_item(i)["payload"]["grounded"]],
        "ai_review": review_summary,
    }
