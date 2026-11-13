"""Sift Review schemas: findings on an existing requirement set. Field names are our own."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FindingCategory(str, Enum):
    # same meanings as the extraction quality flags, so results can be scored against a key
    weak_word = "weak_word"
    ambiguous = "ambiguous"
    not_atomic = "not_atomic"
    not_testable = "not_testable"
    missing_condition = "missing_condition"
    missing_value = "missing_value"
    unclear_reference = "unclear_reference"
    # set-level problems
    conflict = "conflict"
    duplicate = "duplicate"


# categories only code produces
CODE_ONLY = ["no_modal", "placeholder", "duplicate_id", "duplicate_text", "not_ears"]
QUALITY_FLAGS = ["weak_word", "ambiguous", "not_atomic", "not_testable", "missing_condition",
                 "missing_value", "unclear_reference"]


class AiFinding(BaseModel):
    req_id: str = Field(description="The ID of the requirement, exactly as given in the input")
    category: FindingCategory
    evidence: str = Field(
        description="The exact words from that requirement's text that the problem is about, "
                    "copied character for character. Never paraphrase.")
    explanation: str = Field(description="One sentence: what is wrong and why it matters")
    question_for_author: str = Field(
        description="The question the author must answer to fix it. Never propose values.")
    related_ids: list[str] = Field(
        description="Other requirement IDs involved (conflict or duplicate), else empty")


class SetReviewResult(BaseModel):
    findings: list[AiFinding]
