"""Sift schemas. Field names are our own placeholders."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from harness.schemas.common import ReqType, Verdict
from harness.taxonomy import SubsystemId


class Modal(str, Enum):
    shall = "shall"
    must = "must"
    will = "will"
    should = "should"
    may = "may"
    none = "none"


class VerificationMethod(str, Enum):
    test = "test"
    analysis = "analysis"
    inspection = "inspection"
    demonstration = "demonstration"


class QualityFlag(str, Enum):
    weak_word = "weak_word"
    ambiguous = "ambiguous"
    not_atomic = "not_atomic"
    not_testable = "not_testable"
    missing_condition = "missing_condition"
    missing_value = "missing_value"
    unclear_reference = "unclear_reference"


class AsilHint(str, Enum):
    none = "none"
    QM = "QM"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    unknown = "unknown"


# ---- section mapping -----------------------------------------------------------


class SectionMapping(BaseModel):
    section_id: str = Field(description="The section_id exactly as given in the input")
    subsystem_id: SubsystemId
    confidence: float = Field(ge=0, le=1, description="0 to 1")
    rationale: str = Field(description="One sentence: why this subsystem")


class MappingResult(BaseModel):
    mappings: list[SectionMapping]


# ---- extraction + classification ----------------------------------------------


class ExtractedRequirement(BaseModel):
    text: str = Field(description="One atomic requirement, keeping the source's own modal verb")
    source_quote: str = Field(description="Exact source sentence or clause, copied verbatim")
    req_type: ReqType
    modal: Modal = Field(description="The modal verb used in the SOURCE for this requirement")
    verification_method: VerificationMethod
    quality_flags: list[QualityFlag] = Field(description="Problems with the source wording")
    asil_hint: AsilHint = Field(
        description="Suggestion only, not a safety assessment. 'none' if not safety related"
    )


class ExtractionResult(BaseModel):
    requirements: list[ExtractedRequirement]


# ---- AI review v3 ---------------------------------------------------------------------


class ObjectionScope(str, Enum):
    none = "none"      # verdict accept
    text = "text"      # the requirement text, modal or meaning is wrong
    labels = "labels"  # text is right; only type, flags, verification, ASIL hint or quote


class ItemReviewV3(BaseModel):
    index: int = Field(description="0-based index of the item being reviewed")
    verdict: Verdict
    objection_scope: ObjectionScope = Field(
        description="none if accept; text if the requirement wording or meaning must change; "
                    "labels if the wording is right and only classification fields are wrong")
    issues: list[str] = Field(description="Concrete problems found; empty if none")
    suggested_text: str | None = Field(
        description="Only when objection_scope is text: the corrected requirement sentence and "
                    "nothing else. Never notes, brackets or flag names. Otherwise null")
    suggested_req_type: ReqType | None = Field(description="Corrected req_type, else null")
    suggested_flags: list[QualityFlag] | None = Field(
        description="The complete corrected quality_flags list if the flags are wrong, else null")


class ReviewReportV3(BaseModel):
    reviews: list[ItemReviewV3]
    missed: list[str] = Field(
        description="Requirements present in the source that the items failed to capture")


# ---- clarification proposals (fixes for flagged SOURCE wording) -----------------------


class Clarification(BaseModel):
    index: int = Field(description="0-based index of the item being clarified")
    proposed_text: str = Field(
        description="The requirement rewritten so the flagged problems are gone. Same modal "
                    "verb as the source. Any value, limit or condition the source does not "
                    "give is written as a placeholder <TBD: what is needed>, never invented")
    resolves: list[QualityFlag] = Field(
        description="The item's flags this rewrite removes, once placeholders are filled")
    open_questions: list[str] = Field(
        description="One question to the spec author per placeholder or decision needed")
    rationale: str = Field(description="One sentence: what was unclear and how this fixes it")


class ClarificationReport(BaseModel):
    clarifications: list[Clarification]
