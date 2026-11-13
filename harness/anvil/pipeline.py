"""Anvil pipeline, generator first.

start():    approved Sift requirements + a DBC -> one proposed test spec per requirement
            (template + parameters, model-proposed, code-validated). A person approves specs.
generate(): approved, valid specs -> test cases by code, fault-injection check per spec.
export():   cases as JSON, XLSX and a pytest module (linted, not run on hardware).
"""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness import PROTOTYPE_LABEL
from harness.anvil import impact
from harness.anvil.dbc import CanDb, load_dbc
from harness.anvil.generate import generate_cases
from harness.anvil.scripts import lint, module
from harness.anvil.simbench import CONFTEST
from harness.anvil.simulate import fault_check
from harness.anvil.validate import validate
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.prompts import load_prompt
from harness.schemas.forge import SpecBatch, flatten
from harness.sift.pipeline import StageReport, display_id

WORKFLOW = "forge"
CODE_ACTOR = "code:forge"
PROMPT = "forge_spec_v2"


def _dbc_path(audit: AuditStore, run_id: str) -> str:
    return audit.get_item(f"FORGE-{run_id}")["payload"]["dbc_path"]


def _dbc(audit: AuditStore, run_id: str) -> CanDb:
    return load_dbc(_dbc_path(audit, run_id))


def start(cfg: HarnessConfig, audit: AuditStore, sift_run: str, dbc_path: Path | str,
          generator: str = "generator", workers: int = 4) -> StageReport:
    reqs = audit.approved_items(sift_run, "requirement")
    if not reqs:
        raise ValueError(f"Run {sift_run} has no approved requirements.")
    db = load_dbc(dbc_path)
    run_id = audit.start_run(WORKFLOW, note=f"from {sift_run} with {db.filename}")
    meta = {"sift_run": sift_run, "dbc_path": str(Path(dbc_path).resolve()),
            "dbc_file": db.filename, "dbc_sha256": db.sha256, "requirements": len(reqs)}
    audit.add_item(run_id, "forge_input", meta, created_by=CODE_ACTOR, item_id=f"FORGE-{run_id}")
    audit.log_event(CODE_ACTOR, "ingested", run_id=run_id, object_type="forge_input",
                    input_sha256=db.sha256, detail=meta)
    return _propose(cfg, audit, run_id, reqs, db, generator, workers)


def without_spec(audit: AuditStore, run_id: str) -> list[dict]:
    """Approved requirements of the source run that have no spec yet (a section failed)."""
    meta = audit.get_item(f"FORGE-{run_id}")["payload"]
    have = {s["payload"]["req_id"] for s in audit.list_items(run_id, "test_spec")}
    return [r for r in audit.approved_items(meta["sift_run"], "requirement")
            if display_id(r["item_id"]) not in have]


def resume(cfg: HarnessConfig, audit: AuditStore, run_id: str, generator: str = "generator",
           workers: int = 4) -> StageReport:
    """Proposes specs only for requirements that have none, e.g. after an API error."""
    return _propose(cfg, audit, run_id, without_spec(audit, run_id), _dbc(audit, run_id),
                    generator, workers)


