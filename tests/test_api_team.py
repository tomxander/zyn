from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from harness.api.server import create_app
from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.team.auth import Claims, FakeIdentityProvider
from harness.team.principal import Principal
from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings


@pytest.fixture
def team_env(tmp_path: Path):
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
            "proj-b": ProjectSettings(
                name="Project B",
                rule_profile="strict",
                four_eyes=True,
                roles={"viewer": ["g-b-view"], "engineer": ["g-b-eng"], "approver": ["g-b-appr"]},
            ),
        },
        allowed_models=["fake-gen"],
        service_accounts={
            "sa-ci": {
                "project": "proj-a",
                "role": "engineer",
                "token_sha256": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
            }
        },
        max_upload_mb=2,
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
    return cfg, audit


def _client_for(
    cfg: HarnessConfig,
    audit: AuditStore,
    name: str,
    email: str,
    groups: list[str],
    app: Any = None,
) -> TestClient:
    claims: Claims = {
        "sub": f"user-{name.lower()}",
        "iss": "https://idp",
        "name": name,
        "email": email,
        "groups": groups,
    }
    idp = FakeIdentityProvider(claims)
    if app is None:
        app = create_app(cfg, audit=audit, idp=idp)
    app.state.idp = idp
    client = TestClient(app)
    client.get("/auth/callback")
    return client


def test_health_without_sign_in(team_env):
    cfg, audit = team_env
    app = create_app(cfg, audit=audit)
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["mode"] == "team"
    assert "version" in data
    assert "schema" in data


def test_config_lists_only_my_projects(team_env):
    cfg, audit = team_env
    # Alice has approver on proj-a only
    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "team"
    assert data["person"]["name"] == "Alice"
    p_ids = [p["id"] for p in data["projects"]]
    assert p_ids == ["proj-a"]
    assert data["admin"] is False


def test_other_project_ids_are_404(team_env, tmp_path: Path):
    cfg, audit = team_env
    # Setup run and item in proj-b
    audit.start_run(workflow="sift-document", run_id="run-b-1", note="Run in B", project="proj-b", started_by_id="oidc:https://idp#user-dana")
    audit.add_item("run-b-1", "requirement", {"text": "Req in B", "order": 1, "source_quote": "Req in B"}, "Dana", item_id="item-b-1")

    # Alice has access only to proj-a
    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])

    # 1. Run view 404
    assert client.get("/api/runs/run-b-1").status_code == 404
    # 2. Audit view 404
    assert client.get("/api/runs/run-b-1/audit").status_code == 404
    # 3. Action 404
    assert client.post("/api/runs/run-b-1/actions/extract", headers={"X-Zyn-Request": "1"}).status_code == 404
    # 4. Decide 404
    assert client.post("/api/decide", json={"item_id": "item-b-1", "decision": "approved"}, headers={"X-Zyn-Request": "1"}).status_code == 404
    # 5. Edit 404
    assert client.post("/api/edit", json={"kind": "edit", "item_id": "item-b-1", "fields": {"text": "edited"}}, headers={"X-Zyn-Request": "1"}).status_code == 404
    # 6. Download 404
    assert client.get("/api/download?run_id=run-b-1&path=test.json").status_code == 404


def test_download_outside_run_exports_is_404(team_env, tmp_path: Path):
    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-alice")

    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    # Attempt directory traversal or path outside runs/exports/run-a-1
    assert client.get("/api/download?run_id=run-a-1&path=../../config.yaml").status_code == 404
    assert client.get("/api/download?run_id=run-a-1&path=runs/uploads/file.txt").status_code == 404


def test_upload_over_limit_is_413(team_env):
    cfg, audit = team_env
    client = _client_for(cfg, audit, "Bob", "bob@test", ["g-a-eng"])
    # max_upload_mb is 2, send 3MB file
    large_data = b"x" * (3 * 1024 * 1024)
    res = client.post(
        "/api/new/sift",
        data={"project": "proj-a"},
        files={"file": ("large.txt", io.BytesIO(large_data), "text/plain")},
        headers={"X-Zyn-Request": "1"},
    )
    assert res.status_code == 413
    assert "File is over 2 MB." in res.json().get("error", "")


def test_team_settings_admin_only_and_secrets_masked(team_env):
    cfg, audit = team_env
    # Alice (non-admin)
    client_alice = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    assert client_alice.get("/api/team-settings").status_code == 403

    # Eve (admin)
    client_eve = _client_for(cfg, audit, "Eve", "eve@test", ["g-admin"])
    res = client_eve.get("/api/team-settings")
    assert res.status_code == 200
    data = res.json()
    assert data["session_secret"] == "set"
    assert data["oidc"]["client_secret"] == "set"
    assert data["service_accounts"]["sa-ci"]["token_sha256"] == "set"
    assert "rule_profiles" in data


