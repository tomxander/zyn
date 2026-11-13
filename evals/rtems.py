"""E3: requirement extraction and grounding on RTEMS action requirements.

Source: RTEMS rtems-central, pinned commit 82230386 (2023-12-19), spec/rtems/*/req/*.yml.
Only files whose SPDX header offers "CC-BY-SA-4.0 OR BSD-2-Clause" are used, under the
BSD-2-Clause option; copyright embedded brains GmbH & Co. KG and others as stated per file.
Embedded RTOS, not automotive.

The YAML is rendered into a Markdown specification by this script (our construction, not
public ground truth): per action requirement a "Conditions" section (the pre-condition
states, "While ...") and a "Required behaviour" section (the post-condition states, written
as "shall" statements). Gold = every sentence with "shall" in the post-condition states.
Test code and the transition map are never shown to the model.

The model gets each "Required behaviour" section with Sift's extraction prompt (extract_v2,
the same one the product uses). Scored: recall of gold statements, share of extracted
quotes found verbatim in the section, modal verbs kept, extra items.

Run from the project root:
  python -m evals.rtems fetch          # downloads the pinned files into data/public/rtems/
  python -m evals.rtems run --profiles claude-opus,claude-sonnet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import yaml

from harness.audit.store import AuditStore
from harness.config import load_config
from harness.metrics import model_calls
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.prompts import load_prompt
from harness.schemas.sift import ExtractionResult
from harness.sift import checks

COMMIT = "82230386f0691791cbf0ea1ffac69337190d3ff5"
RAW = f"https://raw.githubusercontent.com/RTEMS/rtems-central/{COMMIT}/"
DIR = ROOT / "data" / "public" / "rtems"
COMPONENTS = ["event", "sem", "timer", "barrier", "message", "part", "ratemon", "signal"]
PER_COMPONENT = 1
DUAL = "CC-BY-SA-4.0 OR BSD-2-Clause"
ATTRIBUTION = (f"RTEMS rtems-central at commit {COMMIT[:8]}, spec/rtems/*/req, files offered "
               "as CC-BY-SA-4.0 OR BSD-2-Clause, used under BSD-2-Clause; copyright embedded "
               "brains GmbH & Co. KG and others as stated per file. Rendered into a document "
               "by Zyn's eval script (our construction).")


def fetch() -> list[Path]:
    tree = json.loads((DIR / "tree.json").read_text(encoding="utf-8"))
    paths = sorted(x["path"] for x in tree["tree"]
                   if re.match(r"spec/rtems/[^/]+/req/[^/]+\.yml$", x["path"]))
    got = []
    for comp in COMPONENTS:
        n = 0
        for p in paths:
            if p.split("/")[2] != comp or n >= PER_COMPONENT:
                continue
            text = urllib.request.urlopen(RAW + p, timeout=30).read().decode("utf-8")
            first = text.splitlines()[0] if text else ""
            if DUAL not in first or "functional-type: action" not in text:
                continue
            out = DIR / "req" / p.replace("/", "__")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            got.append(out)
            n += 1
    return got


_REF = re.compile(r"\$\{([^}:]*)(?::([^}]*))?\}")
_CACHE: dict[str, dict | None] = {}


def _item(uid: str) -> dict | None:
    """A spec item by uid (e.g. /rtems/barrier/if/create), fetched at the pinned commit and
    cached under data/public/rtems/items/."""
    if uid in _CACHE:
        return _CACHE[uid]
    local = DIR / "items" / (uid.strip("/").replace("/", "__") + ".yml")
    data = None
    if local.exists():
        data = yaml.safe_load(local.read_text(encoding="utf-8"))
    else:
        try:
            text = urllib.request.urlopen(f"{RAW}spec{uid}.yml", timeout=30).read().decode()
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(text, encoding="utf-8")
            data = yaml.safe_load(text)
        except Exception:  # noqa: BLE001 - missing item: fall back to a readable name
            data = None
    _CACHE[uid] = data
    return data


def _uid(base: str, path: str) -> str:
    if path.startswith("/"):
        parts = path.strip("/").split("/")
    else:
        parts = base.strip("/").split("/")
        for seg in path.split("/"):
            if seg == "..":
                parts.pop()
            elif seg and seg != ".":
                parts.append(seg)
    return "/" + "/".join(parts)


def resolve(text: str, base: str = "/", own: dict | None = None) -> str:
    """Resolves ${path:attribute} references the way the RTEMS spec does, as far as needed
    for readable sentences: names, parameter names, glossary terms and plurals."""
    def sub(m):
        path, attr = m.group(1), (m.group(2) or "/name").lstrip("/")
        if path == ".":
            v = (own or {}).get(attr.split("/")[0])
            return resolve(v, base, own) if isinstance(v, str) else ""
        item = _item(_uid(base, path))
        last = path.rstrip("/").split("/")[-1].replace("-", "_")
        if item is None:
            return last
        pm = re.match(r"params\[(\d+)\]/name", attr)
        if pm:
            ps = item.get("params") or []
            i = int(pm.group(1))
            return ps[i]["name"] if i < len(ps) and "name" in ps[i] else last
        v = item.get(attr.split("/")[0])
        return v if isinstance(v, str) else last
    out = text or ""
    for _ in range(3):  # resolved values can contain references themselves
        new = _REF.sub(sub, out)
        if new == out:
            break
        out = new
    return " ".join(out.split())


def render() -> tuple[str, list[dict]]:
    """Markdown document and gold statements."""
    files = sorted((DIR / "req").glob("*.yml"))
    lines = ["# RTEMS action requirements (rendered for evaluation)", "",
             ("Rendered by Zyn's evaluation script from RTEMS rtems-central specification files. "
             "Not an RTEMS document."), ""]
    gold = []
    for k, f in enumerate(files, start=1):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        base = "/" + "/".join(f.stem.split("__")[1:-1])  # e.g. /rtems/barrier/req
        name = f.stem.split("__")[-1].replace("-", " ")
        comp = f.stem.split("__")[2]
        lines += [f"## {k} {comp} {name}", "", resolve(d.get("text"), base, d), ""]
        lines += [f"### {k}.1 Conditions", ""]
        for c in d.get("pre-conditions") or []:
            for s in c["states"]:
                t = resolve(s.get("text"), base, d)
                if t:
                    lines.append(f"- {t}")
        lines += ["", f"### {k}.2 Required behaviour", ""]
        n = 0
        for c in d.get("post-conditions") or []:
            for s in c["states"]:
                t = resolve(s.get("text"), base, d)
                if not t:
                    continue
                n += 1
                lines += [f"{k}.2.{n} {t}", ""]
                for sent in re.split(r"(?<=\.)\s+(?=[A-Z])", t):
                    if re.search(r"\bshall\b", sent):
                        gold.append({"section": f"{k}.2", "file": f.name, "text": sent})
    return "\n".join(lines) + "\n", gold


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", checks.normalise(s)))


def _match(quote: str, gold: str) -> float:
    q, g = checks.normalise(quote), checks.normalise(gold)
    if g and q and (g in q or q in g):
        return 1.0
    a, b = _tokens(quote), _tokens(gold)
    return len(a & b) / len(a | b) if a | b else 0.0


def run(profiles: list[str], whole: bool = False) -> dict:
    """whole=False: the model sees each "Required behaviour" section. whole=True: it sees the
    whole component (introduction, "While ..." conditions and behaviour), so conditions it
    wrongly extracts as requirements show up as extra items."""
    from harness.sift.ingest import split_sections

    cfg = load_config()
    audit = AuditStore(cfg.resolved_db_path())
    doc, gold = render()
    (DIR / "rendered.md").write_text(doc, encoding="utf-8")
    title, sections = split_sections(doc)
    behaviour = [s for s in sections if s.heading == "Required behaviour"]
    if whole:
        targets = []
        for b in behaviour:
            k = b.number.split(".")[0]
            parts = [s for s in sections if s.number == k or (s.number or "").startswith(k + ".")]
            text = "\n\n".join(f"{s.number} {s.heading}\n{s.text}" for s in parts)
            head = next((s.heading for s in parts if s.number == k), f"component {k}")
            targets.append(SimpleNamespace(number=b.number, heading=head, text=text))
    else:
        targets = behaviour
    res = {"eval": "E3 RTEMS extraction and grounding"
                   + (", whole components" if whole else ", behaviour sections"),
           "attribution": ATTRIBUTION, "whole": whole,
           "files": sorted(p.name for p in (DIR / "req").glob("*.yml")),
           "rendered_sha256": hashlib.sha256(doc.encode()).hexdigest(),
           "gold_statements": len(gold), "sections": len(targets),
           "started": datetime.now().isoformat(timespec="seconds"), "profiles": {}}
    for prof in profiles:
        run_id = audit.start_run("eval-rtems", note=f"E3 RTEMS extraction, {prof}")
        extracted, failed = [], 0
        for sec in targets:
            system = (load_prompt("extract_v2").replace("{section_number}", sec.number or "-")
                      .replace("{heading}", sec.heading).replace("{doc_title}", title)
                      .replace("{subsystem_id}", "GEN"))
            try:
                out = structured_call(cfg=cfg, audit=audit, run_id=run_id,
                                      role_or_profile=prof, task="extract_requirements",
                                      prompt_version="extract_v2", system=system,
                                      user=f"Section text:\n<section>\n{sec.text}\n</section>",
                                      output_model=ExtractionResult)
            except StructuredOutputFailure:
                failed += 1
                continue
            for r in out.output.requirements:
                extracted.append({"section": sec.number, "text": r.text,
                                  "quote": r.source_quote, "modal": r.modal.value,
                                  "grounded": checks.is_grounded(r.source_quote, sec.text),
                                  "modal_changed": checks.modal_changed(r.source_quote, r.text)})
        # greedy one-to-one matching within each section
        pairs = sorted(((_match(e["quote"], g["text"]), i, j)
                        for i, e in enumerate(extracted) for j, g in enumerate(gold)
                        if e["section"] == g["section"]), reverse=True)
        used_e, used_g = set(), set()
        for s, i, j in pairs:
            if s >= 0.6 and i not in used_e and j not in used_g:
                used_e.add(i)
                used_g.add(j)
        mc = model_calls(audit, run_id, cfg)
        n = len(extracted)
        res["profiles"][prof] = {
            "run_id": run_id, "failed_sections": failed, "cost_usd": mc["cost_usd"],
            "calls": mc["calls"], "extracted": n,
            "recall": round(len(used_g) / len(gold), 3) if gold else None,
            "matched": len(used_g),
            "extra": n - len(used_e),
            "quotes_verbatim": round(sum(e["grounded"] for e in extracted) / n, 3) if n else None,
            "modal_kept": round(sum(not e["modal_changed"] for e in extracted) / n, 3)
            if n else None,
            "missed": [gold[j]["text"] for j in range(len(gold)) if j not in used_g][:15],
            "extra_items": [extracted[i]["quote"] for i in range(n) if i not in used_e][:20],
        }
    return res


def markdown(res: dict) -> str:
    lines = [f"# {res['eval']} ({res['started']})", "", f"Data: {res['attribution']}",
             f"Files: {', '.join(res['files'])}.",
             f"{res['gold_statements']} gold statements in {res['sections']} sections.", "",
             "| Model | Recall | Extracted | Extra | Quotes verbatim | Modal kept | Cost (USD) |",
             "|---|---|---|---|---|---|---|"]
    for prof, p in res["profiles"].items():
        lines.append(f"| {prof} | {p['recall']} ({p['matched']}/{res['gold_statements']}) | "
                     f"{p['extracted']} | {p['extra']} | {p['quotes_verbatim']} | "
                     f"{p['modal_kept']} | {p['cost_usd']} |")
    for prof, p in res["profiles"].items():
        lines += ["", f"{prof} run {p['run_id']}; missed: "
                  + ("; ".join(p["missed"]) or "none")]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["fetch", "render", "run"])
    ap.add_argument("--profiles", default="claude-opus")
    ap.add_argument("--whole", action="store_true",
                    help="give the model whole components, conditions included")
    a = ap.parse_args()
    if a.stage == "fetch":
        for p in fetch():
            print(p.name)
    elif a.stage == "render":
        doc, gold = render()
        (DIR / "rendered.md").write_text(doc, encoding="utf-8")
        print(f"{len(gold)} gold statements")
    else:
        r = run(a.profiles.split(","), a.whole)
        out = ROOT / "docs" / "evals"
        out.mkdir(parents=True, exist_ok=True)
        stem = f"e3-rtems{'-whole' if a.whole else ''}-{r['started'][:10]}"
        (out / f"{stem}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        (out / f"{stem}.md").write_text(markdown(r), encoding="utf-8")
        print(markdown(r))
