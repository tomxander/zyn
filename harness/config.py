"""Loads config.yaml and resolves roles to model profiles."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from harness.team.settings import TeamSettings

PACKAGE_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = PACKAGE_DIR.parent
# Files a wheel carries for its first run (config, rules, sample data, the built screen).
# setup.py copies them in at build time; a source folder has none and uses itself.
BUNDLE = PACKAGE_DIR / "_bundle"
# What a new Zyn folder starts with. Never overwritten once present.
SEED_ITEMS = ("config.yaml", ".env.example", "knowledge.example.md",
              "taxonomy_placeholder.yaml", "rules", "data/synthetic")


def _is_source_folder(p: Path) -> bool:
    return (p / "pyproject.toml").is_file() and (p / "config.yaml").is_file()


def resolve_home() -> Path:
    """The Zyn folder: config, rules, sample data, the audit log and exports.

    ZYN_HOME if set; else the source folder when running from a clone; else a folder
    called zyn in the user's home directory (an installed copy)."""
    env = os.environ.get("ZYN_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if _is_source_folder(SOURCE_ROOT):
        return SOURCE_ROOT
    return Path.home() / "zyn"


def seed_source() -> Path | None:
    """Where a new Zyn folder copies its starting files from."""
    if BUNDLE.is_dir():
        return BUNDLE
    return SOURCE_ROOT if _is_source_folder(SOURCE_ROOT) else None


def ensure_home(home: Path) -> list[str]:
    """Fills a new Zyn folder with the starting files it lacks. Returns what was copied."""
    import shutil

    src = seed_source()
    if src is None or src.resolve() == home.resolve():
        return []
    copied = []
    for item in SEED_ITEMS:
        a, b = src / item, home / item
        if not a.exists() or b.exists():
            continue
        b.parent.mkdir(parents=True, exist_ok=True)
        if a.is_dir():
            shutil.copytree(a, b)
        else:
            shutil.copy2(a, b)
        copied.append(item)
    return copied


def web_dist() -> Path:
    """The built review screen: the source folder's web/dist, else the copy in the wheel."""
    for p in (PROJECT_ROOT / "web" / "dist", SOURCE_ROOT / "web" / "dist",
              BUNDLE / "web" / "dist"):
        if (p / "index.html").is_file():
            return p
    return PROJECT_ROOT / "web" / "dist"


PROJECT_ROOT = resolve_home()
if not (PROJECT_ROOT / "config.yaml").is_file():
    _new = ensure_home(PROJECT_ROOT)
    if _new:
        import sys

        # stderr, so the MCP server's stdout stays clean.
        print(f"Zyn: set up a new Zyn folder at {PROJECT_ROOT}", file=sys.stderr)
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
    team: TeamSettings | None = None

    def is_team(self) -> bool:
        return self.team is not None

    def model_allowed(self, profile_name: str) -> bool:
        if self.is_team():
            assert self.team is not None
            return profile_name in self.team.allowed_models
        return True

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
    if cfg.is_team():
        ensure_home(PROJECT_ROOT)
    return cfg
