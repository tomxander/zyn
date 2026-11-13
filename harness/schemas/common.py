"""Schemas shared across workflows. Field names are our own placeholders."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReqType(str, Enum):
    functional = "functional"
    performance = "performance"
    interface = "interface"
    safety = "safety"
    security = "security"
    usability = "usability"
    reliability = "reliability"
    constraint = "constraint"
    other = "other"


class DraftRequirement(BaseModel):
    text: str = Field(description="One atomic requirement, keeping the source's own modal verb")
    source_quote: str = Field(
        description="The exact sentence or clause from the source this came from, copied verbatim"
    )
    req_type: ReqType


class Verdict(str, Enum):
    accept = "accept"
    revise = "revise"
    reject = "reject"


class ItemReview(BaseModel):
    index: int = Field(description="0-based index of the item being reviewed")
    verdict: Verdict
    issues: list[str] = Field(description="Concrete problems found; empty if none")
    suggested_text: str | None = Field(description="Corrected text if verdict is revise, else null")
    suggested_req_type: ReqType | None = Field(
        description="Corrected req_type if the type is wrong, else null"
    )


class ReviewReport(BaseModel):
    reviews: list[ItemReview]
    missed: list[str] = Field(
        description="Requirements present in the source that the items failed to capture"
    )
