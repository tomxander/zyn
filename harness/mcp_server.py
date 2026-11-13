"""Zyn as an MCP server: its deterministic checks as tools for any MCP client.

Claude Code, Claude Desktop or any agent that speaks the Model Context Protocol can call
Zyn as the checker inside its own loop: write requirements or tests, ask Zyn, fix what Zyn
rejects. The tools run code only. They make no model calls, start no runs and write nothing
to the audit log, so a client cannot approve anything through them.

Run:   python -m harness mcp          (stdio, newline-delimited JSON-RPC 2.0)
Add to Claude Code:
       claude mcp add zyn -- <path to .venv python> -m harness mcp

Written against the MCP specification directly (initialize, tools/list, tools/call, ping)
so Zyn needs no extra dependency.
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from harness import PROTOTYPE_LABEL
from harness.config import PROJECT_ROOT

PROTOCOL_VERSION = "2025-06-18"
DEFAULT_DBC = PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"


def _reqs_arg(args: dict) -> list[dict]:
    """Requirements given inline ([{id, text, quote?}]) or as a ReqIF/Excel/CSV path."""
    if args.get("requirements"):
        return [{"ext_id": r.get("id") or f"R{i + 1}", "text": r["text"],
                 "quote": r.get("quote", ""), "heading": ""}
                for i, r in enumerate(args["requirements"])]
    if args.get("requirement_set_path"):
        from harness.sift.check import _quote_of
        from harness.sift.importer import load_requirement_set

        rs = load_requirement_set(args["requirement_set_path"])
        return [{"ext_id": r.ext_id, "text": r.text, "quote": _quote_of(r.attrs),
                 "heading": r.heading} for r in rs.requirements]
    raise ValueError("Give requirements (a list of {id, text}) or requirement_set_path.")


def tool_check_requirements(args: dict) -> dict:
    from harness.sift.check import code_findings
    from harness.sift.rules import load_profile

    profile = load_profile(args.get("rule_profile") or "default")
    reqs = _reqs_arg(args)
    found = code_findings(reqs, profile=profile)
    matches = None
    if args.get("source_path"):
        from harness.outside import ground_findings
        from harness.sift.ingest import load_document

        g, matches = ground_findings(reqs, load_document(args["source_path"]), profile)
        found += g
    return {"rule_profile": profile.name, "requirements": len(reqs), "findings": found,
            "source_matches": matches}


def tool_check_tests(args: dict) -> dict:
    from harness.outside import check_tests, prepare

    paths = [Path(p) for p in args.get("test_paths") or []]
    tmp = None
    if args.get("test_code"):
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name) / (args.get("test_filename") or "test_inline.py")
        p.write_text(args["test_code"], encoding="utf-8")
        paths.append(p)
    if not paths:
        raise ValueError("Give test_paths or test_code.")
    try:
        db, dbc_found, units = prepare(paths, Path(args.get("dbc_path") or DEFAULT_DBC))
        reqs = {}
        if args.get("requirements") or args.get("requirement_set_path"):
            reqs = {r["ext_id"]: r["text"] for r in _reqs_arg(args)}
        found, coverage = check_tests(units, db, reqs)
        found = dbc_found + found
    finally:
        if tmp:
            tmp.cleanup()
    return {"tests": [u.name for u in units], "findings": found, "coverage": coverage}


def tool_check_quote(args: dict) -> dict:
    from harness.outside import best_match, source_sentences
    from harness.sift import checks
    from harness.sift.ingest import load_document

    doc = load_document(args["source_path"])
    exact = checks.is_grounded(args["quote"], doc.markdown)
    m, score = best_match(args["quote"], source_sentences(doc))
    return {"verbatim_in_source": exact, "closest_sentence": m["text"] if m else None,
            "section": m["section"] if m else None, "page": m["page"] if m else None,
            "word_match": score}


def tool_validate_test_spec(args: dict) -> dict:
    from harness.anvil.dbc import load_dbc
    from harness.anvil.validate import validate

    spec = {"template": None, "value_sources": [], "track_bounds": [], **args["spec"]}
    problems = validate(spec, args["requirement_text"],
                        load_dbc(args.get("dbc_path") or DEFAULT_DBC))
    return {"passes": not problems, "problems": problems}


def tool_check_specs(args: dict) -> dict:
    from harness.anvil.dbc import load_dbc
    from harness.anvil.formal import check_set

    specs = [{"value_sources": [], "track_bounds": [], **s} for s in args["specs"]]
    return check_set(specs, load_dbc(args.get("dbc_path") or DEFAULT_DBC))


def tool_list_rule_profiles(args: dict) -> dict:
    from harness.sift.rules import CODE_CHECKS, list_profiles

    return {"profiles": list_profiles(), "checks": CODE_CHECKS}


def tool_fault_score(args: dict) -> dict:
    from harness.anvil.score import kill_score
    from harness.audit.store import AuditStore
    from harness.config import load_config

    cfg = load_config()
    return kill_score(AuditStore(cfg.resolved_db_path()), args["run_id"])


_REQ_PROPS = {
    "requirements": {"type": "array", "description": "Inline requirements.",
                     "items": {"type": "object", "properties": {
                         "id": {"type": "string"}, "text": {"type": "string"},
                         "quote": {"type": "string", "description": "Source quote, if any"}},
                         "required": ["text"]}},
    "requirement_set_path": {"type": "string",
                             "description": "Path to a ReqIF, Excel or CSV requirement set."},
}

TOOLS: dict[str, tuple[Callable[[dict], dict], str, dict]] = {
    "check_requirements": (tool_check_requirements, (
        "Code checks on requirements: weak words, placeholders, modal verbs, atomicity, "
        "duplicates, EARS (per rule profile). With source_path, also matches each requirement "
        "to its source sentence and flags ungrounded requirements, invented values and changed "
        "modal verbs. Deterministic; no model calls."),
        {"type": "object", "properties": {**_REQ_PROPS,
            "source_path": {"type": "string", "description": "Specification the requirements "
                            "were drawn from (PDF, DOCX, Markdown, text)."},
            "rule_profile": {"type": "string", "description": "Rule profile name (default)."}}}),
    "check_tests": (tool_check_tests, (
        "Code checks on tests from any tool (pytest, CAPL, Robot Framework, text): unknown or "
        "misspelt signals and out-of-range values against a DBC, expected values not in the "
        "referenced requirement, missing or unknown requirement IDs, untested requirements."),
        {"type": "object", "properties": {
            "test_paths": {"type": "array", "items": {"type": "string"}},
            "test_code": {"type": "string", "description": "Inline test source."},
            "test_filename": {"type": "string", "description": "Name for inline code, e.g. "
                              "tests.can, so the format is recognised."},
            "dbc_path": {"type": "string", "description": "CAN database (default: synthetic "
                         "ICX-100)."}, **_REQ_PROPS}}),
    "check_quote": (tool_check_quote, (
        "Is this quote verbatim in the source document, and which sentence is closest?"),
        {"type": "object", "properties": {"quote": {"type": "string"},
                                          "source_path": {"type": "string"}},
         "required": ["quote", "source_path"]}),
    "validate_test_spec": (tool_validate_test_spec, (
        "Check a signal-level test spec (template threshold, event_response, timeout, "
        "periodic_tx or tracking, with its parameters and value_sources quotes) against the "
        "requirement text and the DBC, as Anvil does before generating cases."),
        {"type": "object", "properties": {
            "spec": {"type": "object", "description": "Anvil spec fields: template, "
                     "input_signal, threshold, direction, output_signal, expected_value, "
                     "max_latency_ms, timeout_ms, period_ms, message, value_sources, ..."},
            "requirement_text": {"type": "string"},
            "dbc_path": {"type": "string"}}, "required": ["spec", "requirement_text"]}),
    "check_specs": (tool_check_specs, (
        "Write signal-level test specs as formal statements ('When FuelLevel < 10, TT_LowFuel "
        "shall be 1 within 300 ms') and check them as a set: conflicting responses to the "
        "same condition, different timeouts for the same message, impossible tracking "
        "bands, and cluster outputs no spec checks."),
        {"type": "object", "properties": {
            "specs": {"type": "array", "items": {"type": "object"}, "description":
                      "Specs with req_id, template and their parameters."},
            "dbc_path": {"type": "string"}}, "required": ["specs"]}),
    "list_rule_profiles": (tool_list_rule_profiles, ("Rule profiles and the code checks they "
                           "can switch on."), {"type": "object", "properties": {}}),
    "fault_score": (tool_fault_score, (
        "Fault-kill score of a Anvil run: injected faults the generated cases detect, faults "
        "no case detects, cases that detect none."),
        {"type": "object", "properties": {"run_id": {"type": "string"}},
         "required": ["run_id"]}),
}


def handle(msg: dict) -> dict | None:
    """One JSON-RPC message in, one response out (None for notifications)."""
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:
        return None  # notifications (initialized, cancelled) need no answer

    def ok(result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    if method == "initialize":
        return ok({"protocolVersion": msg.get("params", {}).get("protocolVersion",
                                                                PROTOCOL_VERSION),
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "zyn", "version": "0.1"},
                   "instructions": f"{PROTOTYPE_LABEL} Deterministic checks for requirements "
                                   "and tests. Findings are questions for a person, not "
                                   "verdicts."})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{"name": n, "description": d, "inputSchema": s}
                             for n, (_f, d, s) in TOOLS.items()]})
    if method == "tools/call":
        p = msg.get("params", {})
        name = p.get("name")
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        try:
            out = TOOLS[name][0](p.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": json.dumps(
                out, indent=1, ensure_ascii=False, default=str)}],
                "structuredContent": out, "isError": False})
        except Exception as e:  # noqa: BLE001  (report to the client as a tool error, keep serving)
            return ok({"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                       "isError": True})
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"Method not found: {method}"}}


def serve(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "Parse error"}}
        else:
            resp = handle(msg)
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()
