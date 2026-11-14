from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from harness.api.server import create_app
from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.team.principal import Principal
from harness.team.remote import cmd_remote
from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings
from harness.team.tokens import create_token


@pytest.fixture
def remote_env(tmp_path: Path):
    db_file = tmp_path / "team_audit.sqlite"
    audit = AuditStore(str(db_file))

    team = TeamSettings(
        database_url=f"sqlite:///{db_file}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        allow_insecure_http=True,
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={
            "proj-a": ProjectSettings(
                name="Project A",
                rule_profile="default",
                four_eyes=True,
                roles={"viewer": ["g-a-view"], "engineer": ["g-a-eng"], "approver": ["g-a-appr"]},
            ),
        },
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(db_file),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
        team=team,
    )
    app = create_app(cfg, audit)

    alice = Principal(id="alice", name="Alice", email="alice@test", kind="person")
    audit.log_event(
        actor="Alice",
        action="signed_in",
        actor_id="alice",
        detail={"groups": ["g-a-eng"]},
    )
    _, token = create_token(audit, alice, "test-ci-token")

    req_file = tmp_path / "reqs.csv"
    req_file.write_text(
        "ext_id,text\n"
        "REQ-1,The system shall illuminate the telltale within 200 ms.\n"
        "REQ-2,The system should probably illuminate quickly.\n",
        encoding="utf-8",
    )

    return {
        "cfg": cfg,
        "audit": audit,
        "app": app,
        "token": token,
        "req_file": req_file,
        "tmp_path": tmp_path,
    }


class DummyArgs:
    def __init__(self, **kwargs):
        self.server = kwargs.get("server", "http://testserver")
        self.token = kwargs.get("token")
        self.project = kwargs.get("project", "proj-a")
        self.fail_on_findings = kwargs.get("fail_on_findings", False)
        self.remote_cmd = kwargs.get("remote_cmd")
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_remote_check_starts_run_in_project(remote_env, monkeypatch, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    token = remote_env["token"]
    req_file = remote_env["req_file"]

    args = DummyArgs(
        token=token,
        project="proj-a",
        remote_cmd="check",
        file=str(req_file),
        source=None,
        rules=None,
        ears=False,
    )

    code = cmd_remote(args, client=client)
    assert code == 0

    out = capsys.readouterr().out
    data = json.loads(out)
    assert "run_id" in data
    run_id = data["run_id"]

    audit = remote_env["audit"]
    assert audit.run_project(run_id) == "proj-a"


def test_remote_fail_on_findings_exit_code(remote_env, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    token = remote_env["token"]
    req_file = remote_env["req_file"]

    args = DummyArgs(
        token=token,
        project="proj-a",
        remote_cmd="check",
        file=str(req_file),
        source=None,
        rules=None,
        ears=False,
        fail_on_findings=True,
    )

    code = cmd_remote(args, client=client)
    assert code == 1


def test_remote_bad_token_exit_2(remote_env, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    req_file = remote_env["req_file"]

    args = DummyArgs(
        token="zyn_badtokenbadtoken",
        project="proj-a",
        remote_cmd="check",
        file=str(req_file),
        source=None,
        rules=None,
        ears=False,
    )

    code = cmd_remote(args, client=client)
    assert code == 2
    err = capsys.readouterr().err
    assert "Sign in first" in err or "401" in err


def test_remote_runs_and_findings(remote_env, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    token = remote_env["token"]
    req_file = remote_env["req_file"]

    # First run check
    args_check = DummyArgs(
        token=token,
        project="proj-a",
        remote_cmd="check",
        file=str(req_file),
    )
    assert cmd_remote(args_check, client=client) == 0
    run_id = json.loads(capsys.readouterr().out)["run_id"]

    # Test runs list
    args_runs = DummyArgs(
        token=token,
        project="proj-a",
        remote_cmd="runs",
    )
    assert cmd_remote(args_runs, client=client) == 0
    runs = json.loads(capsys.readouterr().out)
    assert any(r["run_id"] == run_id for r in runs)

    # Test findings
    args_find = DummyArgs(
        token=token,
        remote_cmd="findings",
        run_id=run_id,
    )
    assert cmd_remote(args_find, client=client) == 0
    findings = json.loads(capsys.readouterr().out)
    assert len(findings) > 0


def test_remote_export(remote_env, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    token = remote_env["token"]
    req_file = remote_env["req_file"]
    tmp_path = remote_env["tmp_path"]

    # 1. Run check
    args_check = DummyArgs(
        token=token,
        project="proj-a",
        remote_cmd="check",
        file=str(req_file),
    )
    assert cmd_remote(args_check, client=client) == 0
    run_id = json.loads(capsys.readouterr().out)["run_id"]

    # 2. Export run
    out_file = tmp_path / "exported_findings.json"
    args_export = DummyArgs(
        token=token,
        remote_cmd="export",
        run_id=run_id,
        as_file=str(out_file),
    )
    assert cmd_remote(args_export, client=client) == 0
    assert out_file.is_file()
    assert len(out_file.read_text(encoding="utf-8")) > 0


def test_serve_team_without_team_block(capsys, tmp_path):
    from harness.__main__ import cmd_serve

    class ServeArgs:
        team = True
        host = "127.0.0.1"
        port = 8600
        no_browser = True

    # Config with team=None
    cfg = HarnessConfig(db_path=str(tmp_path / "audit.sqlite"), roles={}, profiles={}, team=None)
    code = cmd_serve(cfg, ServeArgs())
    assert code == 2
    err = capsys.readouterr().err
    assert "serve --team needs a team section in config.yaml." in err


def test_remote_reads_zyn_token_from_env(remote_env, monkeypatch, capsys):
    app = remote_env["app"]
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    token = remote_env["token"]

    args = DummyArgs(
        token=None,
        project="proj-a",
        remote_cmd="runs",
    )

    # 1. Without ZYN_TOKEN -> fails with code 2
    monkeypatch.delenv("ZYN_TOKEN", raising=False)
    code = cmd_remote(args, client=client)
    assert code == 2
    assert "Set ZYN_TOKEN in environment" in capsys.readouterr().err

    # 2. With ZYN_TOKEN -> succeeds
    monkeypatch.setenv("ZYN_TOKEN", token)
    code = cmd_remote(args, client=client)
    assert code == 0

