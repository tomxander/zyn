"""Loads the placeholder subsystem taxonomy and builds an Enum for schema use, so a model
cannot return a subsystem that does not exist."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from harness.config import PROJECT_ROOT

TAXONOMY_PATH = PROJECT_ROOT / "taxonomy_placeholder.yaml"


class Subsystem(BaseModel):
    id: str
    name: str
    scope: str


class Taxonomy(BaseModel):
    label: str
    version: int
    subsystems: list[Subsystem]

    def ids(self) -> list[str]:
        return [s.id for s in self.subsystems]

    def prompt_block(self) -> str:
        return "\n".join(f"- {s.id}: {s.name}. {s.scope}" for s in self.subsystems)


@lru_cache
def load_taxonomy(path: Path | str = TAXONOMY_PATH) -> Taxonomy:
    return Taxonomy.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def subsystem_enum() -> type[Enum]:
    return Enum("SubsystemId", {i: i for i in load_taxonomy().ids()}, type=str)


SubsystemId = subsystem_enum()
