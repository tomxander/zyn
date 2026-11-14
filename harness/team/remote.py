"""Client for interacting with a remote Zyn team server via HTTP."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


def _handle_response(res: httpx.Response) -> tuple[int, Any]:
    if res.is_error:
        try:
            err = res.json().get("error", res.text)
        except (ValueError, json.JSONDecodeError):
            err = res.text or str(res.status_code)
        print(f"API Error ({res.status_code}): {err}", file=sys.stderr)
        return 2, None
    try:
        return 0, res.json()
    except (ValueError, json.JSONDecodeError):
        return 0, res.content


async def async_cmd_remote(args: Any, client: httpx.AsyncClient | None = None) -> int:
    token = os.environ.get("ZYN_TOKEN") or getattr(args, "token", None)
    if not token:
        print("Error: No access token. Set ZYN_TOKEN in environment.", file=sys.stderr)
        return 2

    server = getattr(args, "server", None) or os.environ.get("ZYN_SERVER", "http://127.0.0.1:8600")
    server = server.rstrip("/")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Zyn-Request": "1",
    }

    close_client = False
    if client is None:
        client = httpx.AsyncClient(base_url=server, headers=headers, timeout=60.0)
        close_client = True
    else:
        for k, v in headers.items():
            if k not in client.headers:
                client.headers[k] = v

    try:
        cmd = getattr(args, "remote_cmd", "")
        project = getattr(args, "project", None)
        fail_on_findings = getattr(args, "fail_on_findings", False)

        if cmd == "runs":
            params = {}
            if project:
                params["project"] = project
            res = await client.get("/api/runs", params=params)
            code, data = _handle_response(res)
            if code != 0:
                return code
            print(json.dumps(data, indent=2))
            return 0

        if cmd == "check":
            file_path = Path(args.file)
            if not file_path.is_file():
                print(f"File not found: {file_path}", file=sys.stderr)
                return 2

            files = {"file": (file_path.name, file_path.read_bytes())}
            if getattr(args, "source", None) and args.source:
                source_path = Path(args.source)
                if not source_path.is_file():
                    print(f"Source file not found: {source_path}", file=sys.stderr)
                    return 2
                files["source"] = (source_path.name, source_path.read_bytes())

            data = {}
            if project:
                data["project"] = project
            if getattr(args, "rules", None) and args.rules:
                data["rules"] = args.rules
            if getattr(args, "ears", False):
                data["ears"] = "true"

            res = await client.post("/api/new/check", data=data, files=files)
            code, rep = _handle_response(res)
            if code != 0:
                return code
            print(json.dumps(rep, indent=2))

            if fail_on_findings:
                run_id = rep.get("run_id") if isinstance(rep, dict) else None
                if run_id:
                    view_res = await client.get(f"/api/runs/{run_id}")
                    if not view_res.is_error:
                        view = view_res.json()
                        findings = view.get("findings", [])
                        if len(findings) > 0:
                            return 1
            return 0

        if cmd == "testcheck":
            tests = getattr(args, "tests", [])
            if not tests:
                print("Error: No test files specified.", file=sys.stderr)
                return 2
            test_path = Path(tests[0])
            if not test_path.is_file():
                print(f"Test file not found: {test_path}", file=sys.stderr)
                return 2
            files = {"file": (test_path.name, test_path.read_bytes())}

            dbc_path = Path(args.dbc)
            if not dbc_path.is_file():
                print(f"DBC file not found: {dbc_path}", file=sys.stderr)
                return 2
            files["dbc"] = (dbc_path.name, dbc_path.read_bytes())

            if getattr(args, "reqs", None) and args.reqs:
                reqs_path = Path(args.reqs)
                if not reqs_path.is_file():
                    print(f"Requirements file not found: {reqs_path}", file=sys.stderr)
                    return 2
                files["reqs"] = (reqs_path.name, reqs_path.read_bytes())

            data = {}
            if project:
                data["project"] = project

            res = await client.post("/api/new/tests", data=data, files=files)
            code, rep = _handle_response(res)
            if code != 0:
                return code
            print(json.dumps(rep, indent=2))

            if fail_on_findings:
                run_id = rep.get("run_id") if isinstance(rep, dict) else None
                if run_id:
                    view_res = await client.get(f"/api/runs/{run_id}")
                    if not view_res.is_error:
                        view = view_res.json()
                        findings = view.get("findings", [])
                        if len(findings) > 0:
                            return 1
            return 0

        if cmd == "delta":
            old_path = Path(args.old)
            new_path = Path(args.new)
            if not old_path.is_file() or not new_path.is_file():
                print("Error: Old or new file not found.", file=sys.stderr)
                return 2
            files = {
                "old": (old_path.name, old_path.read_bytes()),
                "new": (new_path.name, new_path.read_bytes()),
            }
            data = {}
            if project:
                data["project"] = project

            res = await client.post("/api/new/delta", data=data, files=files)
            code, rep = _handle_response(res)
            if code != 0:
                return code
            print(json.dumps(rep, indent=2))
            return 0

        if cmd == "findings":
            run_id = args.run_id
            res = await client.get(f"/api/runs/{run_id}")
            code, view = _handle_response(res)
            if code != 0:
                return code
            findings = view.get("findings", []) if isinstance(view, dict) else []
            print(json.dumps(findings, indent=2))
            return 0

        if cmd == "export":
            run_id = args.run_id
            as_file = Path(args.as_file)

            action_res = await client.post(f"/api/runs/{run_id}/actions/export", json={})
            code, rep = _handle_response(action_res)
            if code != 0:
                return code

            files = rep.get("files", {}) if isinstance(rep, dict) else {}
            target_key = "json"
            if as_file.suffix.lower() == ".xlsx" and "xlsx" in files:
                target_key = "xlsx"
            elif as_file.suffix.lower() == ".reqif" and "reqif" in files:
                target_key = "reqif"
            elif target_key not in files and files:
                target_key = next(iter(files.keys()))

            target_filename = Path(str(files.get(target_key, "findings.json"))).name
            dl_res = await client.get(f"/api/download?run_id={run_id}&path={target_filename}")
            if dl_res.is_error:
                print(f"Download failed ({dl_res.status_code}): {dl_res.text}", file=sys.stderr)
                return 2

            as_file.parent.mkdir(parents=True, exist_ok=True)
            as_file.write_bytes(dl_res.content)
            print(f"Exported to {as_file}")
            return 0

        print(f"Unknown remote command: {cmd}", file=sys.stderr)
        return 2

    except httpx.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        return 2
    finally:
        if close_client:
            await client.aclose()


def cmd_remote(args: Any, client: httpx.AsyncClient | None = None) -> int:
    return asyncio.run(async_cmd_remote(args, client=client))
