"""The Zyn benchmark pack: one versioned set of tasks, any model, comparable results.

Five tasks on data Zyn did not author (QuRE, PROMISE, RTEMS) and on the synthetic ICX-100
spec (author-made, AI-reviewed). For each model and task the pack reports, over N repeats:
- the task's primary score (mean, lowest, highest)
- run-to-run spread of that score, and item-level agreement where the task has items
- cost per correct item (USD spent / items scored correct), from the audit log

Every repeat asks the model again (no replay) with the published prompts (no project
knowledge file). The manifest pins each data file by sha256, so a result can be tied to the
exact inputs. `export` writes the tasks as plain JSONL (Inspect AI sample format: id, input,
target, metadata) and promptfoo test CSVs (vars plus __expected), so others can run them in
their own harness.

Run:     python -m harness pack run --profiles claude-sonnet,claude-haiku --repeat 3
List:    python -m harness pack manifest
Export:  python -m harness pack export
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from harness import PROTOTYPE_LABEL
from harness.config import PROJECT_ROOT

PACK_VERSION = "zyn-bench-1.1"  # 1.1 adds rtems-whole; 1.0 tasks unchanged
DATA = PROJECT_ROOT / "data"
OUT = PROJECT_ROOT / "runs" / "pack"

TASKS: dict[str, dict] = {
    "icx-map": {
        "title": "ICX-100 section mapping",
        "what": "Map each section of a synthetic cluster spec to a subsystem.",
        "score": "accuracy: sections mapped to an accepted subsystem / sections",
        "files": ["synthetic/icx100_srs.md", "synthetic/icx100_answer_key.json"],
        "data_note": "Author-made, AI-reviewed, not engineer-reviewed.",
    },
    "icx-review": {
        "title": "ICX-100 requirement review",
        "what": "Flag quality problems in 46 requirements (Sift Review, code and AI).",
        "score": "recall: expected flags found / expected flags; flags not in the key reported",
        "files": ["synthetic/icx100_reqset.csv", "synthetic/icx100_answer_key.json"],
        "data_note": "Author-made, AI-reviewed, not engineer-reviewed.",
    },
    "qure-flags": {
        "title": "QuRE defect flags",
        "what": "200 industrial automotive requirements: find weak words humans labelled as "
                "defects.",
        "score": "F1 on defect-labelled weak words",
        "files": ["public/qure/sample_200_42.csv", "public/qure/sample_200_42.gold.json"],
        "data_note": "QuRE 1.0.1 (Zenodo 16049822, CC BY 4.0); human labels.",
    },
    "promise-type": {
        "title": "PROMISE requirement type",
        "what": "625 requirements: functional or non-functional, and the coarse class.",
        "score": "binary accuracy (functional vs non-functional)",
        "files": ["public/promise/nfr.arff"],
        "data_note": "PROMISE NFR dataset; human labels.",
    },
    "rtems-extract": {
        "title": "RTEMS requirement extraction",
        "what": "Extract 'shall' statements from RTEMS behaviour sections with verbatim "
                "quotes.",
        "score": "recall: gold statements matched / gold statements",
        "files": ["public/rtems/rendered.md"],
        "data_note": "Rendered from RTEMS rtems-central spec files (BSD-2-Clause / CC BY-SA).",
    },
    "rtems-whole": {
        "title": "RTEMS extraction, whole components",
        "what": "Extract 'shall' statements from whole RTEMS components, where the "
                "introduction and 'While ...' conditions must not be extracted.",
        "score": "F1: matched gold statements against everything extracted (recall and "
                 "precision)",
        "files": ["public/rtems/rendered.md"],
        "data_note": "Rendered from RTEMS rtems-central spec files (BSD-2-Clause / CC BY-SA).",
    },
}


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def manifest() -> dict:
    tasks = {}
    for tid, t in TASKS.items():
        files = {f: _sha(DATA / f) for f in t["files"]}
        tasks[tid] = {**t, "files": files, "ready": all(files.values())}
    return {"pack": PACK_VERSION, "label": PROTOTYPE_LABEL, "tasks": tasks,
            "rules": ["every repeat asks the model again (no replay)",
                      "published prompts only (no project knowledge file)",
                      "cost from the prices in config.yaml",
                      "scores describe these datasets, not general quality"]}


@contextmanager
def _clean_env(knowledge: Path | None = None):
    """No replay, and no knowledge file unless one is given for an A/B run, for anything
    run inside, including evals that load their own config."""
    keys = ("ZYN_NO_REPLAY", "ZYN_NO_KNOWLEDGE", "ZYN_KNOWLEDGE_FILE")
    old = {k: os.environ.get(k) for k in keys}
    os.environ["ZYN_NO_REPLAY"] = "1"
    if knowledge:
        os.environ.pop("ZYN_NO_KNOWLEDGE", None)
        os.environ["ZYN_KNOWLEDGE_FILE"] = str(Path(knowledge).resolve())
    else:
        os.environ["ZYN_NO_KNOWLEDGE"] = "1"
        os.environ.pop("ZYN_KNOWLEDGE_FILE", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---- one repeat of one task for one model: {score, correct, cost_usd, answers?} -----------


def _icx_map(profile: str) -> dict:
    from harness.audit.store import AuditStore
    from harness.bench import run_map
    from harness.config import load_config
    from harness.metrics import model_calls

    cfg = load_config()
    audit = AuditStore(cfg.resolved_db_path())
    key = json.loads((DATA / "synthetic/icx100_answer_key.json").read_text(encoding="utf-8"))
    r = run_map(cfg, audit, profile, DATA / "synthetic/icx100_srs.md", key)
    return {"score": r["correct"] / r["sections"] if r["sections"] else 0.0,
            "correct": r["correct"], "cost_usd": model_calls(audit, r["run_id"], cfg)[
                "cost_usd"], "answers": [f"{k}:{v}" for k, v in r["answers"].items()],
            "run_id": r["run_id"]}


def _icx_review(profile: str) -> dict:
    from harness.audit.store import AuditStore
    from harness.bench import run_check
    from harness.config import load_config
    from harness.metrics import model_calls

    cfg = load_config()
    audit = AuditStore(cfg.resolved_db_path())
    r = run_check(cfg, audit, profile, DATA / "synthetic/icx100_reqset.csv",
                  DATA / "synthetic/icx100_answer_key.json")
    return {"score": r["found"] / r["required"] if r["required"] else 0.0,
            "correct": r["found"], "not_in_key": r["not_in_key"],
            "cost_usd": model_calls(audit, r["run_id"], cfg)["cost_usd"],
            "answers": r["answers"], "run_id": r["run_id"]}


def _qure(profile: str) -> dict:
    from evals import qure

    p = qure.run([profile], 200, 42)["profiles"][profile]
    d = p["scores"]["code+ai"]  # Sift Review as a person would run it: code checks and AI
    return {"score": d["f1"], "correct": d["tp"], "cost_usd": p["cost_usd"],
            "run_id": p["run_id"]}


def _promise(profile: str) -> dict:
    from evals import promise

    p = promise.run([profile])["profiles"][profile]
    b = p["scores"]["binary"]
    return {"score": b["accuracy"], "correct": round(b["accuracy"] * p["scores"]["answered"]),
            "cost_usd": p["cost_usd"], "run_id": p["run_id"]}


def _rtems(profile: str) -> dict:
    from evals import rtems

    p = rtems.run([profile])["profiles"][profile]
    return {"score": p["recall"] or 0.0, "correct": p["matched"], "cost_usd": p["cost_usd"],
            "quotes_verbatim": p["quotes_verbatim"], "run_id": p["run_id"]}


def _rtems_whole(profile: str) -> dict:
    from evals import rtems

    p = rtems.run([profile], whole=True)["profiles"][profile]
    rec = p["recall"] or 0.0
    prec = p["matched"] / p["extracted"] if p["extracted"] else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"score": round(f1, 3), "correct": p["matched"], "cost_usd": p["cost_usd"],
            "recall": rec, "precision": round(prec, 3), "extra": p["extra"],
            "run_id": p["run_id"]}


RUNNERS: dict[str, Callable[[str], dict]] = {
    "icx-map": _icx_map, "icx-review": _icx_review, "qure-flags": _qure,
    "promise-type": _promise, "rtems-extract": _rtems, "rtems-whole": _rtems_whole}


def _agreement(answer_sets: list[set]) -> float | None:
    from harness.bench import _pairwise

    return _pairwise(answer_sets) if len(answer_sets) > 1 else None


def summarise(repeats: list[dict]) -> dict:
    good = [r for r in repeats if "error" not in r]
    if not good:
        return {"repeats": len(repeats), "errors": len(repeats)}
    scores = [r["score"] for r in good]
    cost = sum(r["cost_usd"] or 0 for r in good)
    correct = sum(r["correct"] for r in good)
    out = {"repeats": len(repeats), "errors": len(repeats) - len(good),
           "score_mean": round(statistics.mean(scores), 3),
           "score_min": round(min(scores), 3), "score_max": round(max(scores), 3),
           "score_spread": round(max(scores) - min(scores), 3),
           "cost_usd": round(cost, 4),
           "cost_per_correct_usd": round(cost / correct, 5) if correct else None}
    if all("answers" in r for r in good):
        out["item_agreement"] = _agreement([set(r["answers"]) for r in good])
    return out


def run_pack(profiles: list[str], tasks: list[str] | None = None, repeat: int = 3,
             runners: dict[str, Callable[[str], dict]] | None = None,
             out_dir: Path | None = None, knowledge: Path | None = None) -> dict:
    runners = runners or RUNNERS
    man = manifest()
    tasks = tasks or [t for t, v in man["tasks"].items() if v["ready"]]
    unknown = sorted(set(tasks) - set(TASKS))
    if unknown:
        raise ValueError(f"Unknown tasks {unknown}. Known: {', '.join(TASKS)}")
    res = {"pack": PACK_VERSION, "label": PROTOTYPE_LABEL,
           "started": datetime.now().isoformat(timespec="seconds"), "repeat": repeat,
           "manifest": man, "results": {}}
    if knowledge:
        k = Path(knowledge)
        res["knowledge"] = {"file": k.name, "sha256": _sha(k)}
        man = {**man, "rules": [r if "knowledge" not in r else
                                f"project knowledge file {k.name} added to every call (A/B run)"
                                for r in man["rules"]]}
        res["manifest"] = man
    with _clean_env(knowledge):
        for prof in profiles:
            res["results"][prof] = {}
            for t in tasks:
                reps = []
                for _ in range(repeat):
                    try:
                        reps.append(runners[t](prof))
                    except Exception as e:  # noqa: BLE001  (record and go on)
                        reps.append({"error": f"{type(e).__name__}: {e}"})
                res["results"][prof][t] = {"repeats": reps, **summarise(reps)}
    out = out_dir or OUT / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (out / "results.md").write_text(markdown(res), encoding="utf-8")
    res["files"] = {"json": str(out / "results.json"), "md": str(out / "results.md")}
    return res


def markdown(res: dict) -> str:
    man = res["manifest"]
    lines = [f"# Zyn benchmark pack {res['pack']}, {res['started']}", "",
             f"{res['label']} {res['repeat']} repeats per model and task. "
             + "; ".join(man["rules"]) + ".", "",
             ("| Model | Task | Score (mean) | Lowest | Highest | Item agreement | "
             "Cost per correct item (USD) | Errors |"), "|---|---|---|---|---|---|---|---|"]
    for prof, tasks in res["results"].items():
        for t, s in tasks.items():
            lines.append(f"| {prof} | {TASKS[t]['title']} | {s.get('score_mean', '-')} | "
                         f"{s.get('score_min', '-')} | {s.get('score_max', '-')} | "
                         f"{s.get('item_agreement') if s.get('item_agreement') is not None else '-'}"
                         f" | {s.get('cost_per_correct_usd', '-')} | {s.get('errors', 0)} |")
    lines += ["", "## Tasks", ""]
    for t, v in man["tasks"].items():
        lines.append(f"- **{v['title']}** ({t}): {v['what']} Score: {v['score']}. "
                     f"{v['data_note']}")
    lines += ["", "## Data files (sha256)", ""]
    for v in man["tasks"].values():
        for f, h in v["files"].items():
            lines.append(f"- `{f}`: {h or 'missing'}")
    return "\n".join(lines) + "\n"


# ---- export for other harnesses ----------------------------------------------------------


def _items(task: str) -> list[dict]:
    """[{id, input, target, metadata}] for one task, from local data only."""
    if task == "promise-type":
        from evals.promise import PROMISE_COARSE, load

        return [{"id": r["id"], "input": r["text"],
                 "target": "functional" if r["label"] == "F" else "non-functional",
                 "metadata": {"label": r["label"], "coarse": PROMISE_COARSE[r["label"]]}}
                for r in load()]
    if task == "qure-flags":
        gold = json.loads((DATA / "public/qure/sample_200_42.gold.json").read_text(
            encoding="utf-8"))
        rows = list(csv.DictReader((DATA / "public/qure/sample_200_42.csv").open(
            encoding="utf-8")))
        return [{"id": r["ID"], "input": r["Requirement"],
                 "target": ", ".join(sorted({g["weak_word"] for g in gold[r["ID"]]
                                             if g["label"] == "defect"})) or "none",
                 "metadata": {"labels": gold[r["ID"]]}} for r in rows]
    key = json.loads((DATA / "synthetic/icx100_answer_key.json").read_text(encoding="utf-8"))
    if task == "icx-review":
        return [{"id": g["gold_id"], "input": g["text"],
                 "target": ", ".join(g["flags"]) or "none",
                 "metadata": {"acceptable_flags": g["acceptable_flags"],
                              "data_note": TASKS[task]["data_note"]}}
                for g in key["requirements"]]
    if task == "icx-map":
        from harness.sift.ingest import load_document

        doc = load_document(DATA / "synthetic/icx100_srs.md")
        return [{"id": s.number or "_title",
                 "input": f"{s.number or ''} {s.heading}".strip() + f"\n{s.text}",
                 "target": " | ".join(key["sections"].get(s.number or "_title", [])),
                 "metadata": {"accepted": key["sections"].get(s.number or "_title", [])}}
                for s in doc.sections if (s.number or "_title") in key["sections"]]
    if task == "rtems-extract":
        from evals.rtems import render
        from harness.sift.ingest import split_sections

        doc, gold = render()
        _title, sections = split_sections(doc)
        out = []
        for s in sections:
            if s.heading != "Required behaviour":
                continue
            stmts = [g["text"] for g in gold if g["section"] == s.number]
            out.append({"id": s.number, "input": s.text, "target": "\n".join(stmts),
                        "metadata": {"statements": len(stmts)}})
        return out
    raise ValueError(f"Unknown task {task}")


def export(out_dir: Path | None = None, tasks: list[str] | None = None) -> dict:
    out = out_dir or OUT / f"export-{PACK_VERSION}"
    (out / "inspect").mkdir(parents=True, exist_ok=True)
    (out / "promptfoo").mkdir(parents=True, exist_ok=True)
    man = manifest()
    written = {}
    for t in tasks or [k for k, v in man["tasks"].items() if v["ready"]]:
        items = _items(t)
        with (out / "inspect" / f"{t}.jsonl").open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        with (out / "promptfoo" / f"{t}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "input", "__expected"])
            for it in items:
                w.writerow([it["id"], it["input"], it["target"]])
        written[t] = len(items)
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    (out / "README.md").write_text(
        f"# Zyn benchmark pack {PACK_VERSION}\n\n{PROTOTYPE_LABEL}\n\n"
        "inspect/<task>.jsonl: Inspect AI samples (id, input, target, metadata).\n"
        "promptfoo/<task>.csv: promptfoo tests (vars id and input; __expected holds the "
        "target; pick the assertion type that fits the task, e.g. icontains or "
        "similar).\n\nTargets are the answer keys Zyn scores against. For tasks with lists "
        "(flags, statements) exact string match is too strict; score them the way Zyn does "
        "(see harness/pack.py and evals/).\n\n"
        + "\n".join(f"- {TASKS[t]['title']} ({t}): {n} items. {TASKS[t]['data_note']}"
                    for t, n in written.items()) + "\n", encoding="utf-8")
    return {"dir": str(out), "tasks": written}
