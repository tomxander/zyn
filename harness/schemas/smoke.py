from __future__ import annotations

from pydantic import BaseModel

from harness.schemas.common import DraftRequirement


class SmokeExtraction(BaseModel):
    requirements: list[DraftRequirement]