def _propose(cfg, audit, run_id, reqs, db, generator, workers) -> StageReport:
    by_section: dict[str, list[dict]] = {}
    for r in reqs:
        by_section.setdefault(r["payload"].get("section_number") or "-", []).append(r)
    system = load_prompt(PROMPT).replace("{dbc}", db.prompt_block())

    def one(section: str, group: list[dict]):
        lines = "\n".join(f"[{display_id(r['item_id'])}] {r['payload']['text']}" for r in group)
        return section, group, structured_call(
            cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator, task="forge_spec",
            prompt_version=PROMPT, system=system,
            user=f"Approved requirements from section {section}:\n{lines}",
            output_model=SpecBatch)

    done, failed = [], {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(one, s, g) for s, g in by_section.items()]
        results = []
        for f, s in zip(futs, by_section, strict=True):
            try:
                results.append(f.result())
            except StructuredOutputFailure as e:
                failed[s] = str(e)
    for section, group, res in sorted(results, key=lambda x: x[1][0]["item_id"]):
        by_id = {display_id(r["item_id"]): r for r in group}
        for spec in res.output.specs:
            req = by_id.get(spec.req_id)
            if req is None:
                audit.log_event(CODE_ACTOR, "spec_dropped", run_id=run_id,
                                detail={"reason": "unknown requirement ID", "req_id": spec.req_id})
                continue
            payload = flatten(spec.model_dump(mode="json"))
            payload.update({
                "requirement_text": req["payload"]["text"],
                "requirement_quote": req["payload"].get("source_quote", ""),
                "requirement_item": req["item_id"], "section_number": section,
                "problems": validate(payload, req["payload"]["text"], db),
                "generated_by": res.profile_name,
            })
            audit.add_item(run_id, "test_spec", payload, created_by=f"model:{res.profile_name}",
                           item_id=f"TS-{spec.req_id}@{run_id}")
            done.append(spec.req_id)
    return StageReport(run_id, done, [], failed)


def repropose_candidates(audit: AuditStore, run_id: str) -> list[dict]:
    seen, out = set(), []
    for s in _repropose_candidates(audit, run_id):
        if s["item_id"] not in seen:
            seen.add(s["item_id"])
            out.append(s)
    return out


def _repropose_candidates(audit: AuditStore, run_id: str) -> list[dict]:
    """Specs worth asking again: rejected or failing code checks and without cases, or whose
    requirement has a newer approved version (after a spec change)."""
    have = {c["payload"]["spec_item"] for c in audit.list_items(run_id, "test_case")}
    return [s for s in audit.list_items(run_id, "test_spec")
            if s["item_id"] not in have
            and (s["status"] == "rejected" or s["payload"]["problems"])
    ] + [s for s in audit.list_items(run_id, "test_spec")
         if s["status"] != "rejected"
         and impact.spec_requirement_state(audit, s["payload"]) == "changed"]


def repropose(cfg: HarnessConfig, audit: AuditStore, run_id: str,
              item_ids: list[str] | None = None, generator: str = "generator") -> StageReport:
    """Asks the model again (current prompt) for the given specs only. Each answer becomes a
    new version of the same spec, open for a person's decision; other specs are untouched.
    Always asks again: re-proposing exists to get a different answer."""
    cfg = cfg.fresh()
    db = _dbc(audit, run_id)
    targets = [s for s in repropose_candidates(audit, run_id)
               if item_ids is None or s["item_id"] in item_ids]
    system = load_prompt(PROMPT).replace("{dbc}", db.prompt_block())
    by_section: dict[str, list[dict]] = {}
    for s in targets:
        by_section.setdefault(s["payload"].get("section_number") or "-", []).append(s)
    done, failed = [], {}
    for section, group in by_section.items():
        lines = "\n".join(f"[{g['payload']['req_id']}] "
                          f"{_requirement_fields(audit, g['payload'])['requirement_text']}"
                          for g in group)
        try:
            res = structured_call(
                cfg=cfg, audit=audit, run_id=run_id, role_or_profile=generator,
                task="forge_spec", prompt_version=PROMPT, system=system,
                user=f"Approved requirements from section {section}:\n{lines}",
                output_model=SpecBatch)
        except StructuredOutputFailure as e:
            failed[section] = str(e)
            continue
        by_req = {g["payload"]["req_id"]: g for g in group}
        for spec in res.output.specs:
            old_item = by_req.get(spec.req_id)
            if old_item is None:
                continue
            keep = _requirement_fields(audit, old_item["payload"])
            payload = {**flatten(spec.model_dump(mode="json")), **keep,
                       "generated_by": res.profile_name}
            payload["problems"] = validate(payload, keep["requirement_text"], db)
            audit.edit_item(old_item["item_id"], payload, f"model:{res.profile_name}",
                            comment=f"re-proposed with {PROMPT}", source="model")
            done.append(spec.req_id)
    return StageReport(run_id, done, [], failed)