def test_viewer_cannot_start_or_edit(team_env):
    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-bob")
    audit.add_item("run-a-1", "requirement", {"text": "Req", "order": 1, "source_quote": "Req"}, "Bob", item_id="item-a-1")

    client = _client_for(cfg, audit, "Charlie", "charlie@test", ["g-a-view"])
    # Viewer cannot start a run
    res_start = client.post("/api/new/sift", data={"project": "proj-a"}, files={"file": ("test.txt", b"hello", "text/plain")}, headers={"X-Zyn-Request": "1"})
    assert res_start.status_code == 403
    assert "engineer" in res_start.json().get("error", "")

    # Viewer cannot edit
    res_edit = client.post("/api/edit", json={"kind": "edit", "item_id": "item-a-1", "fields": {"text": "new"}}, headers={"X-Zyn-Request": "1"})
    assert res_edit.status_code == 403
    assert "engineer" in res_edit.json().get("error", "")


def test_engineer_cannot_decide(team_env):
    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-alice")
    audit.add_item("run-a-1", "requirement", {"text": "Req", "order": 1, "source_quote": "Req"}, "Alice", item_id="item-a-1")

    client = _client_for(cfg, audit, "Bob", "bob@test", ["g-a-eng"])
    res = client.post("/api/decide", json={"item_id": "item-a-1", "decision": "approved"}, headers={"X-Zyn-Request": "1"})
    assert res.status_code == 403
    assert "approver" in res.json().get("error", "")


def test_decision_records_four_eyes_setting(team_env):
    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-bob")
    audit.add_item("run-a-1", "requirement", {"text": "Req", "order": 1, "source_quote": "Req"}, "Bob", item_id="item-a-1")

    # Alice is approver and did not touch item-a-1 or start run-a-1
    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    res = client.post("/api/decide", json={"item_id": "item-a-1", "decision": "approved"}, headers={"X-Zyn-Request": "1"})
    assert res.status_code == 200

    # Verify event detail contains four_eyes: True
    decisions = [e for e in audit.events() if e["action"] == "approved"]
    assert len(decisions) == 1
    assert decisions[0]["detail"].get("four_eyes") is True


def test_four_eyes_on_decide_and_bulk_skips(team_env):
    cfg, audit = team_env
    # Alice started run-a-1
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-alice")
    # item-1 edited by Alice
    audit.add_item("run-a-1", "requirement", {"text": "Req 1", "order": 1, "source_quote": "Req 1"}, "Alice", item_id="item-a-1")
    alice_p = Principal(id="oidc:https://idp#user-alice", name="Alice", email="alice@test", kind="person")
    scoped_alice = audit.scoped("proj-a", alice_p)
    scoped_alice.edit_item("item-a-1", {"text": "Req 1 edited", "order": 1, "source_quote": "Req 1"}, "Alice")

    # item-2 not edited by Alice
    audit.add_item("run-a-1", "requirement", {"text": "Req 2", "order": 2, "source_quote": "Req 2"}, "Bob", item_id="item-a-2")

    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    # Direct decide on item-a-1 is blocked
    res_dec = client.post("/api/decide", json={"item_id": "item-a-1", "decision": "approved"}, headers={"X-Zyn-Request": "1"})
    assert res_dec.status_code == 403
    assert "You edited this; someone else must decide on it." in res_dec.json().get("error", "")

    # Direct decide on finding in run Alice started is blocked
    audit.add_item("run-a-1", "finding", {"req_id": "item-a-2", "category": "vague"}, "model", item_id="finding-1")
    res_find = client.post("/api/decide", json={"item_id": "finding-1", "decision": "approved"}, headers={"X-Zyn-Request": "1"})
    assert res_find.status_code == 403
    assert "You started this run; someone else must decide on its findings." in res_find.json().get("error", "")


def test_card_shows_block_decide_reason(team_env):

    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a", started_by_id="oidc:https://idp#user-bob")
    audit.add_item("run-a-1", "requirement", {"text": "Req 1", "order": 1, "source_quote": "Req 1"}, "Bob", item_id="item-a-1")
    # Alice edits item-a-1
    alice_p = Principal(id="oidc:https://idp#user-alice", name="Alice", email="alice@test", kind="person")
    scoped_alice = audit.scoped("proj-a", alice_p)
    scoped_alice.edit_item("item-a-1", {"text": "Req 1 edited", "order": 1, "source_quote": "Req 1"}, "Alice")

    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    res = client.get("/api/runs/run-a-1")
    assert res.status_code == 200
    data = res.json()
    req_card = next(c for c in data["requirements"] if c["item_id"] == "item-a-1")
    assert req_card["decision"]["block_decide"] == "You edited this; someone else must decide on it."


