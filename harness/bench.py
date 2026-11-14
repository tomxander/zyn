"""Benchmark: the same task, the same inputs and the same answer key, on several models.

Tasks:
- map:   map the sections of a spec to subsystems; scored against the key's section list.
- check: Sift Review of a requirement set (code checks + AI batches + conflict pass);
         scored against the key's quality flags.
Each task runs `repeat` times per model. Stability is how much the repeats agree with each
other, which no single run can show. Every run is an ordinary audited run, so any number in
the report can be traced back to the model calls behind it.

Nothing here measures engineering productivity. The answer keys are synthetic and
AI-reviewed; treat the numbers as a comparison of models on this material only.
"""

from __future__ import annotations

import itertools
import json
import os
import statistics
from datetime import datetime
from pathlib import Path

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig
from harness.metrics import model_calls
from harness.models.runner import LOCAL_PROVIDERS, StructuredOutputFailure
from harness.schemas.check import QUALITY_FLAGS
from harness.sift import check, pipeline

SYN = PROJECT_ROOT / "data" / "synthetic"
DEFAULTS = {"spec": SYN / "icx100_srs.md", "set": SYN / "icx100_reqset.csv",
            "key": SYN / "icx100_answer_key.json"}


def available(cfg: HarnessConfig, name: str) -> tuple[bool, str]:
    p = cfg.profile(name)
    if not cfg.model_allowed(name):
        return False, "not allowed by team data rule"
    if cfg.is_offline() and p.provider not in LOCAL_PROVIDERS:
        return False, "offline mode"
    if p.provider == "anthropic":
        ok = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        return ok, "ready" if ok else "no API key"
    if p.provider == "ollama":
        try:
            import ollama

            names = [m.model for m in ollama.Client(
                host=p.setting("host", "http://localhost:11434"), timeout=3).list().models]
        except Exception:  # noqa: BLE001 - any failure means not reachable
            return False, "Ollama not running or not installed"
        if any(n == p.model or n.split(":")[0] == p.model for n in names):
            return True, "ready"
        return False, f"not pulled (ollama pull {p.model})"
    return True, "test provider"


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def _pairwise(sets: list[set]) -> float | None:
    pairs = list(itertools.combinations(sets, 2))
    return round(statistics.mean(_jaccard(a, b) for a, b in pairs), 2) if pairs else None


# ---- tasks ------------------------------------------------------------------------------


def run_map(cfg, audit, profile: str, spec: Path, key: dict) -> dict:
    rep = pipeline.start(cfg, audit, spec, generator=profile)
    maps = audit.list_items(rep.run_id, "section_mapping")
    ok = sum(1 for m in maps if m["payload"]["subsystem_id"] in key["sections"].get(
        m["payload"]["number"] or "_title", []))
    return {"run_id": rep.run_id, "sections": len(maps), "correct": ok,
            "answers": {m["payload"]["number"] or "_title": m["payload"]["subsystem_id"]
                        for m in maps}}


def run_check(cfg, audit, profile: str, reqset: Path, key_path: Path) -> dict:
    run_id = check.start(cfg, audit, reqset).run_id
    rep = check.ai_review(cfg, audit, run_id, reviewer=profile)
    s = check.score(audit, run_id, key_path, ("code", "ai"))
    finds = audit.list_items(run_id, "finding")
    ai = {(f["payload"]["req_id"], f["payload"]["category"]) for f in finds
          if f["payload"]["source"] == "ai"}
    known = json.loads(Path(key_path).read_text(encoding="utf-8")).get("known_spec_issues", [])
    return {"run_id": run_id, "failed_batches": list(rep.failed), "found": s["found"],
            "required": s["required_flags"], "not_in_key": s["flags_not_in_key"],
            "conflicts": sum(1 for f in finds if f["payload"]["category"] == "conflict"),
            "quotes_located": sum(1 for f in finds if f["payload"]["source"] == "ai"
                                  and f["payload"]["evidence_found"]),
            "ai_findings": len(ai), "known_issues_in_key": len(known),
            "answers": sorted(f"{r}:{c}" for r, c in ai if c in QUALITY_FLAGS)}


# ---- the benchmark ----------------------------------------------------------------------


