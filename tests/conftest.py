from __future__ import annotations

import os

import pytest

from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.models.fake_provider import FakeProvider
from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings


@pytest.fixture
def cfg(tmp_path) -> HarnessConfig:
    return HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        max_attempts=3,
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
    )


@pytest.fixture
def cfg_team(tmp_path) -> HarnessConfig:
    team = TeamSettings(
        database_url=f"sqlite:///{tmp_path}/team_audit.sqlite",
        public_url="https://zyn.corp.test",
        session_secret="test-session-secret-32-chars-long!",
        allow_insecure_http=True,
        oidc=OidcSettings(
            issuer="https://idp.corp.test",
            client_id="zyn-client",
            client_secret="test-oidc-secret",
        ),
        admins=["g-admin"],
        projects={
            "brake": ProjectSettings(
                name="Brake System",
                rule_profile="default",
                four_eyes=True,
                roles={
                    "viewer": ["g-brake-view"],
                    "engineer": ["g-brake-eng"],
                    "approver": ["g-brake-appr"],
                },
            ),
            "body": ProjectSettings(
                name="Body Electronics",
                rule_profile="default",
                four_eyes=True,
                roles={
                    "viewer": ["g-body-view"],
                    "engineer": ["g-body-eng"],
                    "approver": ["g-body-appr"],
                },
            ),
        },
        allowed_models=["fake-gen"],
    )
    return HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        max_attempts=3,
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
        team=team,
    )


@pytest.fixture
def audit(cfg) -> AuditStore:
    return AuditStore(cfg.resolved_db_path())


@pytest.fixture(autouse=True)
def reset_fake():
    FakeProvider.queue.clear()
    FakeProvider.calls.clear()
    yield
    FakeProvider.queue.clear()
    FakeProvider.calls.clear()


@pytest.fixture(autouse=True)
def isolate_uploads(tmp_path, monkeypatch):
    up_dir = tmp_path / "test_uploads"
    up_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("harness.api.server.UPLOADS", up_dir)



PG_URL = os.environ.get("ZYN_TEST_PG_URL")


@pytest.fixture(
    params=[
        "sqlite",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(
                not os.environ.get("ZYN_TEST_PG_URL"),
                reason="set ZYN_TEST_PG_URL to run PostgreSQL tests",
            ),
        ),
    ]
)
def store_backend(request, tmp_path):
    if request.param == "sqlite":
        store = AuditStore(tmp_path / f"audit_{request.node.name}.sqlite")
        yield store
    else:
        import psycopg

        from harness.audit.migrations import upgrade

        pg_url = os.environ["ZYN_TEST_PG_URL"]
        upgrade(pg_url, app_user="")
        store = AuditStore(pg_url)
        with psycopg.connect(pg_url, autocommit=True) as con:
            for tbl in ("runs", "items", "events", "tokens"):
                con.execute(f"ALTER TABLE {tbl} DISABLE TRIGGER ALL")
            con.execute("TRUNCATE TABLE runs, items, events, tokens CASCADE")
            for tbl in ("runs", "items", "events", "tokens"):
                con.execute(f"ALTER TABLE {tbl} ENABLE TRIGGER ALL")
        try:
            yield store
        finally:
            if hasattr(store.backend, "close"):
                store.backend.close()