def test_typed_name_label_in_audit_view(team_env):
    cfg, audit = team_env
    audit.start_run(workflow="sift-document", run_id="run-a-1", project="proj-a")
    # Event logged without actor_id (e.g. from personal mode before migration)
    audit.log_event("LegacyUser", "approved", run_id="run-a-1", object_type="requirement", object_id="req-1")
    # Event logged by AI
    audit.log_event("AI", "generated", run_id="run-a-1")

    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    res = client.get("/api/runs/run-a-1/audit")
    assert res.status_code == 200
    events = res.json()["events"]
    human_ev = next(e for e in events if "LegacyUser" in e["actor"])
    assert human_ev["actor"] == "LegacyUser (name typed, not signed in)"
    ai_ev = next(e for e in events if e["action"] == "generated")
    assert ai_ev["actor"] == "AI"


def test_project_rule_profile_used(team_env, monkeypatch):
    from harness.sift import check as sift_check

    cfg, audit = team_env
    captured_rules = []

    def mock_start(cfg, store, path, **kwargs):
        captured_rules.append(kwargs.get("rules"))
        return {"run_id": "check-1", "findings": 0}

    monkeypatch.setattr(sift_check, "start", mock_start)

    client = _client_for(cfg, audit, "Dana", "dana@test", ["g-b-eng"])
    res = client.post(
        "/api/new/check",
        data={"project": "proj-b"},
        files={"file": ("reqs.txt", b"The system shall brake.", "text/plain")},
        headers={"X-Zyn-Request": "1"},
    )
    assert res.status_code == 200
    assert captured_rules == ["strict"]


def test_tokens_endpoints(team_env):
    cfg, audit = team_env
    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])

    # 1. Initially empty
    res_list = client.get("/api/tokens")
    assert res_list.status_code == 200
    assert res_list.json() == []

    # 2. Create token
    res_create = client.post("/api/tokens", json={"label": "ci-token", "days": 30}, headers={"X-Zyn-Request": "1"})
    assert res_create.status_code == 201
    data = res_create.json()
    tok_id = data["token_id"]
    secret = data["secret"]
    assert tok_id.startswith("tok-")
    assert secret.startswith("zyn_")

    # 3. List shows token
    res_list2 = client.get("/api/tokens")
    assert res_list2.status_code == 200
    tokens = res_list2.json()
    assert len(tokens) == 1
    assert tokens[0]["token_id"] == tok_id
    assert tokens[0]["label"] == "ci-token"
    assert tokens[0]["revoked"] is False

    # 4. Revoke token
    res_rev = client.post(f"/api/tokens/{tok_id}/revoke", headers={"X-Zyn-Request": "1"})
    assert res_rev.status_code == 200
    assert res_rev.json() == {"ok": True}

    # 5. List shows revoked
    res_list3 = client.get("/api/tokens")
    assert res_list3.json()[0]["revoked"] is True


def test_cli_refuses_in_team_mode(team_env, monkeypatch):
    from harness.__main__ import main

    cfg, _ = team_env
    # Point load_config to cfg
    monkeypatch.setattr("harness.__main__.load_config", lambda *args, **kwargs: cfg)
    # Run smoke command
    code = main(["smoke"])
    assert code == 2



