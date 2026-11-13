"""E1: Sift Review quality flags against human review labels (QuRE).

QuRE 1.0.1 (Femmer, Houdek, Unterbusch et al., Zenodo record 16049822, CC BY 4.0): 2,111
requirements from automotive industrial specifications. Each row is one weak word in one
requirement, labelled by a human as a quality defect or acceptable ("ok") in context.

What is scored: for each labelled weak word, did Sift Review report a finding that quotes
it? "Flagged" is compared with "defect". Precision, recall and F1 for the defect class, for
the code checks, the AI reviewer, both, and a baseline that flags every weak word.
Requirements are sampled by unique requirement (fixed seed), not by row.

Run from the project root:
  python -m evals.qure prepare --n 200 --seed 42
  python -m evals.qure run --profiles claude-opus,claude-sonnet --n 200 --seed 42
The QuRE file is not redistributed; download it to data/public/qure/QuRE.csv first.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from harness.audit.store import AuditStore
from harness.config import load_config
from harness.metrics import model_calls
from harness.sift import check

SRC = ROOT / "data" / "public" / "qure" / "QuRE.csv"
ATTRIBUTION = ("QuRE 1.0.1, Femmer, Houdek, Unterbusch et al., Zenodo record 16049822, "
               "CC BY 4.0. Used unmodified; sampled for evaluation.")


def load() -> dict[str, list[dict]]:
    by_req: dict[str, list[dict]] = defaultdict(list)
    for r in csv.DictReader(SRC.open(encoding="utf-8")):
        by_req[r["requirement"]].append(r)
    return by_req


def prepare(n: int, seed: int) -> Path:
    by_req = load()
    texts = sorted(by_req)
    random.Random(seed).shuffle(texts)
    pick = texts[:n]
    out = ROOT / "data" / "public" / "qure" / f"sample_{n}_{seed}.csv"
    gold = {}
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Requirement"])
        for t in pick:
            rid = f"Q{by_req[t][0]['id']}"
            w.writerow([rid, t])
            gold[rid] = [{"weak_word": r["weak_word"], "label": r["defect"]} for r in by_req[t]]
    out.with_suffix(".gold.json").write_text(json.dumps(gold, indent=1), encoding="utf-8")
    return out


def _mentions(evidence: str, word: str) -> bool:
    e, w = evidence.lower(), word.lower()
    return w in e or (len(w) > 4 and w[:-1] in e)


def score_run(audit: AuditStore, run_id: str, gold: dict) -> dict:
    finds = defaultdict(list)
    for f in audit.list_items(run_id, "finding"):
        finds[f["payload"]["req_id"]].append(f["payload"])
        for c in check.corroborations(audit, f["item_id"]):
            finds[f["payload"]["req_id"]].append(c)  # an AI report merged into a code finding

    def predicted(rid, word, sources):
        return any(_mentions(p.get("evidence", ""), word) for p in finds[rid]
                   if p.get("source") in sources)

    out = {}
    for name, sources in (("code", {"code"}), ("ai", {"ai"}), ("code+ai", {"code", "ai"}),
                          ("flag every weak word", None)):
        tp = fp = fn = tn = 0
        for rid, rows in gold.items():
            for g in rows:
                p = True if sources is None else predicted(rid, g["weak_word"], sources)
                d = g["label"] == "defect"
                tp += p and d
                fp += p and not d
                fn += (not p) and d
                tn += (not p) and not d
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[name] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(prec, 3),
                     "recall": round(rec, 3), "f1": round(f1, 3)}
    return out


def run(profiles: list[str], n: int, seed: int) -> dict:
    cfg = load_config()
    audit = AuditStore(cfg.resolved_db_path())
    sample = ROOT / "data" / "public" / "qure" / f"sample_{n}_{seed}.csv"
    if not sample.exists():
        prepare(n, seed)
    gold = json.loads(sample.with_suffix(".gold.json").read_text(encoding="utf-8"))
    res = {"eval": "E1 QuRE quality flags", "attribution": ATTRIBUTION,
           "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
           "sample": f"{n} unique requirements, seed {seed}",
           "labelled_weak_words": sum(len(v) for v in gold.values()),
           "defects": sum(1 for v in gold.values() for g in v if g["label"] == "defect"),
           "started": datetime.now().isoformat(timespec="seconds"), "profiles": {}}
    for prof in profiles:
        run_id = check.start(cfg, audit, sample).run_id
        rep = check.ai_review(cfg, audit, run_id, reviewer=prof, conflicts=False)
        mc = model_calls(audit, run_id, cfg)
        res["profiles"][prof] = {"run_id": run_id, "failed": rep.failed,
                                 "cost_usd": mc["cost_usd"], "calls": mc["calls"],
                                 "scores": score_run(audit, run_id, gold)}
    return res


def markdown(res: dict) -> str:
    lines = [f"# {res['eval']} ({res['started']})", "", f"Data: {res['attribution']}",
             (f"Sample: {res['sample']}; {res['labelled_weak_words']} labelled weak words, "
             f"{res['defects']} judged defects by the human reviewers."), "",
             ("A weak word counts as flagged when a finding quotes it. Scores are for the "
             "defect class, before any human review in Zyn."), "",
             "| Model | Flagged by | Precision | Recall | F1 | TP | FP | FN |",
             "|---|---|---|---|---|---|---|---|"]
    for prof, p in res["profiles"].items():
        for name, s in p["scores"].items():
            lines.append(f"| {prof} | {name} | {s['precision']} | {s['recall']} | {s['f1']} | "
                         f"{s['tp']} | {s['fp']} | {s['fn']} |")
    lines += ["", "Runs: " + ", ".join(f"{k} {v['run_id']} (USD {v['cost_usd']}, "
                                         f"{v['calls']} calls)"
                                         for k, v in res["profiles"].items())]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prepare", "run"])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--profiles", default="claude-opus")
    a = ap.parse_args()
    if a.stage == "prepare":
        print(prepare(a.n, a.seed))
    else:
        r = run(a.profiles.split(","), a.n, a.seed)
        out = ROOT / "docs" / "evals"
        out.mkdir(parents=True, exist_ok=True)
        stem = f"e1-qure-{r['started'][:10]}"
        (out / f"{stem}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        (out / f"{stem}.md").write_text(markdown(r), encoding="utf-8")
        print(markdown(r))
