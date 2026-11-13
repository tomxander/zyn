"""Custom checks: a team's house rules as deterministic regular-expression checks.

A rule is described in plain words. The model drafts a check (a `when` filter and a
`must_match` or `must_not_match` expression) plus examples it should pass and flag; code then
compiles it, runs it on those examples and on a requirement set, and shows every hit. A named
person accepts it into a rule profile. From then on it runs as code, with no model involved.

Run:  python -m harness rules draft "Every timing requirement states its unit" --set FILE
      python -m harness rules accept timing_has_unit --into default --as "Tom"
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from harness.sift.rules import RULES_DIR, load_profile, save_profile

PROMPT = "custom_check_v1"
PROPOSALS = RULES_DIR / "proposals"


class CheckDraft(BaseModel):
    name: str
    description: str
    when: str | None
    must_match: str | None
    must_not_match: str | None
    explanation: str
    question: str
    examples_pass: list[str]
    examples_fail: list[str]


def compile_check(c: dict) -> list[str]:
    """Problems that stop a check from running; empty means it can run."""
    problems = []
    if bool(c.get("must_match")) == bool(c.get("must_not_match")):
        problems.append("set exactly one of must_match and must_not_match")
    for k in ("when", "must_match", "must_not_match"):
        if c.get(k):
            try:
                re.compile(c[k])
            except re.error as e:
                problems.append(f"{k} is not a valid regular expression: {e}")
    return problems


def run_check(c: dict, text: str) -> str | None:
    """The evidence for a finding on this text, or None when the text passes."""
    flags = re.IGNORECASE
    if c.get("when") and not re.search(c["when"], text, flags):
        return None
    if c.get("must_not_match"):
        m = re.search(c["must_not_match"], text, flags)
        return m.group(0) if m else None
    if c.get("must_match") and not re.search(c["must_match"], text, flags):
        w = re.search(c["when"], text, flags) if c.get("when") else None
        return w.group(0) if w else " ".join(text.split()[:6])
    return None


def findings(checks: list[dict], reqs: list[dict]) -> list[dict]:
    out = []
    for c in checks:
        if compile_check(c):
            continue
        for r in reqs:
            ev = run_check(c, r["text"])
            if ev is not None:
                out.append({"req_id": r["ext_id"], "category": f"custom:{c['name']}",
                            "evidence": ev, "explanation": c["explanation"],
                            "question_for_author": c["question"], "related_ids": []})
    return out


def trial(c: dict, reqs: list[dict]) -> dict:
    """What a check does on its own examples and on a set, for the person deciding."""
    problems = compile_check(c)
    if problems:
        return {"problems": problems}
    wrong_pass = [e for e in c.get("examples_pass", []) if run_check(c, e) is not None]
    wrong_fail = [e for e in c.get("examples_fail", []) if run_check(c, e) is None]
    hits = [{"id": r["ext_id"], "text": r["text"], "evidence": run_check(c, r["text"])}
            for r in reqs if run_check(c, r["text"]) is not None]
    return {"problems": [], "examples_ok": not wrong_pass and not wrong_fail,
            "flagged_but_should_pass": wrong_pass, "passed_but_should_flag": wrong_fail,
            "hits": hits, "hit_rate": f"{len(hits)} of {len(reqs)}"}


def draft(cfg, audit, description: str, reqs: list[dict], generator: str = "generator") -> dict:
    """Model drafts a check; code tries it; the proposal is saved for a person to accept."""
    from harness.models.runner import structured_call
    from harness.prompts import load_prompt

    run_id = audit.start_run("rules", note=f"custom check: {description[:80]}")
    res = structured_call(cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator,
                          task="custom_check", prompt_version=PROMPT,
                          system=load_prompt(PROMPT), user=f"Rule: {description}",
                          output_model=CheckDraft)
    c = res.output.model_dump()
    c["name"] = re.sub(r"[^a-z0-9_]+", "_", c["name"].lower()).strip("_")[:40] or "custom_check"
    t = trial(c, reqs)
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    path = PROPOSALS / f"{c['name']}.yaml"
    path.write_text(yaml.safe_dump({**c, "drafted_by": res.profile_name,
                                    "drafted_in_run": run_id, "trial": t}, sort_keys=False,
                                   allow_unicode=True), encoding="utf-8")
    audit.log_event(f"model:{res.profile_name}", "check_drafted", run_id=run_id,
                    object_type="custom_check", object_id=c["name"],
                    detail={"check": c, "trial": t, "file": str(path)})
    return {"run_id": run_id, "check": c, "trial": t, "file": str(path)}


def accept(name: str, profile: str, actor: str, rules_dir: Path | None = None) -> Path:
    """A named person adds a drafted check to a rule profile. Refuses a check that does not
    compile or that fails its own examples."""
    if not actor.strip():
        raise ValueError("Accepting a check needs your name.")
    base = rules_dir or RULES_DIR
    src = base / "proposals" / f"{name}.yaml"
    if not src.is_file():
        raise FileNotFoundError(f"No proposal {src}")
    c = yaml.safe_load(src.read_text(encoding="utf-8"))
    t = trial(c, [])
    if t["problems"] or not t["examples_ok"]:
        raise ValueError(f"Check {name} does not behave as its examples say: {t}")
    p = load_profile(profile, rules_dir)
    keep = {k: c[k] for k in ("name", "description", "when", "must_match", "must_not_match",
                              "explanation", "question", "examples_pass", "examples_fail")}
    keep.update(accepted_by=actor, accepted_at=datetime.now(UTC).isoformat(timespec="seconds"),
                drafted_by=c.get("drafted_by"))
    p.custom_checks = [x for x in p.custom_checks if x.get("name") != name] + [keep]
    return save_profile(p, rules_dir)