def test_team_server_opens_team_database_url(tmp_path: Path):
    personal_db = tmp_path / "personal.sqlite"
    team_db = tmp_path / "team.sqlite"

    team_store = AuditStore(str(team_db))
    with team_store.backend.connect() as con:
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow, project) VALUES (?,?,?,?)",
            ("run-in-team-db", "2026-11-14T10:00:00.000Z", "sift", "proj"),
        )

    team = TeamSettings(
        database_url=f"sqlite:///{team_db}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        allow_insecure_http=True,
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"proj": ProjectSettings(name="Proj", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(personal_db),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
        team=team,
    )
    claims: Claims = {
        "sub": "user-alice",
        "iss": "https://idp",
        "name": "Alice",
        "email": "alice@test",
        "groups": ["g-v"],
    }
    idp = FakeIdentityProvider(claims)
    # create_app without passing audit must open cfg.team.database_url, NOT personal_db
    app = create_app(cfg, idp=idp)
    client = TestClient(app, base_url="http://testserver")
    client.get("/auth/callback")
    res = client.get("/api/runs?project=proj")
    assert res.status_code == 200
    run_ids = [r["run_id"] for r in res.json()]
    assert "run-in-team-db" in run_ids


def test_team_server_refuses_old_schema(tmp_path: Path, monkeypatch):
    from harness.audit import migrations

    team_db = tmp_path / "old_team.sqlite"
    team_store = AuditStore(str(team_db))
    monkeypatch.setattr(migrations, "LATEST_VERSION", 3)

    team = TeamSettings(
        database_url=f"sqlite:///{team_db}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        allow_insecure_http=True,
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"proj": ProjectSettings(name="Proj", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(team_db),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={"fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a")},
        team=team,
    )
    with pytest.raises(RuntimeError, match=r"Database schema is version 2, this Zyn needs 3\. Run: zyn upgrade"):
        create_app(cfg, audit=team_store)


def test_health_reports_database_schema_version(tmp_path: Path):
    team_db = tmp_path / "team_health.sqlite"
    team_store = AuditStore(str(team_db))

    team = TeamSettings(
        database_url=f"sqlite:///{team_db}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        allow_insecure_http=True,
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"proj": ProjectSettings(name="Proj", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(team_db),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
        team=team,
    )
    app = create_app(cfg, audit=team_store)
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["schema"] == 2


def test_tokens_and_sessions_mixed_for_four_eyes(team_env):
    """Item 1: A token edit by Alice cannot be approved by Alice via session cookie."""
    cfg, audit = team_env

    # Alice signs in via web first and creates a token via API
    alice_web = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng", "g-a-appr"])
    res_tok = alice_web.post(
        "/api/tokens",
        json={"label": "pat-alice"},
        headers={"X-Zyn-Request": "1"},
    )
    assert res_tok.status_code == 201
    secret = res_tok.json()["secret"]

    app = alice_web.app
    # Alice edits an item using bearer token
    # Create item in proj-a
    run_id = audit.start_run("sift", project="proj-a")
    item_id = audit.add_item(run_id, "requirement", {"text": "v1 text"}, "model:fake-gen")

    bearer_client = TestClient(app)
    # Edit item as Alice with token
    res = bearer_client.post(
        "/api/edit",
        json={"item_id": item_id, "fields": {"text": "v2 text by alice via token"}},
        headers={"Authorization": f"Bearer {secret}", "X-Zyn-Request": "1"},
    )
    assert res.status_code == 200

    # Alice opens browser (session cookie) and tries to approve her own edit
    res_approve = alice_web.post(
        "/api/decide",
        json={"item_id": item_id, "decision": "approved"},
        headers={"X-Zyn-Request": "1"},
    )
    assert res_approve.status_code == 403
    assert "You edited this" in res_approve.json()["error"]

    # Bob (approver) decides on it -> succeeds
    bob_web = _client_for(cfg, audit, "Bob", "bob@test", ["g-a-appr"])
    res_bob = bob_web.post(
        "/api/decide",
        json={"item_id": item_id, "decision": "approved"},
        headers={"X-Zyn-Request": "1"},
    )
    assert res_bob.status_code == 200
    assert audit.status(item_id) == "approved"
    # Verify four_eyes was recorded
    dec_event = [e for e in audit.events(run_id=run_id) if e["action"] == "approved"][-1]
    assert dec_event["detail"]["four_eyes"] is True


def test_carry_over_by_engineer(team_env):
    """Item 2: carry_over checks decide rights and four-eyes per finding."""
    cfg, audit = team_env
    # Start run in proj-a by Alice
    alice_p = Principal(id="user-alice", name="Alice", email="alice@test", kind="person")
    scoped_a = audit.scoped("proj-a", alice_p)
    run_id = scoped_a.start_run("check")

    # Add candidate finding with prior decision
    finding_id = scoped_a.add_item(
        run_id,
        "finding",
        {
            "category": "ambiguity",
            "source": "code",
            "prior": {"decision": "approved", "by": "Dave", "run_id": "old-run-1", "comment": "accepted"},
        },
        "model:fake-gen",
    )

    # 1. Alice is an engineer only (not approver) -> carry_over skips the finding
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])
    res = alice_client.post(f"/api/runs/{run_id}/actions/carry_over", json={}, headers={"X-Zyn-Request": "1"})
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 0
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["item_id"] == finding_id
    assert audit.status(finding_id) == "proposed"

    # 2. Bob is an approver (did not start run) -> carry_over succeeds
    bob_client = _client_for(cfg, audit, "Bob", "bob@test", ["g-a-appr"])
    res_bob = bob_client.post(f"/api/runs/{run_id}/actions/carry_over", json={}, headers={"X-Zyn-Request": "1"})
    assert res_bob.status_code == 200
    data_bob = res_bob.json()
    assert data_bob["count"] == 1
    assert data_bob["skipped"] == []
    assert audit.status(finding_id) == "approved"


def test_revoke_person_stops_tokens(team_env):
    """Item 3: revoking a person stops their personal access tokens."""
    cfg, audit = team_env
    from harness.team.tokens import create_token

    alice_p = Principal(id="user-alice", name="Alice", email="alice@test", kind="person")
    audit.log_event("Alice", "signed_in", actor_id="user-alice", detail={"groups": ["g-a-eng"]})
    _, secret = create_token(audit, alice_p, "pat-alice")

    app = create_app(cfg, audit=audit)
    client = TestClient(app)

    # Token works initially
    res = client.get("/api/runs?project=proj-a", headers={"Authorization": f"Bearer {secret}"})
    assert res.status_code == 200

    # Revoke Alice via person_revoked event
    audit.log_event("admin", "person_revoked", detail={"person_id": "user-alice"})

    # Token must now fail
    res_after = client.get("/api/runs?project=proj-a", headers={"Authorization": f"Bearer {secret}"})
    assert res_after.status_code == 401


