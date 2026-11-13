"""Versioned prompt files. A prompt's file name is its version; never edit a
released prompt in place, add a _v2 file instead so audit hashes stay meaningful."""

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