def _requirement_fields(audit: AuditStore, spec_payload: dict) -> dict:
    """Requirement fields for a spec: the requirement's latest approved text if it changed."""
    if impact.spec_requirement_state(audit, spec_payload) == "changed":
        r = impact.requirement_now(audit, spec_payload)["payload"]
        return {"requirement_text": r["text"],
                "requirement_quote": r.get("source_quote", ""),
                "requirement_item": spec_payload["requirement_item"],
                "section_number": r.get("section_number") or spec_payload["section_number"]}
    return {k: spec_payload[k] for k in (
        "requirement_text", "requirement_quote", "requirement_item", "section_number")}


def revalidate(audit: AuditStore, run_id: str, payload: dict) -> list[str]:
    return validate(payload, payload["requirement_text"], _dbc(audit, run_id))


def generate(audit: AuditStore, run_id: str, actor: str) -> dict:
    """Cases for every approved spec whose code checks pass. Re-running replaces nothing:
    a spec version that already has cases is skipped. A new spec version gets new cases
    under new IDs; the old ones stay in the record as superseded."""
    db = _dbc(audit, run_id)
    have = {(c["payload"]["spec_item"], c["payload"].get("spec_version", 1))
            for c in audit.list_items(run_id, "test_case")}
    made, skipped = 0, []
    for s in audit.approved_items(run_id, "test_spec"):
        p = s["payload"]
        if (s["item_id"], s["version"]) in have:
            continue
        state = impact.spec_requirement_state(audit, p)
        if state != "current":
            skipped.append({"spec": s["item_id"], "problems": [
                f"requirement {state} since this spec; propose the spec again first"]})
            continue
        problems = validate(p, p["requirement_text"], db)
        if problems:
            skipped.append({"spec": s["item_id"], "problems": problems})
            continue
        req = {"id": p["req_id"], "text": p["requirement_text"],
               "quote": p["requirement_quote"] or p["requirement_text"]}
        cases = generate_cases(p, req, db)
        fc = fault_check(p, cases, db)
        audit.log_event(CODE_ACTOR, "fault_checked", run_id=run_id, object_type="test_spec",
                        object_id=s["item_id"], object_version=s["version"], detail=fc)
        for c in cases:
            if s["version"] > 1:
                c = {**c, "case_id": f"{c['case_id']}-v{s['version']}"}
            audit.add_item(run_id, "test_case", {**c, "spec_item": s["item_id"],
                                                 "spec_version": s["version"]},
                           created_by=CODE_ACTOR, item_id=f"{c['case_id']}@{run_id}")
            made += 1
    audit.log_event(actor, "cases_generated", run_id=run_id,
                    detail={"cases": made, "skipped": skipped})
    return {"cases": made, "skipped": skipped}


def fault_results(audit: AuditStore, run_id: str) -> dict[str, dict]:
    return {e["object_id"]: e["detail"] for e in audit.events(run_id=run_id)
            if e["action"] == "fault_checked"}


