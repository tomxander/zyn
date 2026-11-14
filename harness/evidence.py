"""Evidence report for any run: one verdict per item, the evidence behind it, who decided.

Five verdicts, so a model or infrastructure problem never looks like a finding:
- pass:    checked and fine (all code checks passed and a person approved, or nothing found)
- fail:    a real problem (a confirmed finding, a rejected item, a test that fails on the
           correct simulation)
- warn:    needs a person (undecided, approved over a failed check, faults no case detects)
- skipped: not checked (not automatable, rejected spec, a test naming no DBC signal)
- broken:  could not be checked (the model call for it failed)

Outputs, written next to the run's other exports:
- evidence.html       readable report, prints to PDF from any browser
- evidence.junit.xml  for CI dashboards (warn is a passing test with a verdict property)
- audit_chain.json    every event of the run, each hashed together with the previous one,
                      so a later change to any event breaks the chain (verify_chain)

The process mapping says which ASPICE processes this kind of record may support. It is
not an assessment and claims no compliance.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig

VERDICTS = ("pass", "fail", "warn", "skipped", "broken")

PROCESSES = {
    "sift": [("SYS.2 / SWE.1 requirements analysis",
              ("Each requirement quotes its source text and page; code checks and an AI "
              "reviewer's advice are recorded; a named person approved or rejected it.")),
             ("SUP.8 configuration management",
              "Every edit is a new version; the record is append-only.")],
    "check": [("SYS.2 / SWE.1 requirements analysis",
               ("Each requirement of the imported set was checked by code rules (profile "
               "recorded) and, where run, an AI reviewer whose findings quote the text.")),
              ("SUP.9 problem resolution",
               "Each finding was confirmed or dismissed by a named person, with a reason.")],
    "delta": [("SUP.10 change request management",
               ("Changes between two revisions are listed and each marked needs action or no "
               "action by a named person.")),
              ("SUP.8 configuration management",
               "Both revisions are identified by file hash.")],
    "forge": [("SYS.5 / SWE.6 verification against requirements",
               ("Each test case traces to the requirement clause it rests on and lists the "
               "values it had to assume.")),
              ("Verification measure",
               ("Each spec's cases were run against a simulated correct cluster and injected "
               "faults; the record shows which faults they detect. Not run on hardware."))],
}
PROCESSES["smoke"] = PROCESSES["sift"]
PROCESSES["tests"] = [
    ("SYS.5 / SWE.6 verification against requirements",
     ("Tests produced elsewhere were checked by code against the CAN database (signal names, "
     "ranges) and the requirement set (references, values, coverage).")),
    ("SUP.9 problem resolution",
     "Each finding was confirmed or dismissed by a named person, with a reason.")]


def _decision(audit: AuditStore, item_id: str) -> dict | None:
    d = audit.latest_decision(item_id)
    if not d:
        return None
    return {"decision": d["action"], "by": d["actor"], "at": d["ts"],
            "comment": (d["detail"] or {}).get("comment")}


def _row(item_id, title, verdict, reason, evidence="", checks=(), ai=None, decision=None,
         ref=None) -> dict:
    assert verdict in VERDICTS
    return {"id": ref or item_id.split("@")[0], "item_id": item_id, "title": title,
            "verdict": verdict, "reason": reason, "evidence": evidence or "",
            "checks": list(checks), "ai": ai, "decision": decision}


# ---- per workflow ------------------------------------------------------------------------


def _sift_rows(audit: AuditStore, run_id: str) -> list[dict]:
    from harness.api.views import support_states

    rows = []
    for it in audit.list_items(run_id, "requirement"):
        p = it["payload"]
        review = audit.latest_ai_review(it["item_id"])
        checks = support_states(audit, it, review)
        failed = [c["label"] for c in checks if not c["ok"]]
        st = it["status"]
        if st == "rejected":
            v, why = "fail", "Rejected by a person"
        elif st == "approved" and not failed:
            v, why = "pass", "Approved; every check passed"
        elif st == "approved":
            v, why = "warn", "Approved over: " + "; ".join(failed)
        else:
            v, why = "warn", "Not decided yet" + (f"; {'; '.join(failed)}" if failed else "")
        ai = None
        if review and review.get("detail"):
            ai = f"{review['detail'].get('verdict')} ({review['actor']})"
        quote = p.get("source_quote", "")
        if p.get("page"):
            quote = f"p. {p['page']}: {quote}"
        rows.append(_row(it["item_id"], p.get("text", ""), v, why, quote,
                         [f"{'ok' if c['ok'] else 'FAIL'} {c['label']}" for c in checks], ai,
                         _decision(audit, it["item_id"])))
    return rows


def _check_rows(audit: AuditStore, run_id: str) -> list[dict]:
    from harness.sift import check as sc

    reqs = sorted(audit.list_items(run_id, "imported_requirement"),
                  key=lambda i: i["payload"]["order"])
    finds: dict[str, list[dict]] = {}
    for f in audit.list_items(run_id, "finding"):
        finds.setdefault(f["payload"]["req_id"], []).append(f)
    done = sc.ai_done(audit, run_id)
    ai_ran = bool(done)
    batch_of = {}
    for n, b in enumerate(sc.batches(audit, run_id)):
        for r in b:
            batch_of[r["item_id"]] = n
    meta = (audit.get_item(f"SET-{run_id}") or {}).get("payload") or {}
    unchecked = set((meta.get("coverage") or {}).get("no_signal") or [])
    rows = []
    for r in reqs:
        p = r["payload"]
        fs = finds.get(p["ext_id"], [])
        conf = [f for f in fs if f["status"] == "approved"]
        open_ = [f for f in fs if f["status"] in ("proposed", "edited")]
        dism = [f for f in fs if f["status"] == "rejected"]
        lines = [f"{'confirmed' if f in conf else 'open' if f in open_ else 'dismissed'} "
                 f"{f['payload']['category']} ({f['payload']['source']}): "
                 f"\"{f['payload']['evidence']}\"" for f in fs]
        if conf:
            v, why = "fail", f"{len(conf)} finding(s) confirmed by a person"
        elif open_:
            v, why = "warn", f"{len(open_)} finding(s) not decided yet"
        elif ai_ran and batch_of.get(r["item_id"]) not in done:
            v, why = "broken", "The AI review of its batch did not finish"
        elif dism:
            v, why = "pass", f"All {len(dism)} finding(s) dismissed by a person"
        elif p["ext_id"] in unchecked:
            v, why = "skipped", ("Nothing to check: the test names no signal from "
                                 f"{meta.get('dbc') or 'the CAN database'}")
        else:
            v, why = "pass", ("No findings" if ai_ran
                              else "No findings from code checks; AI review not run")
        decided = [_decision(audit, f["item_id"]) for f in conf + dism]
        last = max((d for d in decided if d), key=lambda d: d["at"], default=None)
        rows.append(_row(r["item_id"], p["text"], v, why, "", lines, None, last,
                         ref=p["ext_id"]))
    return rows


def _delta_rows(audit: AuditStore, run_id: str) -> list[dict]:
    from harness.sift import delta as sd

    rows = []
    for e in audit.list_items(run_id, "delta_entry"):
        p = e["payload"]
        st = e["status"]
        if st == "approved":
            v, why = "warn", "Marked needs action"
        elif st == "rejected":
            v, why = "pass", "Marked no action"
        else:
            v, why = "warn", "Not decided yet"
        rows.append(_row(e["item_id"], sd.summary(p), v, why,
                         p.get("new_text") or p.get("old_text") or "", [p["kind"]], None,
                         _decision(audit, e["item_id"])))
    return rows


def _forge_rows(audit: AuditStore, run_id: str) -> list[dict]:
    from harness.anvil import pipeline as forge
    from harness.anvil.score import current_checks

    checks = current_checks(audit, run_id)
    cases: dict[str, int] = {}
    for c in audit.list_items(run_id, "test_case"):
        cases[c["payload"]["spec_item"]] = cases.get(c["payload"]["spec_item"], 0) + 1
    rows = []
    for s in audit.list_items(run_id, "test_spec"):
        p = s["payload"]
        fc = checks.get(s["item_id"])
        lines = [f"FAIL {x}" for x in p.get("problems", [])]
        if fc:
            lines += [f"{'ok' if f['detected_by'] else 'NOT DETECTED'} fault: {f['fault']}"
                      for f in fc.get("faults", {}).values()]
        if p["template"] == "not_automatable":
            v, why = "skipped", f"Not automatable: {p.get('manual_test_idea') or 'manual test'}"
        elif s["status"] == "rejected":
            v, why = "skipped", "Spec rejected by a person"
        elif s["status"] != "approved":
            v, why = "warn", "Spec not decided yet"
        elif p.get("problems"):
            v, why = "fail", "Approved spec fails code checks"
        elif fc is None:
            v, why = "warn", "Approved; cases not generated yet"
        elif fc.get("reference_passes") is False:
            v, why = "fail", "A case fails on the correct simulation"
        elif fc["detected"] < fc["total"]:
            v, why = "warn", f"Cases detect {fc['detected']} of {fc['total']} injected faults"
        else:
            v, why = "pass", (f"{cases.get(s['item_id'], 0)} cases; detect all "
                              f"{fc['total']} injected faults")
        rows.append(_row(s["item_id"], p.get("requirement_text", ""), v, why,
                         p.get("requirement_quote", ""), lines, f"template {p['template']} "
                         f"({p.get('generated_by', 'model')})", _decision(audit, s["item_id"]),
                         ref=p["req_id"]))
    for r in forge.without_spec(audit, run_id):
        rows.append(_row(r["item_id"], r["payload"].get("text", ""), "broken",
                         "No spec: the model call for its section failed", ""))
    return rows


ROWS = {"sift": _sift_rows, "smoke": _sift_rows, "check": _check_rows, "tests": _check_rows,
        "delta": _delta_rows, "forge": _forge_rows}


def kind_of(audit: AuditStore, run_id: str) -> str:
    from harness.api.views import SIFT

    wf = next(r["workflow"] for r in audit.list_runs() if r["run_id"] == run_id)
    return {"sift-check": "check", "sift-delta": "delta", "forge": "forge",
            "test-check": "tests"}.get(
        wf, "sift" if wf in SIFT else "smoke")


def verdicts(audit: AuditStore, run_id: str) -> dict:
    kind = kind_of(audit, run_id)
    rows = ROWS[kind](audit, run_id)
    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICTS}
    return {"run_id": run_id, "kind": kind, "rows": rows, "counts": counts}


# ---- audit chain -------------------------------------------------------------------------


def _canon(e: dict) -> str:
    return json.dumps({k: v for k, v in e.items() if k != "chain" and not (k == "actor_id" and v is None)}, sort_keys=True,
                      ensure_ascii=False, separators=(",", ":"))


def audit_chain(audit: AuditStore, run_id: str) -> dict:
    prev = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    events = []
    for e in audit.events(run_id=run_id):
        prev = hashlib.sha256((prev + _canon(e)).encode("utf-8")).hexdigest()
        events.append({**e, "chain": prev})
    return {"run_id": run_id, "algorithm": "sha256(previous + canonical event JSON), "
            "starting from sha256(run_id)", "events": events, "head": prev}


def verify_chain(data: dict) -> tuple[bool, int | None]:
    """(True, None) if every link holds, else (False, index of the first broken event)."""
    prev = hashlib.sha256(data["run_id"].encode("utf-8")).hexdigest()
    for i, e in enumerate(data["events"]):
        prev = hashlib.sha256((prev + _canon(e)).encode("utf-8")).hexdigest()
        if e.get("chain") != prev:
            return False, i
    return prev == data["head"], None if prev == data["head"] else len(data["events"])


# ---- writers -----------------------------------------------------------------------------


def _models(audit: AuditStore, run_id: str) -> list[str]:
    out = set()
    for e in audit.events(run_id=run_id):
        if e["action"] in ("generated", "replayed"):
            out.add(f"{e['model_profile']} ({e['model_served'] or e['model_requested']})")
    return sorted(out)


def junit(v: dict, run_id: str) -> bytes:
    rows = v["rows"]
    c = v["counts"]
    suite = ET.Element("testsuite", name=f"zyn.{v['kind']}.{run_id}", tests=str(len(rows)),
                       failures=str(c["fail"]), errors=str(c["broken"]),
                       skipped=str(c["skipped"]))
    for r in rows:
        tc = ET.SubElement(suite, "testcase", classname=f"zyn.{v['kind']}", name=r["id"])
        props = ET.SubElement(tc, "properties")
        ET.SubElement(props, "property", name="verdict", value=r["verdict"])
        if r["verdict"] == "fail":
            ET.SubElement(tc, "failure", message=r["reason"]).text = "\n".join(r["checks"])
        elif r["verdict"] == "broken":
            ET.SubElement(tc, "error", message=r["reason"])
        elif r["verdict"] == "skipped":
            ET.SubElement(tc, "skipped", message=r["reason"])
        elif r["verdict"] == "warn":
            ET.SubElement(tc, "system-out").text = f"WARN: {r['reason']}"
    root = ET.Element("testsuites")
    root.append(suite)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


_CSS = """
body{font-family:Inter,system-ui,sans-serif;font-size:13px;line-height:1.5;margin:32px;
color:black;background:white}
h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;margin:28px 0 8px}
table{border-collapse:collapse;width:100%}td,th{border-top:1px solid silver;padding:6px 8px;
text-align:left;vertical-align:top}th{font-weight:600}
.v{font-weight:600;text-transform:uppercase;font-size:11px}.q{font-style:italic}
.m{font-family:'IBM Plex Mono',monospace;font-size:12px}.quiet{opacity:.72}
ul{margin:0;padding-left:16px}@media print{body{margin:12mm}}
"""


def _h(x) -> str:
    return html.escape(str(x if x is not None else ""))


def html_report(v: dict, meta: dict) -> str:
    c = v["counts"]
    parts = [(f"<!doctype html><html lang='en'><meta charset='utf-8'>"
             f"<title>Zyn evidence {_h(v['run_id'])}</title><style>{_CSS}</style><body>"),
             (f"<p class='quiet'>{_h(PROTOTYPE_LABEL)} Outputs are model-assisted; verdicts "
             "come from code checks and named people as recorded below.</p>"),
             f"<h1>Evidence report: {_h(meta['tool'])}</h1>",
             (f"<p class='m'>Run {_h(v['run_id'])} · generated {_h(meta['generated'])} by "
             f"{_h(meta['actor'])} · audit chain head {_h(meta['chain_head'][:16])}…</p>"),
             "<h2>Verdicts</h2><p>" + " · ".join(f"{_h(k)} {c[k]}" for k in VERDICTS) + "</p>",
             ("<p class='quiet'>pass: checked and fine · fail: a real problem · warn: needs a "
             "person · skipped: deliberately not checked · broken: could not be checked "
             "(model or infrastructure)</p>"),
             "<h2>Inputs and settings</h2><ul>"]
    for k, val in meta["inputs"].items():
        parts.append(f"<li>{_h(k)}: <span class='m'>{_h(val)}</span></li>")
    parts.append("</ul><h2>Items</h2><table><tr><th>Item</th><th>Verdict</th><th>Text and "
                 "evidence</th><th>Checks</th><th>Decision</th></tr>")
    for r in v["rows"]:
        d = r["decision"]
        dec = (f"{_h(d['decision'])} by {_h(d['by'])}<br><span class='m quiet'>"
               f"{_h(d['at'][:19])}</span>" + (f"<br>{_h(d['comment'])}" if d.get("comment")
                                               else "")) if d else "<span class='quiet'>none"
        dec += "</span>" if not d else ""
        ai = f"<br><span class='quiet'>AI: {_h(r['ai'])}</span>" if r["ai"] else ""
        parts.append(
            f"<tr><td class='m'>{_h(r['id'])}</td><td><span class='v'>{_h(r['verdict'])}"
            f"</span><br>{_h(r['reason'])}</td><td>{_h(r['title'])}"
            + (f"<br><span class='q'>“{_h(r['evidence'])}”</span>" if r["evidence"]
               else "") + ai + "</td><td><ul>"
            + "".join(f"<li>{_h(x)}</li>" for x in r["checks"]) + f"</ul></td><td>{dec}</td></tr>")
    parts.append("</table><h2>What this record may support</h2><table><tr><th>Process"
                 "</th><th>How</th></tr>")
    for proc, how in PROCESSES.get(v["kind"], []):
        parts.append(f"<tr><td>{_h(proc)}</td><td>{_h(how)}</td></tr>")
    parts.append("</table><p class='quiet'>A mapping to help an assessor find the record, not "
                 "an assessment. Compliance depends on your own process and validation plan."
                 "</p><h2>Limits</h2><ul>"
                 "<li>Model output is advice; only a named person approves or rejects.</li>"
                 "<li>Code checks find what they are written to find, nothing more.</li>"
                 "<li>Fault checks run on a simulated cluster with a fixed fault list, not "
                 "on hardware.</li>"
                 "<li>Verify the audit chain with <span class='m'>python -m harness evidence "
                 "verify &lt;audit_chain.json&gt;</span>.</li></ul></body></html>")
    return "".join(parts)


def export_evidence(audit: AuditStore, run_id: str, actor: str,
                    cfg: HarnessConfig | None = None, out_dir: Path | None = None) -> dict:
    from harness.api.views import tool_name

    v = verdicts(audit, run_id)
    chain = audit_chain(audit, run_id)
    run = next(r for r in audit.list_runs() if r["run_id"] == run_id)
    inputs = {"workflow": run["workflow"], "note": run.get("note") or ""}
    models = _models(audit, run_id)
    if models:
        inputs["models"] = ", ".join(models)
    rules = (audit.get_item(f"SET-{run_id}") or {}).get("payload", {}).get("rules")
    if rules:
        inputs["rule profile"] = f"{rules['name']} ({rules['sha256'][:12]})"
    meta = {"tool": tool_name(run["workflow"]), "actor": actor,
            "generated": datetime.now(UTC).isoformat(timespec="seconds"),
            "chain_head": chain["head"], "inputs": inputs}
    out = (out_dir or PROJECT_ROOT / "runs" / "exports" / run_id) / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    files = {"html": out / "evidence.html", "junit": out / "evidence.junit.xml",
             "chain": out / "audit_chain.json"}
    files["chain"].write_text(json.dumps(chain, indent=1, ensure_ascii=False), encoding="utf-8")
    files["junit"].write_bytes(junit(v, run_id))
    files["html"].write_text(html_report(v, meta), encoding="utf-8")
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}
    audit.log_event(actor, "exported", run_id=run_id, object_type="evidence",
                    detail={"counts": v["counts"], "chain_head": chain["head"],
                            "files": {k: str(p) for k, p in files.items()}, "sha256": hashes})
    return {"count": len(v["rows"]), "counts": v["counts"], "chain_head": chain["head"],
            "files": {k: str(p) for k, p in files.items()}}