def test_token_lifetime_capped_at_configured_days(team_env):
    """Item 4: requesting 36500 days is capped at team.token_days (90 days)."""
    from datetime import datetime

    cfg, audit = team_env
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])

    res = alice_client.post(
        "/api/tokens",
        json={"label": "huge-lifetime-token", "days": 36500},
        headers={"X-Zyn-Request": "1"},
    )
    assert res.status_code == 201
    token_id = res.json()["token_id"]

    # Check token in DB
    with audit.backend.connect() as con:
        row = con.execute("SELECT created_at, expires_at FROM tokens WHERE token_id=?", (token_id,))[0]

    created = datetime.fromisoformat(row["created_at"])
    expires = datetime.fromisoformat(row["expires_at"])
    delta_days = (expires - created).total_seconds() / 86400
    assert delta_days <= cfg.team.token_days + 1  # Capped at 90 days, not 36500!


def test_admin_upload_project_traversal_refused(team_env, tmp_path):
    """Item 5: Admin cannot specify project='../zz' to write outside uploads."""
    cfg, audit = team_env
    admin_client = _client_for(cfg, audit, "Admin", "admin@test", ["g-admin"])

    req_csv = tmp_path / "reqs.csv"
    req_csv.write_text("ext_id,text\nREQ-1,Text 1\n", encoding="utf-8")

    with open(req_csv, "rb") as f:
        res = admin_client.post(
            "/api/new/check",
            data={"project": "../zz"},
            files={"file": ("reqs.csv", f, "text/csv")},
            headers={"X-Zyn-Request": "1"},
        )
    assert res.status_code == 404
    assert "Unknown project" in res.json()["error"]
    assert not (Path("runs") / "zz").exists()


def test_sift_runs_in_config_filtered_by_project(team_env):
    """Item 6a: /api/config does not leak other projects' run IDs in sift_runs."""
    cfg, audit = team_env
    # Start sift runs in proj-a and proj-b
    audit.start_run("sift", run_id="run-sift-a", project="proj-a")
    audit.start_run("sift", run_id="run-sift-b", project="proj-b")

    # Alice is only in proj-a
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-view"])
    res = alice_client.get("/api/config?project=proj-a")
    assert res.status_code == 200
    sift_runs = res.json()["sift_runs"]
    assert "run-sift-a" in sift_runs
    assert "run-sift-b" not in sift_runs

    # Even without ?project query parameter, Alice must not see proj-b runs
    res_no_proj = alice_client.get("/api/config")
    assert res_no_proj.status_code == 200
    assert "run-sift-b" not in res_no_proj.json()["sift_runs"]


def test_decide_other_project_returns_404_before_code_check(team_env):
    """Item 6b: decide on another project's item returns 404 before code check / AI objection."""
    cfg, audit = team_env
    # Run in proj-b has a test spec with code problems
    run_b = audit.start_run("forge", run_id="run-b-spec", project="proj-b")
    spec_id = audit.add_item(
        run_b,
        "test_spec",
        {"title": "Spec with problems", "problems": ["Syntax error in test spec"]},
        "model:fake-gen",
    )

    # Alice is only in proj-a
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-appr"])
    res = alice_client.post(
        "/api/decide",
        json={"item_id": spec_id, "decision": "approved"},
        headers={"X-Zyn-Request": "1"},
    )
    # Must return 404 (No such item), NOT 400 (Fails the code checks)!
    assert res.status_code == 404
    assert res.json()["error"] == "No such item"


def test_jobs_from_another_project_returns_404(team_env):
    """Item 6c: /api/jobs/{id} returns 404 for jobs belonging to another project."""
    cfg, audit = team_env
    # Run in proj-b
    run_b = audit.start_run("check", run_id="run-b-job", project="proj-b")

    # Bob (in proj-b) starts job
    bob_client = _client_for(cfg, audit, "Bob", "bob@test", ["g-b-eng"])
    app = bob_client.app
    job_info = app.state.jobs.start(run_b, "Running analysis", lambda: {"done": True})
    job_id = job_info["id"]

    # Bob can see his job
    assert bob_client.get(f"/api/jobs/{job_id}").status_code == 200

    # Alice (in proj-a) gets 404!
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-view"])
    res_alice = alice_client.get(f"/api/jobs/{job_id}")
    assert res_alice.status_code == 404


def test_score_key_path_outside_project_refused(team_env, tmp_path):
    """Item 6d: score action confines key_path to project's uploads folder."""
    cfg, audit = team_env
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])

    run_a = audit.start_run("check", run_id="run-a-score", project="proj-a")
    # Attempt to score against a file outside project uploads
    secret_file = tmp_path / "secret.json"
    secret_file.write_text("{}", encoding="utf-8")

    res = alice_client.post(
        f"/api/runs/{run_a}/actions/score",
        json={"key_path": str(secret_file)},
        headers={"X-Zyn-Request": "1"},
    )
    assert res.status_code == 404
    assert "Answer key file not found" in res.json()["error"]


