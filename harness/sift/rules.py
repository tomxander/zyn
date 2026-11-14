"""Rule profiles for Sift Review: which code checks run and how the weak-word list is tuned.

A profile is a small YAML file in rules/ (rules/default.yaml, rules/ears.yaml, or your own).
The profile used, with its hash, is stored with each Sift Review run, so a finding can be
traced to the exact rules that produced it. Profiles change code checks only; the AI
reviewer's prompt is not affected.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from harness.config import PROJECT_ROOT
from harness.sift import checks

RULES_DIR = PROJECT_ROOT / "rules"

CODE_CHECKS = {
    "weak_word": "Vague words from the weak-word list",
    "placeholder": "Open placeholders (TBD, TBC, ??, <...>)",
    "no_modal": "No modal verb (shall, should, must, will, may)",
    "not_atomic": "More than one modal verb",
    "not_ears": "Not in an EARS sentence pattern",
    "duplicate_id": "The same ID used twice",
    "duplicate_text": "The same text under two IDs",
    # only with a source document (checker mode)
    "ungrounded": "No matching sentence in the source document",
    "invented_value": "Numbers not in the matching source sentence or section",
    "modal_changed": "Modal verb differs from the source",
}
DEFAULT_CHECKS = [c for c in CODE_CHECKS if c != "not_ears"]

DEFAULT_WEAK_PHRASES_ALLOW = [
    r"\bcan\s+flexible\s+data[-\s]?rate\b",
    r"\bflexible\s+data[-\s]?rate\b",
    r"\bfast\s+(?:ethernet|charg\w+)\b",
    r"\bquick\s+(?:disconnect|release)\b",
    r"\bas\s+required\s+by\s+(?:iso|iec|sae|un\s+ece|din|ieee)\b\s+(?:[A-Za-z]{1,2}[-\s]?)?\d+[\w.-]*",
]


class RuleProfile(BaseModel):
    name: str
    description: str = ""
    checks: list[str] = Field(default_factory=lambda: list(DEFAULT_CHECKS))
    weak_words_add: list[str] = Field(default_factory=list)    # extra vague words to flag
    weak_words_allow: list[str] = Field(default_factory=list)  # list words to stop flagging
    weak_phrases_allow: list[str] = Field(default_factory=lambda: list(DEFAULT_WEAK_PHRASES_ALLOW))
    custom_checks: list[dict] = Field(default_factory=list)    # accepted house-rule checks

    def model_post_init(self, _ctx) -> None:
        unknown = sorted(set(self.checks) - set(CODE_CHECKS))
        if unknown:
            raise ValueError(f"Rule profile '{self.name}': unknown checks {unknown}. "
                             f"Known: {', '.join(CODE_CHECKS)}")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True)
                              .encode("utf-8")).hexdigest()

    def on(self, check: str) -> bool:
        return check in self.checks

    def weak_words(self, text: str) -> list[str]:
        allow_words = {w.lower() for w in self.weak_words_allow}
        suppressed_spans: list[tuple[int, int]] = []
        for pat_str in self.weak_phrases_allow:
            try:
                for m in re.finditer(pat_str, text, re.IGNORECASE):
                    suppressed_spans.append(m.span())
            except re.error:
                continue

        found: set[str] = set()
        for w, span in checks.find_weak_word_spans(text):
            if any(s <= span[0] and span[1] <= e for s, e in suppressed_spans):
                continue
            if w.lower() not in allow_words:
                found.add(w.lower())

        for w in self.weak_words_add:
            if re.search(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE):
                found.add(w.lower())
        return sorted(found)

    def summary(self) -> dict:
        return {"name": self.name, "description": self.description, "checks": self.checks,
                "weak_words_add": self.weak_words_add,
                "weak_words_allow": self.weak_words_allow,
                "custom_checks": [c.get("name") for c in self.custom_checks],
                "sha256": self.sha256}


def profile_path(name: str, rules_dir: Path | None = None) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError(f"Rule profile names use letters, digits, - and _ only: '{name}'")
    return (rules_dir or RULES_DIR) / f"{name}.yaml"


def load_profile(name: str = "default", rules_dir: Path | None = None) -> RuleProfile:
    p = profile_path(name, rules_dir)
    if not p.is_file():
        if name == "default":
            return RuleProfile(name="default", description="Built-in checks, EARS off")
        known = ", ".join(x["name"] for x in list_profiles(rules_dir)) or "none"
        raise FileNotFoundError(f"No rule profile '{name}' in {p.parent}. Known: {known}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return RuleProfile(**{"name": name, **raw})


def save_profile(profile: RuleProfile, rules_dir: Path | None = None) -> Path:
    p = profile_path(profile.name, rules_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(exclude={"name"})
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


def list_profiles(rules_dir: Path | None = None) -> list[dict]:
    d = rules_dir or RULES_DIR
    names = sorted(p.stem for p in d.glob("*.yaml")) if d.is_dir() else []
    if "default" not in names:
        names.insert(0, "default")
    out = []
    for n in names:
        try:
            out.append({"name": n, "description": load_profile(n, rules_dir).description})
        except (ValueError, yaml.YAMLError) as e:
            out.append({"name": n, "description": f"Cannot be read: {e}", "broken": True})
    return out
