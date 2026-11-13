"""Zyn as an MCP server: protocol handshake, tool list, tool calls, errors."""

from __future__ import annotations

import io
import json
from pathlib import Path

from harness.mcp_server import TOOLS, handle, serve

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def call(name, **arguments):
    r = handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                "params": {"name": name, "arguments": arguments}})
    return r["result"]


def test_handshake_and_tool_list():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    assert init["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert {t["name"] for t in tools} == set(TOOLS)
    assert all(t["inputSchema"]["type"] == "object" and t["description"] for t in tools)
    assert handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})["error"]["code"] == -32601


def test_check_requirements_with_source():
    r = call("check_requirements", source_path=str(DATA / "icx100_srs.md"), requirements=[
        {"id": "A", "text": "The cluster shall respond quickly."},
        {"id": "B", "text": "The cluster shall enter the ACTIVE state within 2.5 s of IGN "
                            "changing from OFF to ON."}])
    assert r["isError"] is False
    cats = {(f["req_id"], f["category"]) for f in r["structuredContent"]["findings"]}
    assert ("A", "weak_word") in cats and ("B", "invented_value") in cats
    assert json.loads(r["content"][0]["text"])["requirements"] == 2


def test_check_tests_inline_capl():
    r = call("check_tests", test_filename="t.can",
             test_code="testcase TC_1()\n{\n  // REQ-1\n  $FuelLvl = 9;\n}\n",
             requirements=[{"id": "REQ-1", "text": "Below 10 percent the telltale is lit."},
                           {"id": "REQ-2", "text": "The chime sounds."}])
    s = r["structuredContent"]
    assert s["tests"] == ["TC_1"] and s["coverage"]["untested"] == ["REQ-2"]
    assert any(f["category"] == "unknown_signal" and f["evidence"] == "FuelLvl"
               for f in s["findings"])


def test_check_quote_and_validate_spec():
    q = call("check_quote", quote="The cluster shall perform a display self-test at startup",
             source_path=str(DATA / "icx100_srs.md"))["structuredContent"]
    assert q["verbatim_in_source"] is True
    v = call("validate_test_spec", requirement_text="When the fuel level is below 10 percent, "
             "the low-fuel telltale shall be lit.", spec={
                 "template": "threshold", "input_signal": "FuelLevel", "threshold": 12,
                 "direction": "below", "output_signal": "TT_LowFuel", "expected_value": 1,
                 "value_sources": [{"param": "threshold", "quote": "below 10 percent"}]})
    assert v["structuredContent"]["passes"] is False
    assert any("12" in p for p in v["structuredContent"]["problems"])


def test_errors_come_back_as_tool_errors():
    r = call("check_requirements")
    assert r["isError"] is True and "requirement" in r["content"][0]["text"]
    assert handle({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                   "params": {"name": "drop_tables"}})["error"]["code"] == -32602


def test_stdio_loop_answers_each_line():
    lines = [{"jsonrpc": "2.0", "id": 1, "method": "ping"}, "not json",
             {"jsonrpc": "2.0", "method": "notifications/initialized"},
             {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": "list_rule_profiles", "arguments": {}}}]
    out = io.StringIO()
    serve(io.StringIO("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines)),
          out)
    answers = [json.loads(x) for x in out.getvalue().splitlines()]
    assert [a.get("id") for a in answers] == [1, None, 2]
    assert answers[1]["error"]["code"] == -32700
    assert "default" in {p["name"] for p in answers[2]["result"]["structuredContent"]["profiles"]}
