"""Identity principal for team mode and personal mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Principal:
    id: str
    name: str
    email: str | None
    kind: Literal["person", "token", "service", "typed"]
    token_id: str | None = None