def benchmark(cfg: HarnessConfig, audit: AuditStore, profiles: list[str],
              tasks: tuple[str, ...] = ("map", "check"), repeat: int = 2,
              spec: Path | None = None, reqset: Path | None = None,
              key_path: Path | None = None, out_dir: Path | None = None) -> dict:
    # Every repeat asks the model again, and prompts stay the published ones.
    cfg = cfg.model_copy(update={"replay": False, "knowledge_file": None})
    spec, reqset = spec or DEFAULTS["spec"], reqset or DEFAULTS["set"]
    key_path = key_path or DEFAULTS["key"]
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    started = datetime.now()
    results: dict = {"label": PROTOTYPE_LABEL, "started": started.isoformat(timespec="seconds"),
                     "spec": spec.name, "requirement_set": reqset.name,
                     "key": Path(key_path).name, "repeat": repeat,
                     "notes": "Every repeat asks the model again (no replay). The project "
                              "knowledge file is not used, so prompts match the published "
                              "ones.", "profiles": {}}
    for name in profiles:
        ok, why = available(cfg, name)
        entry: dict = {"model": cfg.profile(name).model, "status": why, "tasks": {}}
        results["profiles"][name] = entry
        if not ok:
            continue
        for task in tasks:
            runs = []
            for _ in range(repeat):
                try:
                    r = (run_map(cfg, audit, name, spec, key) if task == "map"
                         else run_check(cfg, audit, name, reqset, key_path))
                except StructuredOutputFailure as e:
                    r = {"error": str(e)}
                if "run_id" in r:
                    mc = model_calls(audit, r["run_id"], cfg)
                    r.update(cost_usd=mc["cost_usd"], model_seconds=mc["model_seconds"],
                             calls=mc["calls"], schema_retries=mc["schema_retries"])
                runs.append(r)
            entry["tasks"][task] = {"runs": runs, **_summary(task, runs)}
    out = out_dir or PROJECT_ROOT / "runs" / "bench" / started.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(results), encoding="utf-8")
    results["files"] = {"json": str(out / "report.json"), "md": str(out / "report.md")}
    return results


def _summary(task: str, runs: list[dict]) -> dict:
    good = [r for r in runs if "error" not in r]
    if not good:
        return {"errors": len(runs)}
    s = {"errors": len(runs) - len(good),
         "cost_usd_mean": round(statistics.mean(r["cost_usd"] for r in good), 4),
         "seconds_mean": round(statistics.mean(r["model_seconds"] for r in good), 1)}
    if task == "map":
        s["correct_mean"] = round(statistics.mean(r["correct"] for r in good), 1)
        s["of"] = good[0]["sections"]
        s["stability"] = _pairwise([set(r["answers"].items()) for r in good])
    else:
        s["found_mean"] = round(statistics.mean(r["found"] for r in good), 1)
        s["of"] = good[0]["required"]
        s["not_in_key_mean"] = round(statistics.mean(r["not_in_key"] for r in good), 1)
        s["conflicts_mean"] = round(statistics.mean(r["conflicts"] for r in good), 1)
        s["quotes_located"] = f"{sum(r['quotes_located'] for r in good)}/" \
                              f"{sum(r['ai_findings'] for r in good)}"
        s["stability"] = _pairwise([set(r["answers"]) for r in good])
    return s


def render_markdown(res: dict) -> str:
    lines = [f"# Zyn benchmark, {res['started']}", "",
             (f"{res['label']} Synthetic inputs ({res['spec']}, {res['requirement_set']}), "
             f"answer key {res['key']} (author-made, AI-reviewed, not engineer-reviewed). "
             f"Each task run {res['repeat']} times per model. Stability is the mean pairwise "
             "overlap between repeats (1.0 = identical answers). Cost uses the prices in "
             "config.yaml. Not a productivity measure."),
             "", res.get("notes", ""), ""]
    lines += ["## Section mapping", "",
              "| Model | Correct | Stability | Cost per run (USD) | Model time (s) | Errors |",
              "|---|---|---|---|---|---|"]
    for name, e in res["profiles"].items():
        t = e["tasks"].get("map")
        if not t:
            lines.append(f"| {name} | {e['status']} | | | | |")
        elif "of" in t:
            lines.append(f"| {name} | {t['correct_mean']} of {t['of']} | {t['stability']} | "
                         f"{t['cost_usd_mean']} | {t['seconds_mean']} | {t['errors']} |")
        else:
            lines.append(f"| {name} | failed | | | | {t['errors']} |")
    lines += ["", "## Sift Review of the requirement set", "",
              ("| Model | Expected flags found | Flags not in key | Conflicts | Quotes located "
              "| Stability | Cost per run (USD) | Model time (s) | Errors |"),
              "|---|---|---|---|---|---|---|---|---|"]
    for name, e in res["profiles"].items():
        t = e["tasks"].get("check")
        if not t:
            lines.append(f"| {name} | {e['status']} | | | | | | | |")
        elif "of" in t:
            lines.append(f"| {name} | {t['found_mean']} of {t['of']} | {t['not_in_key_mean']} | "
                         f"{t['conflicts_mean']} | {t['quotes_located']} | {t['stability']} | "
                         f"{t['cost_usd_mean']} | {t['seconds_mean']} | {t['errors']} |")
        else:
            lines.append(f"| {name} | failed | | | | | | | {t['errors']} |")
    lines += ["", "Run IDs (open any of them in the review screen):", ""]
    for name, e in res["profiles"].items():
        for task, t in e["tasks"].items():
            ids = [r.get("run_id", "error") for r in t["runs"]]
            lines.append(f"- {name} / {task}: {', '.join(ids)}")
    return "\n".join(lines) + "\n"