def export(audit: AuditStore, run_id: str, actor: str, out_dir: Path | None = None) -> dict:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    specs = {s["item_id"]: s for s in audit.list_items(run_id, "test_spec")}
    cases, left_out = [], []
    for c in audit.list_items(run_id, "test_case"):
        state = impact.case_state(audit, c, specs[c["payload"]["spec_item"]])
        if state == "current":
            cases.append(c["payload"])
        else:
            left_out.append({"case_id": c["payload"]["case_id"], "state": state})
    if not cases:
        raise ValueError("No current test cases in this run. Approve specs and generate.")
    faults = fault_results(audit, run_id)
    from harness.anvil.score import kill_score
    score = kill_score(audit, run_id)
    out = out_dir or PROJECT_ROOT / "runs" / "exports" / run_id
    out.mkdir(parents=True, exist_ok=True)
    src = module(cases, run_id)
    problems = lint(src)
    files = {"json": out / "test_cases.json", "xlsx": out / "test_cases.xlsx",
             "pytest": out / "test_generated.py", "conftest": out / "conftest.py",
             "robot": out / "zyn_generated.robot",
             "robot_keywords": out / "zyn_keywords.resource",
             "capl": out / "zyn_generated.can", "steps": out / "test_steps.csv"}
    from harness.anvil import formats

    suite, resource = formats.robot(cases, run_id)
    files["robot"].write_text(suite, encoding="utf-8")
    files["robot_keywords"].write_text(resource, encoding="utf-8")
    capl_src = formats.capl(cases, run_id)
    files["capl"].write_text(capl_src, encoding="cp1252", errors="replace")  # CANoe default
    problems += [f"CAPL: {p}" for p in formats.capl_problems(capl_src)]
    files["steps"].write_text(formats.steps_csv(cases), encoding="utf-8")
    used_specs = {c["spec_item"] for c in cases}
    files["json"].write_text(json.dumps({"label": PROTOTYPE_LABEL, "run_id": run_id,
                                         "dbc_path": str(_dbc_path(audit, run_id)),
                                         "cases": cases, "left_out": left_out,
                                         "specs": {k: specs[k]["payload"] for k in used_specs},
                                         "fault_checks": faults, "fault_score": score,
                                         "lint": problems},
                                        indent=2, ensure_ascii=False),
                             encoding="utf-8")
    files["pytest"].write_text(src, encoding="utf-8")
    files["conftest"].write_text(CONFTEST.format(folder=out.as_posix(), root=str(PROJECT_ROOT)),
                                 encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = "Test cases"
    ws.append([(f"{PROTOTYPE_LABEL} Run {run_id}. Generated by code from approved test specs. "
               "Not run against hardware.")])
    ws["A1"].font = Font(bold=True)
    cols = ["Case", "Requirement", "Template", "Kind", "Title", "Steps", "Expected",
            "Why these values", "Oracle (requirement clause)", "Open values"]
    ws.append(cols)
    for c in ws[2]:
        c.font = Font(bold=True)
    for c in cases:
        steps = "; ".join(f"{s['at_ms']} ms {s['do']} "
                          + " ".join(str(s[k]) for k in ("signal", "message", "value")
                                     if k in s) for s in c["steps"])
        ws.append([c["case_id"], c["requirement_id"], c["template"], c["kind"], c["title"],
                   steps, c["expected"], c["boundary_rationale"], c["oracle"]["quote"],
                   "; ".join(c["open_values"])])
    fs = wb.create_sheet("Fault check")
    fs.append([f"{PROTOTYPE_LABEL} {score['note']}"])
    fs["A1"].font = Font(bold=True)
    fs.append(["Injected faults detected", score["detected"], "of", score["faults"]])
    fs.append([])
    fs.append(["Requirement", "Template", "Fault", "Detected by"])
    for c in fs[4]:
        c.font = Font(bold=True)
    tmpl = {s["item_id"]: s["payload"]["template"] for s in specs.values()}
    for sid, fc in faults.items():
        if sid not in used_specs:
            continue
        for f in fc.get("faults", {}).values():
            fs.append([specs[sid]["payload"]["req_id"], tmpl.get(sid), f["fault"],
                       ", ".join(f["detected_by"]) or "NOT DETECTED"])
    wb.save(files["xlsx"])
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}
    audit.log_event(actor, "exported", run_id=run_id, object_type="test_case",
                    detail={"count": len(cases), "lint": problems,
                            "files": {k: str(p) for k, p in files.items()}, "sha256": hashes})
    return {"count": len(cases), "left_out": len(left_out), "lint": problems,
            "files": {k: str(p) for k, p in files.items()}}
