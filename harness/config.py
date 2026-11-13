"""Loads config.yaml and resolves roles to model profiles."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


class Profile(BaseModel):
    """One model configuration. Extra keys are provider-specific settings."""

    model_config = ConfigDict(extra="allow")

    name: str
    provider: str
    model: str

    def setting(self, key: str, default: Any = None) -> Any:
        return (self.model_extra or {}).get(key, default)


class Knowledge(BaseModel):
    """The project knowledge file as read for one model call."""

    path: str
    text: str
    sha256: str
    lines: int


class HarnessConfig(BaseModel):
    db_path: str
    max_attempts: int = 3
    offline: bool = False  # refuse every provider that sends data off this machine
    # Reuse a stored answer when the same model already answered the same prompt and input.
    replay: bool = False
    # Plain-text house rules, terms and units added to every model call (None = no file).
    knowledge_file: str | None = None
    roles: dict[str, str]
    profiles: dict[str, Profile]

    def knowledge_path(self) -> Path | None:
        if not self.knowledge_file:
            return None
        p = Path(self.knowledge_file)
        return p if p.is_absolute() else PROJECT_ROOT / p

    def knowledge(self) -> Knowledge | None:
        """The knowledge file's current text, or None when it is unset, missing or empty.
        Read on every call so an edit takes effect without a restart."""
        p = self.knowledge_path()
        if p is None or not p.is_file():
            return None
        text = p.read_text(encoding="utf-8").strip()
        if not text:
            return None
        return Knowledge(path=self.knowledge_file or str(p), text=text,
                         sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                         lines=len(text.splitlines()))

    def fresh(self) -> HarnessConfig:
        """Same settings without replay, for anything that must ask the model again
        (stability passes, benchmarks, re-proposals, the smoke test)."""
        return self.model_copy(update={"replay": False})

    def profile(self, name_or_role: str) -> Profile:
        """Accepts a role name (generator, reviewer) or a profile name."""
        name = self.roles.get(name_or_role, name_or_role)
        if name not in self.profiles:
            known = ", ".join(sorted(self.profiles))
            raise KeyError(f"Unknown profile or role '{name_or_role}'. Known profiles: {known}")
        return self.profiles[name]

    def is_offline(self) -> bool:
        return self.offline or os.environ.get("ZYN_OFFLINE", "").strip() in ("1", "true", "yes")

    def resolved_db_path(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


def load_config(path: Path | str = DEFAULT_CONFIG) -> HarnessConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    raw["profiles"] = {n: {"name": n, **p} for n, p in raw.get("profiles", {}).items()}
    # The benchmark pack sets these so every task asks the model afresh with the published
    # prompts, whatever config.yaml says.
    if os.environ.get("ZYN_NO_REPLAY", "").strip() in ("1", "true", "yes"):
        raw["replay"] = False
    if os.environ.get("ZYN_NO_KNOWLEDGE", "").strip() in ("1", "true", "yes"):
        raw["knowledge_file"] = None
    if os.environ.get("ZYN_KNOWLEDGE_FILE", "").strip():  # the pack's knowledge A/B run
        raw["knowledge_file"] = os.environ["ZYN_KNOWLEDGE_FILE"].strip()
    cfg = HarnessConfig.model_validate(raw)
    for role, target in cfg.roles.items():
        if target not in cfg.profiles:
            raise ValueError(f"Role '{role}' points at missing profile '{target}'")
    return cfg
