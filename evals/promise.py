"""E2: requirement type classification against PROMISE NFR (original 625).

PROMISE NFR, (c) 2007 Jane Cleland-Huang, tera-PROMISE repository, CC BY-SA 3.0 (licence in
the data file header). Mirror: github.com/AleksandarMitrevski/se-requirements-classification
at commit 1f5dc45, file 0-datasets/tera-PROMISE NFR/nfr.arff. Not automotive.

The model classifies each requirement into Zyn's own type list (the same req_type used by
Sift extraction, same definitions). PROMISE uses 12 classes, so scoring is done twice:
- binary: functional vs non-functional;
- coarse: PROMISE classes and Zyn types both mapped onto functional, performance, security,
  usability, reliability, other.

Run from the project root:  python -m evals.promise --profiles claude-opus,claude-sonnet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from harness.audit.store import AuditStore
from harness.config import load_config
from harness.metrics import model_calls
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.schemas.common import ReqType

SRC = ROOT / "data" / "public" / "promise" / "nfr.arff"
ATTRIBUTION = ("PROMISE NFR (original 625), (c) 2007 Jane Cleland-Huang, tera-PROMISE "
               "repository, CC BY-SA 3.0. Used unmodified for evaluation, not redistributed.")
PROMISE_COARSE = {"F": "functional", "PE": "performance", "SC": "performance",
                  "SE": "security", "US": "usability", "LF": "usability", "A": "reliability",
                  "FT": "reliability", "L": "other", "O": "other", "MN": "other", "PO": "other"}
ZYN_COARSE = {"functional": "functional", "interface": "functional",
              "performance": "performance", "security": "security", "usability": "usability",
              "reliability": "reliability", "safety": "reliability", "constraint": "other",
              "other": "other"}
SYSTEM = """You classify software requirements by type. For each requirement give req_type, \
the main nature of the requirement:
- functional: a behaviour or function the system performs
- performance: timing, speed, capacity, throughput, scalability
- interface: a signal, data exchange or connection with another system
- safety: protection against harm to people
- security: access control, authentication, data protection, integrity
- usability: ease of use, learnability, look and feel, accessibility
- reliability: availability, fault tolerance, recovery
- constraint: a legal, regulatory, platform, portability, maintainability or operational \
condition the solution must meet
- other: none of the above
One answer per requirement, using the IDs as given."""


class Item(BaseModel):
    id: str = Field(description="The requirement ID exactly as given")
    req_type: ReqType


class Batch(BaseModel):
    items: list[Item]


def load() -> list[dict]:
    t = SRC.read_text(encoding="utf-8", errors="replace")
    data = t[t.index("@DATA") + 5:]
    rows = re.findall(r"^\s*(\d+),'(.*)',(\w+)\s*$", data, re.MULTILINE)
    return [{"id": f"P{i:03d}", "project": p, "text": " ".join(x.split()), "label": c}
            for i, (p, x, c) in enumerate(rows, start=1)]


def _f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return round(p, 3), round(r, 3), round(2 * p * r / (p + r), 3) if p + r else 0.0


def score(rows: list[dict], pred: dict[str, str]) -> dict:
    got = [(r, pred.get(r["id"])) for r in rows]
    answered = [(r, p) for r, p in got if p]
    tp = sum(1 for r, p in answered if r["label"] != "F" and ZYN_COARSE[p] != "functional")
    fp = sum(1 for r, p in answered if r["label"] == "F" and ZYN_COARSE[p] != "functional")
    fn = sum(1 for r, p in answered if r["label"] != "F" and ZYN_COARSE[p] == "functional")
    acc = sum(1 for r, p in answered if (r["label"] == "F") == (ZYN_COARSE[p] == "functional"))
    prec, rec, f1 = _f1(tp, fp, fn)
    classes = sorted(set(PROMISE_COARSE.values()))
    per = {}
    for c in classes:
        ctp = sum(1 for r, p in answered if PROMISE_COARSE[r["label"]] == c and ZYN_COARSE[p] == c)
        cfp = sum(1 for r, p in answered if PROMISE_COARSE[r["label"]] != c and ZYN_COARSE[p] == c)
        cfn = sum(1 for r, p in answered if PROMISE_COARSE[r["label"]] == c and ZYN_COARSE[p] != c)
        per[c] = dict(zip(("precision", "recall", "f1"), _f1(ctp, cfp, cfn), strict=True))
    conf = Counter((PROMISE_COARSE[r["label"]], ZYN_COARSE[p]) for r, p in answered)
    return {"answered": len(answered), "of": len(rows),
            "binary": {"accuracy": round(acc / len(answered), 3) if answered else 0,
                       "nfr_precision": prec, "nfr_recall": rec, "nfr_f1": f1},
            "coarse_macro_f1": round(sum(v["f1"] for v in per.values()) / len(per), 3),
            "coarse_per_class": per,
            "confusion": {f"{a} -> {b}": n for (a, b), n in sorted(conf.items())}}


def run(profiles: list[str], batch: int = 25) -> dict:
    cfg = load_config()
    audit = AuditStore(cfg.resolved_db_path())
    rows = load()
    res = {"eval": "E2 PROMISE type classification", "attribution": ATTRIBUTION,
           "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
           "requirements": len(rows), "labels": dict(Counter(r["label"] for r in rows)),
           "started": datetime.now().isoformat(timespec="seconds"), "profiles": {}}
    for prof in profiles:
        run_id = audit.start_run("eval-promise", note=f"E2 PROMISE NFR 625, {prof}")
        pred, failed = {}, []
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            user = "\n".join(f"[{r['id']}] {r['text']}" for r in chunk)
            try:
                out = structured_call(cfg=cfg, audit=audit, run_id=run_id,
                                      role_or_profile=prof, task="classify_type",
                                      prompt_version="eval_classify_type_v1", system=SYSTEM,
                                      user=user, output_model=Batch)
            except StructuredOutputFailure as e:
                failed.append(str(e))
                continue
            ids = {r["id"] for r in chunk}
            pred.update({it.id: it.req_type.value for it in out.output.items if it.id in ids})
        mc = model_calls(audit, run_id, cfg)
        res["profiles"][prof] = {"run_id": run_id, "failed_batches": len(failed),
                                 "cost_usd": mc["cost_usd"], "calls": mc["calls"],
                                 "scores": score(rows, pred)}
    return res


def markdown(res: dict) -> str:
    lines = [f"# {res['eval']} ({res['started']})", "", f"Data: {res['attribution']}",
             f"{res['requirements']} requirements; labels {res['labels']}.", "",
             ("| Model | Answered | F vs NFR accuracy | NFR precision | NFR recall | NFR F1 | "
             "Coarse macro F1 | Cost (USD) |"), "|---|---|---|---|---|---|---|---|"]
    for prof, p in res["profiles"].items():
        s, b = p["scores"], p["scores"]["binary"]
        lines.append(f"| {prof} | {s['answered']}/{s['of']} | {b['accuracy']} | "
                     f"{b['nfr_precision']} | {b['nfr_recall']} | {b['nfr_f1']} | "
                     f"{s['coarse_macro_f1']} | {p['cost_usd']} |")
    for prof, p in res["profiles"].items():
        lines += ["", f"{prof} per coarse class: " + "; ".join(
            f"{c} F1 {v['f1']}" for c, v in p["scores"]["coarse_per_class"].items()),
            f"Run {p['run_id']}."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", default="claude-opus")
    a = ap.parse_args()
    r = run(a.profiles.split(","))
    out = ROOT / "docs" / "evals"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"e2-promise-{r['started'][:10]}"
    (out / f"{stem}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (out / f"{stem}.md").write_text(markdown(r), encoding="utf-8")
    print(markdown(r))