def test_upload_streaming_size_limit_and_unique_filenames(team_env):
    """Item 9: upload streaming enforces size limit and stored files have unique per-upload folders."""
    from harness.api import server

    cfg, audit = team_env
    # Set limit to 1MB
    cfg.team.max_upload_mb = 1
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])

    # 1. Upload file exceeding 1MB (2MB of content)
    big_content = b"x" * (2 * 1024 * 1024)
    res = alice_client.post(
        "/api/new/check",
        data={"project": "proj-a"},
        files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
        headers={"X-Zyn-Request": "1"},
    )
    assert res.status_code == 413
    assert "File is over 1 MB" in res.json()["error"]

    # Verify no partial big.csv file left behind
    upload_dir = server.UPLOADS / "proj-a"
    if upload_dir.exists():
        assert not any("big" in p.name for p in upload_dir.rglob("*"))

    # 2. Upload two files with identical original names
    valid_csv = b"ext_id,text\nREQ-1,Hello\n"
    res1 = alice_client.post(
        "/api/new/check",
        data={"project": "proj-a"},
        files={"file": ("reqs.csv", io.BytesIO(valid_csv), "text/csv")},
        headers={"X-Zyn-Request": "1"},
    )
    assert res1.status_code == 200

    res2 = alice_client.post(
        "/api/new/check",
        data={"project": "proj-a"},
        files={"file": ("reqs.csv", io.BytesIO(valid_csv), "text/csv")},
        headers={"X-Zyn-Request": "1"},
    )
    assert res2.status_code == 200

    # Both files must exist in distinct per-upload directories with their original name
    files = list(upload_dir.rglob("reqs.csv"))
    assert len(files) >= 2
    assert files[0].parent != files[1].parent


def test_bearer_token_cannot_manage_tokens(team_env):
    """Item 1: A bearer token cannot create, list or revoke tokens (must be a browser session)."""
    cfg, audit = team_env
    alice_web = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])
    res = alice_web.post("/api/tokens", json={"label": "pat-1"}, headers={"X-Zyn-Request": "1"})
    assert res.status_code == 201
    secret = res.json()["secret"]
    token_id = res.json()["token_id"]

    # Bearer token calling /api/tokens must get 403
    app = alice_web.app
    bearer_client = TestClient(app)
    res_create = bearer_client.post(
        "/api/tokens",
        json={"label": "child-token"},
        headers={"Authorization": f"Bearer {secret}", "X-Zyn-Request": "1"},
    )
    assert res_create.status_code == 403
    assert "Tokens can only be managed from a browser session" in res_create.json()["error"]

    res_list = bearer_client.get(
        "/api/tokens",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert res_list.status_code == 403

    res_revoke = bearer_client.post(
        f"/api/tokens/{token_id}/revoke",
        headers={"Authorization": f"Bearer {secret}", "X-Zyn-Request": "1"},
    )
    assert res_revoke.status_code == 403


def test_personal_mode_two_uploads_same_test_names_and_finding_ids(tmp_path):
    """Item 2: Personal mode preserves original filename in per-upload folder so test names and finding ids match."""
    from harness.api.server import create_app
    from harness.audit.store import AuditStore
    from harness.config import HarnessConfig, Profile

    db_path = tmp_path / "personal.sqlite"
    audit = AuditStore(str(db_path))
    cfg = HarnessConfig(
        db_path=str(db_path),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={"fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a")},
        team=None,
    )
    app = create_app(cfg, audit=audit)
    client = TestClient(app)

    test_code = (
        b"def test_speed_limit():\n"
        b"    # REQ-1\n"
        b"    speed = 120\n"
        b"    assert speed <= 100\n"
    )

    # Upload 1
    res1 = client.post(
        "/api/new/tests",
        data={"reviewer": "Alice"},
        files={"file": ("test_speed.py", io.BytesIO(test_code), "text/plain")},
    )
    assert res1.status_code == 200
    run1 = res1.json()["run_id"]
    items1 = audit.list_items(run1)
    finding_ids1 = [item["item_id"] for item in items1 if item["item_type"] == "finding"]
    unit_names1 = [
        item["payload"].get("unit") or item["payload"].get("source")
        for item in items1
        if item["item_type"] == "finding"
    ]

    # Upload 2 with identical file
    res2 = client.post(
        "/api/new/tests",
        data={"reviewer": "Alice"},
        files={"file": ("test_speed.py", io.BytesIO(test_code), "text/plain")},
    )
    assert res2.status_code == 200
    run2 = res2.json()["run_id"]
    items2 = audit.list_items(run2)
    finding_ids2 = [item["item_id"] for item in items2 if item["item_type"] == "finding"]
    unit_names2 = [
        item["payload"].get("unit") or item["payload"].get("source")
        for item in items2
        if item["item_type"] == "finding"
    ]

    # Finding IDs and unit/test names must match across uploads of the same file
    assert finding_ids1 == finding_ids2
    assert unit_names1 == unit_names2


