"""Reviewer learning: proposals drawn from the decisions people made on findings.

Nothing changes until a named person accepts a proposal. Proposals come from code reading the
audit log, not from a model:

- allow_word:   a weak word whose findings people dismissed at least MIN_SAME times and never
                confirmed. Proposal: add it to the rule profile's weak_words_allow.
- check_off:    a code check people overruled in at least 80 percent of at least MIN_CHECK
                decisions. Proposal: switch it off in the rule profile.
- knowledge:    terms in findings dismissed as "Defined elsewhere in the project" at least
                MIN_SAME times. Proposal: list them in the project knowledge file.

Before a person decides, each rule-profile proposal is replayed against every decided
finding: how many dismissed findings it would remove (the gain) and how many confirmed
findings it would also remove (the cost, which should be zero). Knowledge-file proposals
change what the model is told, so they cannot be replayed without model calls; they say so.

Like AskUI's "Dreaming", but over a person's decisions and with a measured effect.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from harness.audit.store import AuditStore
from harness.sift.rules import load_profile, save_profile

MIN_SAME = 3
MIN_CHECK = 8
DEFINED_ELSEWHERE = "Defined elsewhere in the project"


def _decided(audit: AuditStore) -> list[dict]:
    out = []
    for f in audit.items_of_type("finding"):
        d = audit.latest_decision(f["item_id"])
        if d:
            out.append({**f["payload"], "item_id": f["item_id"], "run_id": f["run_id"],
                        "decision": "confirmed" if d["action"] == "approved" else "dismissed",
                        "comment": (d["detail"] or {}).get("comment") or ""})
    return out


def _pid(kind: str, target: str) -> str:
    return f"{kind}:{hashlib.sha256(target.encode()).hexdigest()[:8]}"


def _replay(decided: list[dict], drop) -> dict:
    """Effect of removing every decided finding for which drop(finding) is true."""
    gone = [f for f in decided if drop(f)]
    return {"dismissed_removed": sum(f["decision"] == "dismissed" for f in gone),
            "confirmed_removed": sum(f["decision"] == "confirmed" for f in gone),
            "measured_on": len(decided)}


def proposals(audit: AuditStore, profile: str = "default") -> list[dict]:
    decided = _decided(audit)
    prof = load_profile(profile)
    out = []
    by_word: dict[str, dict] = defaultdict(lambda: {"dismissed": 0, "confirmed": 0, "runs": set()})
    for f in decided:
        if f.get("source") == "code" and f.get("category") == "weak_word":
            w = f["evidence"].lower()
            by_word[w][f["decision"]] += 1
            by_word[w]["runs"].add(f["run_id"])
    for w, n in sorted(by_word.items()):
        if n["dismissed"] >= MIN_SAME and not n["confirmed"] and w not in prof.weak_words_allow:
            out.append({
                "id": _pid("allow_word", w), "kind": "allow_word", "profile": profile,
                "change": {"weak_words_allow": [w]},
                "why": f"'{w}' was dismissed {n['dismissed']} times in {len(n['runs'])} runs "
                       "and never confirmed.",
                "effect": _replay(decided, lambda f, w=w: f.get("category") == "weak_word"
                                  and f.get("source") == "code" and f["evidence"].lower() == w)})
    by_check: dict[str, dict] = defaultdict(lambda: {"dismissed": 0, "confirmed": 0})
    for f in decided:
        if f.get("source") == "code" and f.get("category") in prof.checks:
            by_check[f["category"]][f["decision"]] += 1
    for c, n in sorted(by_check.items()):
        total = n["dismissed"] + n["confirmed"]
        if total >= MIN_CHECK and n["dismissed"] / total >= 0.8:
            out.append({
                "id": _pid("check_off", c), "kind": "check_off", "profile": profile,
                "change": {"checks_off": [c]},
                "why": f"People overruled the '{c}' check in {n['dismissed']} of {total} "
                       "decisions.",
                "effect": _replay(decided, lambda f, c=c: f.get("source") == "code"
                                  and f.get("category") == c)})
    terms: dict[str, int] = defaultdict(int)
    for f in decided:
        if f["decision"] == "dismissed" and DEFINED_ELSEWHERE in f["comment"]:
            terms[f["evidence"].strip()] += 1
    common = sorted(t for t, n in terms.items() if n >= MIN_SAME and len(t) <= 60)
    if common:
        out.append({
            "id": _pid("knowledge", "|".join(common)), "kind": "knowledge",
            "change": {"knowledge_lines": [f"- Defined elsewhere in the project, not a "
                                           f"missing reference: {t}" for t in common]},
            "why": f"Findings on these terms were dismissed as '{DEFINED_ELSEWHERE}' at least "
                   f"{MIN_SAME} times each.",
            "effect": {"not_measured": "This changes what the model is told; compare with "
                                       "`python -m harness pack run` with and without it."}})
    return out


def accept(audit: AuditStore, proposal: dict, actor: str, cfg=None) -> str:
    """Applies one proposal for a named person and records it in the audit log."""
    if not actor.strip():
        raise ValueError("Accepting a proposal needs your name.")
    ch = proposal["change"]
    if proposal["kind"] in ("allow_word", "check_off"):
        if proposal["effect"].get("confirmed_removed"):
            raise ValueError("This change would also remove findings people confirmed; it is "
                             "not applied automatically. Edit the rule profile by hand if you "
                             "still want it.")
        p = load_profile(proposal["profile"])
        p.weak_words_allow = sorted(set(p.weak_words_allow) | set(ch.get("weak_words_allow",
                                                                         [])))
        p.checks = [c for c in p.checks if c not in ch.get("checks_off", [])]
        where = str(save_profile(p))
    else:
        from harness.config import load_config

        cfg = cfg or load_config()
        path = cfg.knowledge_path()
        if path is None:
            raise ValueError("No knowledge_file in config.yaml.")
        old = path.read_text(encoding="utf-8") if path.is_file() else "# Project knowledge\n"
        stamp = datetime.now(UTC).date().isoformat()
        add = f"\n## Learned from review decisions ({stamp}, accepted by {actor})\n" + "\n".join(
            ch["knowledge_lines"]) + "\n"
        path.write_text(old.rstrip("\n") + "\n" + add, encoding="utf-8")
        where = str(path)
    run_id = audit.start_run("rules", note=f"learned proposal {proposal['id']}")
    audit.log_event(actor, "proposal_accepted", run_id=run_id, object_type="learned_proposal",
                    object_id=proposal["id"], detail={**proposal, "applied_to": where})
    return where


def save(props: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(props, indent=1), encoding="utf-8")
    return path
