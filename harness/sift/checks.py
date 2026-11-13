"""Deterministic checks that run alongside the model. Code, not model judgement.

The weak-word list is our own working list, not taken from any standard."""

from __future__ import annotations

import re

WEAK_WORDS = [
    "adequate", "adequately", "appropriate", "appropriately", "as appropriate",
    "as soon as possible", "approximately", "clearly", "easy", "easily", "efficient",
    "efficiently", "fast", "flexible", "if possible", "minimal", "minimize", "maximize",
    "normal", "normally", "quick", "quickly", "reasonable", "reasonably", "robust",
    "seamless", "seamlessly", "smooth", "smoothly", "sufficient", "sufficiently",
    "user-friendly", "user friendly", "etc", "and/or", "as required", "where possible",
]
_WEAK = re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(WEAK_WORDS, key=len,
                                                                   reverse=True)) + r")\b",
                   re.IGNORECASE)
_MODAL = re.compile(r"\b(shall|must|will|should|may)\b", re.IGNORECASE)


def normalise(text: str) -> str:
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s*\|\s*", " | ", text)  # table cells: spacing around pipes varies
    return " ".join(text.split()).lower().strip(" |")


def is_grounded(quote: str, source: str) -> bool:
    """The quote must appear in the source (whitespace, case and table spacing normalised)."""
    q = normalise(quote)
    return bool(q) and q in normalise(source)


def weak_words(text: str) -> list[str]:
    return sorted({m.group(1).lower() for m in _WEAK.finditer(text)})


def modal_of(text: str) -> str | None:
    m = _MODAL.search(text)
    return m.group(1).lower() if m else None


def modal_changed(quote: str, text: str) -> bool:
    """True when the source quote uses one modal verb and the rewritten text another
    (e.g. 'should' strengthened to 'shall')."""
    q, t = modal_of(quote), modal_of(text)
    return q is not None and t is not None and q != t


_FLAG_NAMES = ("weak_word", "ambiguous", "not_atomic", "not_testable", "missing_condition",
               "missing_value", "unclear_reference")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_WORD = re.compile(r"[a-z][a-z'-]+")


def suggestion_problems(suggested: str, source_quote: str, section_text: str) -> list[str]:
    """Reasons an AI-suggested requirement text must not be applied with one click.
    The suggestion has to read as a requirement drawn from the section, not as a note."""
    problems = []
    low = suggested.lower()
    if "[" in suggested or "]" in suggested or "flag" in low or any(
            f in low for f in _FLAG_NAMES):
        problems.append("contains reviewer notes or flag names, not just requirement text")
    if modal_changed(source_quote, suggested):
        problems.append(f"changes the modal verb from '{modal_of(source_quote)}' "
                        f"to '{modal_of(suggested)}'")
    src = normalise(section_text)
    new_numbers = sorted(set(_NUMBER.findall(suggested)) - set(_NUMBER.findall(src)))
    if new_numbers:
        problems.append("adds numbers not in the section: " + ", ".join(new_numbers))
    words = [w for w in _WORD.findall(low) if len(w) > 3]
    src_words = set(_WORD.findall(src))
    new_words = [w for w in words if w not in src_words]
    if words and len(new_words) / len(words) > 0.3:
        problems.append("much of the wording is not in the section: " + ", ".join(
            sorted(set(new_words))[:6]))
    return problems


# ---- clarification proposals ------------------------------------------------------------

PLACEHOLDER = re.compile(r"<TBD:[^>]*>")


def placeholders(text: str) -> list[str]:
    return PLACEHOLDER.findall(text)


def clarification_problems(proposed: str, source_quote: str, section_text: str,
                           resolves: list[str]) -> list[str]:
    """Reasons a proposed clarification of flagged source wording must not be used.
    Unlike suggestion_problems, new wording is expected here; invented values are not.
    Missing values must appear as <TBD: ...> placeholders."""
    problems = []
    bare = PLACEHOLDER.sub(" ", proposed)
    low = bare.lower()
    if "[" in bare or "]" in bare or any(f in low for f in _FLAG_NAMES):
        problems.append("contains notes or flag names, not just requirement text")
    if modal_changed(source_quote, proposed):
        problems.append(f"changes the modal verb from '{modal_of(source_quote)}' "
                        f"to '{modal_of(proposed)}'")
    new_numbers = sorted(set(_NUMBER.findall(bare))
                         - set(_NUMBER.findall(normalise(section_text))))
    if new_numbers:
        problems.append("invents values not in the section: " + ", ".join(new_numbers)
                        + " (should be <TBD: ...> placeholders)")
    if not resolves:
        problems.append("claims to resolve none of the requirement's flags")
    if "weak_word" in resolves and weak_words(bare):
        problems.append("still contains weak words: " + ", ".join(weak_words(bare)))
    if "missing_value" in resolves and not placeholders(proposed) and not _NUMBER.search(bare):
        problems.append("claims to resolve missing_value but gives no value or placeholder")
    return problems


def new_numbers(text: str, source: str) -> list[str]:
    """Numbers in the requirement that do not appear in its source text (possible invention)."""
    return sorted(set(_NUMBER.findall(text)) - set(_NUMBER.findall(normalise(source))))