def test_jobs_without_run_id_record_project_and_principal(team_env):
    """Item 3: /api/jobs/{id} checks project and principal even when job has run_id=None."""
    cfg, audit = team_env
    alice_client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-eng"])
    app = alice_client.app

    # Start job on behalf of Alice in proj-a with run_id=None (like new/sift or new/forge)
    job_info = app.state.jobs.start(
        None,
        "Sifting document without run_id yet",
        lambda: {"new_run_id": "run-created-later"},
        project="proj-a",
        principal_id="oidc:https://idp#user-alice",
    )
    job_id = job_info["id"]

    # Alice can read her own job
    res_alice = alice_client.get(f"/api/jobs/{job_id}")
    assert res_alice.status_code == 200

    # Bob (in proj-b, different project) gets 404
    bob_client = _client_for(cfg, audit, "Bob", "bob@test", ["g-b-view"], app=app)
    res_bob = bob_client.get(f"/api/jobs/{job_id}")
    assert res_bob.status_code == 404

    # Charlie (viewer in proj-a, colleague on the same project) CAN follow the job's progress (200)
    charlie_client = _client_for(cfg, audit, "Charlie", "charlie@test", ["g-a-view"], app=app)
    res_charlie = charlie_client.get(f"/api/jobs/{job_id}")
    assert res_charlie.status_code == 200

    # Admin CAN read it
    admin_client = _client_for(cfg, audit, "Admin", "admin@test", ["g-admin"], app=app)
    res_admin = admin_client.get(f"/api/jobs/{job_id}")
    assert res_admin.status_code == 200


def test_logout_invalidates_session_cookie(team_env):
    """Logout is POST with X-Zyn-Request, invalidates only that session ID."""
    cfg, audit = team_env
    alice_client1 = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-view"])
    app = alice_client1.app
    # Alice signs in on a second device (separate session)
    alice_client2 = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-view"], app=app)

    # Both sessions work initially
    assert alice_client1.get("/api/runs?project=proj-a").status_code == 200
    assert alice_client2.get("/api/runs?project=proj-a").status_code == 200

    # GET /auth/logout is rejected (405)
    assert alice_client1.get("/auth/logout").status_code == 405

    # POST without X-Zyn-Request is rejected (403)
    assert alice_client1.post("/auth/logout").status_code == 403

    # Copy session cookie from client 1
    cookie1 = alice_client1.cookies.get("session")

    # Logout client 1
    res_logout = alice_client1.post("/auth/logout", headers={"X-Zyn-Request": "1"})
    assert res_logout.status_code == 200

    # Client 1 / stolen cookie 1 is rejected (401)
    stolen_client = TestClient(app)
    stolen_client.cookies.set("session", cookie1)
    res_stolen = stolen_client.get("/api/runs?project=proj-a")
    assert res_stolen.status_code == 401
    assert res_stolen.json()["error"] == "Sign in first."

    # Client 2 (different device/session) STILL works!
    assert alice_client2.get("/api/runs?project=proj-a").status_code == 200


def test_viewer_upload_rejected_before_parsing_body(team_env):
    """Viewer cannot start a run and gets 403 before a large body is taken in."""
    cfg, audit = team_env
    cfg.team.max_upload_mb = 1
    viewer_client = _client_for(cfg, audit, "Charlie", "charlie@test", ["g-a-view"])

    # 3MB upload (exceeding the 1MB upload limit)
    big_content = b"x" * (3 * 1024 * 1024)
    res = viewer_client.post(
        "/api/new/check?project=proj-a",
        files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
        headers={"X-Zyn-Request": "1"},
    )
    # Must get 403 (role check failed) rather than 413 (file size exceeded)
    assert res.status_code == 403


def test_log_event_does_not_mutate_caller_detail(tmp_path):
    """Item 7: log_event makes a copy of the caller's detail dict."""
    from harness.team.principal import Principal

    store = AuditStore(str(tmp_path / "audit.sqlite"))
    token_principal = Principal(id="u1", name="Alice", email="alice@test", kind="token", token_id="tok-123")
    scoped = store.scoped("proj-a", token_principal)

    caller_detail = {"foo": "bar"}
    scoped.log_event("Alice", "custom_action", detail=caller_detail)

    assert caller_detail == {"foo": "bar"}
    assert "token_id" not in caller_detail


