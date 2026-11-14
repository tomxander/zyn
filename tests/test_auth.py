from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from harness.api.server import create_app
from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.team.auth import Claims, FakeIdentityProvider
from harness.team.principal import Principal
from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings
from harness.team.tokens import create_token, resolve_token, revoke_token


@pytest.fixture
def auth_cfg(tmp_path: Path) -> HarnessConfig:
    db_file = tmp_path / "auth_audit.sqlite"
    team = TeamSettings(
        database_url=f"sqlite:///{db_file}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        allow_insecure_http=True,
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={
            "brake": ProjectSettings(
                name="Brake",
                roles={"viewer": ["g-brake-view"], "engineer": ["g-brake-eng"], "approver": ["g-brake-appr"]},
            )
        },
        allowed_models=["fake-gen"],
        service_accounts={
            "sa-ci": {
                "project": "brake",
                "role": "engineer",
                "token_sha256": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # sha256("password")
            }
        },
    )
    return HarnessConfig(
        db_path=str(db_file),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
        team=team,
    )


def test_api_needs_sign_in_in_team_mode(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    app = create_app(auth_cfg, audit=audit)
    client = TestClient(app)

    # Health endpoint is public
    res_health = client.get("/api/health")
    assert res_health.status_code == 200

    # Protected endpoint without session or token answers 401
    res_runs = client.get("/api/runs")
    assert res_runs.status_code == 401
    assert res_runs.json() == {"error": "Sign in first."}


def test_personal_mode_still_uses_typed_name(tmp_path: Path):
    db_file = tmp_path / "personal_audit.sqlite"
    cfg = HarnessConfig(
        db_path=str(db_file),
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
    )
    audit = AuditStore(cfg.resolved_db_path())
    app = create_app(cfg, audit=audit)
    client = TestClient(app)

    # Read works without sign-in
    res = client.get("/api/runs")
    assert res.status_code == 200

    # Write without typed name answers 403
    res_post = client.post("/api/new/sift", json={})
    assert res_post.status_code == 403


def test_callback_creates_session_and_logs_signed_in(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    claims: Claims = {
        "sub": "user-alice",
        "iss": "https://idp",
        "name": "Alice",
        "email": "alice@corp.test",
        "groups": ["g-brake-eng"],
    }
    idp = FakeIdentityProvider(claims)
    app = create_app(auth_cfg, audit=audit, idp=idp)
    client = TestClient(app)

    # Trigger callback
    res = client.get("/auth/callback", follow_redirects=False)
    assert res.status_code in (302, 303, 307)

    # Verify signed_in event logged
    events = audit.events()
    signed_in = [e for e in events if e["action"] == "signed_in"]
    assert len(signed_in) == 1
    assert signed_in[0]["actor"] == "Alice"
    assert signed_in[0]["actor_id"] == "oidc:https://idp#user-alice"
    assert signed_in[0]["detail"]["groups"] == ["g-brake-eng"]


def test_group_removed_takes_effect_after_next_sign_in(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    claims: Claims = {
        "sub": "user-alice",
        "iss": "https://idp",
        "name": "Alice",
        "email": "alice@corp.test",
        "groups": ["g-brake-eng"],
    }
    idp = FakeIdentityProvider(claims)
    app = create_app(auth_cfg, audit=audit, idp=idp)
    client = TestClient(app)

    # First sign in with g-brake-eng
    client.get("/auth/callback")
    res1 = client.get("/api/config")
    assert res1.status_code == 200
    my_projects = res1.json().get("projects", [])
    assert any(p["id"] == "brake" and p["role"] == "engineer" for p in my_projects)

    # Now group is removed from IDP
    claims["groups"] = []
    # Next sign in updates groups
    client.get("/auth/callback")
    res2 = client.get("/api/config")
    assert res2.status_code == 200
    assert res2.json().get("projects") == []


def test_revoked_person_session_rejected(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    claims: Claims = {
        "sub": "user-alice",
        "iss": "https://idp",
        "name": "Alice",
        "email": "alice@corp.test",
        "groups": ["g-brake-eng"],
    }
    idp = FakeIdentityProvider(claims)
    app = create_app(auth_cfg, audit=audit, idp=idp)
    client = TestClient(app)

    # Alice signs in
    client.get("/auth/callback")
    res1 = client.get("/api/runs")
    assert res1.status_code == 200

    # Admin revokes Alice
    audit.log_event(
        actor="Admin",
        action="person_revoked",
        detail={"person_id": "oidc:https://idp#user-alice"},
    )

    # Next request is rejected with 401
    res2 = client.get("/api/runs")
    assert res2.status_code == 401
    assert res2.json() == {"error": "Sign in first."}


def test_cookie_write_without_header_refused(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    claims: Claims = {
        "sub": "user-alice",
        "iss": "https://idp",
        "name": "Alice",
        "email": "alice@corp.test",
        "groups": ["g-brake-eng"],
    }
    idp = FakeIdentityProvider(claims)
    app = create_app(auth_cfg, audit=audit, idp=idp)
    client = TestClient(app)

    client.get("/auth/callback")

    # POST without X-Zyn-Request header is refused (CSRF guard)
    res = client.post("/api/new/sift", json={"project": "brake"})
    assert res.status_code == 403
    assert "X-Zyn-Request" in res.json().get("error", "")

    # With header X-Zyn-Request: 1 it proceeds past CSRF check
    res_valid = client.post("/api/new/sift", json={"project": "brake"}, headers={"X-Zyn-Request": "1"})
    # May fail on missing target file, but NOT on 403 CSRF
    assert res_valid.status_code != 403


def test_token_works_until_revoked_or_expired(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    owner = Principal(id="oidc:https://idp#user-alice", name="Alice", email="alice@corp.test", kind="person")

    # Record signed_in event so owner's groups are known
    audit.log_event("Alice", "signed_in", actor_id=owner.id, detail={"groups": ["g-brake-eng"]})

    token_id, secret = create_token(audit, owner, label="my-ci-token", days=30)
    access = resolve_token(audit, auth_cfg.team, secret)
    assert access is not None
    assert access.roles.get("brake") == "engineer"

    # Revoke token
    revoke_token(audit, token_id, by=owner)
    access_after = resolve_token(audit, auth_cfg.team, secret)
    assert access_after is None


def test_service_account_token_scoped_to_its_project(auth_cfg: HarnessConfig):
    audit = AuditStore(auth_cfg.resolved_db_path())
    # Secret with sha256 matching sa-ci
    access = resolve_token(audit, auth_cfg.team, "password")
    assert access is not None
    assert access.principal.kind == "service"
    assert access.principal.name == "sa-ci"
    assert access.roles == {"brake": "engineer"}


def test_session_cookie_https_only_by_default(tmp_path: Path):
    from starlette.middleware.sessions import SessionMiddleware

    db_file = tmp_path / "team.sqlite"
    team = TeamSettings(
        database_url=f"sqlite:///{db_file}",
        public_url="http://zyn.corp.test",  # Even with http:// URL, https_only must default to True
        session_secret="very-secret-session-key-32-chars-long",
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={},
        allowed_models=[],
    )
    cfg = HarnessConfig(db_path=str(db_file), roles={}, profiles={}, team=team)
    app = create_app(cfg)

    # Inspect SessionMiddleware in app.user_middleware
    session_mw = next(m for m in app.user_middleware if m.cls == SessionMiddleware)
    assert session_mw.kwargs.get("https_only") is True