def test_revoke_person_cli_requires_as_and_records_actor(team_env, monkeypatch):
    """revoke-person requires --as, writes actor as that name, object_id as victim, actor_id None."""
    from harness.__main__ import main

    cfg, audit = team_env
    monkeypatch.setattr("harness.__main__.load_config", lambda *args, **kwargs: cfg)

    # Calling without --as fails (exit code 2)
    with pytest.raises(SystemExit):
        main(["revoke-person", "oidc:https://idp#victim"])

    # Calling with --as succeeds
    code = main(["revoke-person", "oidc:https://idp#victim", "--as", "AdminEve"])
    assert code == 0

    # Verify event in store
    events = audit.events()
    rev_events = [e for e in events if e["action"] == "person_revoked"]
    assert len(rev_events) == 1
    rev = rev_events[0]
    assert rev["actor"] == "AdminEve"
    assert rev["object_id"] == "oidc:https://idp#victim"
    assert rev["actor_id"] is None


def test_serve_fake_sign_in_refused_without_dev(team_env, monkeypatch, capsys):
    from harness.__main__ import main

    cfg, _ = team_env
    monkeypatch.setattr("harness.__main__.load_config", lambda *args, **kwargs: cfg)
    monkeypatch.delenv("ZYN_DEV", raising=False)

    code = main(["serve", "--team", "--fake-sign-in", "Alice,g-a-eng"])
    assert code == 2
    err = capsys.readouterr().err
    assert "serve --fake-sign-in requires ZYN_DEV=1 in environment." in err


def test_serve_fake_sign_in_authenticates(team_env):
    cfg, audit = team_env
    app = create_app(cfg, audit=audit, fake_sign_in=("Alice", ["g-a-eng"]))
    client = TestClient(app)

    res = client.get("/auth/login", follow_redirects=True)
    assert res.status_code == 200

    cfg_res = client.get("/api/config?project=proj-a")
    assert cfg_res.status_code == 200
    data = cfg_res.json()
    assert data["person"]["name"] == "Alice"
    proj = next(p for p in data["projects"] if p["id"] == "proj-a")
    assert proj["role"] == "engineer"

    events = audit.events()
    sign_ins = [e for e in events if e["action"] == "signed_in"]
    assert len(sign_ins) >= 1
    assert sign_ins[-1]["actor"] == "Alice"


def test_admin_without_project_role_cannot_decide_or_edit_and_logs_project(team_env, capsys):
    cfg, audit = team_env
    audit.start_run(
        workflow="sift-document",
        run_id="run-a-admin-test",
        project="proj-a",
        started_by_id="oidc:https://idp#user-bob",
    )
    audit.add_item(
        "run-a-admin-test",
        "finding",
        {"title": "f1"},
        "Bob",
        item_id="item-a-admin-test",
    )

    admin_client = _client_for(cfg, audit, "AdminEve", "eve@test", ["g-admin"])

    # Attempt to decide without a project role
    res_decide = admin_client.post(
        "/api/decide",
        json={"item_id": "item-a-admin-test", "decision": "approved"},
        headers={"X-Zyn-Request": "1"},
    )
    assert res_decide.status_code == 403
    assert "do not have access" in res_decide.json()["error"].lower()

    # Attempt to edit without a project role
    res_edit = admin_client.post(
        "/api/edit",
        json={"item_id": "item-a-admin-test", "content": {"title": "f2"}},
        headers={"X-Zyn-Request": "1"},
    )
    assert res_edit.status_code == 403

    # Check access logs captured to stderr
    err_output = capsys.readouterr().err
    logs = [json.loads(line) for line in err_output.strip().splitlines() if line.startswith("{") and "403" in line]
    assert len(logs) >= 2
    for log in logs:
        assert log["status"] == 403
        assert log["project"] == "proj-a"
        assert log["principal_id"] == "oidc:https://idp#user-admineve"


def test_service_account_cannot_decide_via_api(team_env):
    cfg, audit = team_env
    audit.start_run(
        workflow="sift-document",
        run_id="run-a-sa-test",
        project="proj-a",
        started_by_id="oidc:https://idp#user-bob",
    )
    audit.add_item(
        "run-a-sa-test",
        "finding",
        {"title": "f1"},
        "Bob",
        item_id="item-a-sa-test",
    )

    app = create_app(cfg, audit=audit)
    client = TestClient(app)

    # sa-ci token is 'password' (sha256 in team_env is 5e884898...)
    res = client.post(
        "/api/decide",
        json={"item_id": "item-a-sa-test", "decision": "approved"},
        headers={"Authorization": "Bearer password", "X-Zyn-Request": "1"},
    )
    assert res.status_code == 403
    assert "Service accounts cannot decide findings" in res.json()["error"]


def test_session_absolute_timeout_after_session_hours(team_env):
    cfg, audit = team_env
    client = _client_for(cfg, audit, "Alice", "alice@test", ["g-a-view"])

    # Normal session works
    res1 = client.get("/api/config?project=proj-a")
    assert res1.status_code == 200

    # Setting session_hours = 0 causes absolute session timeout check to fail
    assert cfg.team is not None
    cfg.team.session_hours = 0

    res2 = client.get("/api/config?project=proj-a")
    assert res2.status_code == 401
    assert "Sign in first." in res2.json()["error"]



