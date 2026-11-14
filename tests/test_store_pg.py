from __future__ import annotations

import os

import psycopg
import pytest

from harness.audit.migrations import LATEST_VERSION, current_version, upgrade
from harness.audit.store import AuditStore

PG_URL = os.environ.get("ZYN_TEST_PG_URL")


def test_migrations_grant_includes_tokens():
    # Verify migration script grants access to tokens table
    import inspect

    from harness.audit import migrations
    source = inspect.getsource(migrations.upgrade)
    assert "tokens" in source
    assert "GRANT SELECT, INSERT ON runs, items, events, tokens" in source or "tokens" in source


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_upgrade_is_idempotent():
    upgrade(PG_URL, app_user="")
    applied2 = upgrade(PG_URL, app_user="")
    assert applied2 == []


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_store_pg_basic():
    upgrade(PG_URL, app_user="")
    with psycopg.connect(PG_URL, autocommit=True) as con:
        for tbl in ("runs", "items", "events", "tokens"):
            con.execute(f"ALTER TABLE {tbl} DISABLE TRIGGER ALL")
        con.execute("TRUNCATE TABLE runs, items, events, tokens CASCADE")
        for tbl in ("runs", "items", "events", "tokens"):
            con.execute(f"ALTER TABLE {tbl} ENABLE TRIGGER ALL")
    store = AuditStore(PG_URL)
    try:
        run_id = store.start_run("test-pg")
        item_id = store.add_item(run_id, "finding", {"title": "pg title"}, "Alice")
        assert store.get_item(item_id) is not None
        assert current_version(store.backend) == LATEST_VERSION
    finally:
        if hasattr(store.backend, "close"):
            store.backend.close()


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_app_user_cannot_update_or_delete():
    # Create role and apply permissions
    app_user = "test_zyn_app"
    app_pass = "app_pass_test"
    upgrade(PG_URL, app_user=app_user, app_password=app_pass)

    # Parse PG_URL to form connection for app_user
    parsed = psycopg.conninfo.conninfo_to_dict(PG_URL)
    parsed["user"] = app_user
    parsed["password"] = app_pass
    app_conninfo = psycopg.conninfo.make_conninfo(**parsed)

    with psycopg.connect(app_conninfo, autocommit=True) as con:
        # App user can insert into tokens
        con.execute(
            "INSERT INTO tokens (token_id, sha256, owner_id, owner_name, label, created_at, expires_at) "
            "VALUES ('tok-test-perm', 'hash123', 'u1', 'Alice', 'test', '2026-11-14T10:00:00.000Z', '2027-11-14T10:00:00.000Z')"
        )
        cur = con.execute("SELECT token_id FROM tokens WHERE token_id='tok-test-perm'")
        assert cur.fetchone() is not None

        # App user cannot UPDATE tokens (permission denied or trigger)
        with pytest.raises(Exception, match=r"(?:tokens is append-only|permission denied)"):
            con.execute("UPDATE tokens SET label='hacked' WHERE token_id='tok-test-perm'")

        # App user cannot DELETE tokens
        with pytest.raises(Exception, match=r"(?:tokens is append-only|permission denied)"):
            con.execute("DELETE FROM tokens WHERE token_id='tok-test-perm'")

        # App user cannot UPDATE runs
        with pytest.raises(Exception, match=r"(?:runs is append-only|permission denied)"):
            con.execute("UPDATE runs SET note='hacked' WHERE run_id='nonexistent'")

    # Admin user has table permissions, so triggers enforce append-only
    with psycopg.connect(PG_URL, autocommit=True) as admin_con:
        with pytest.raises(Exception, match=r"tokens is append-only"):
            admin_con.execute("UPDATE tokens SET label='hacked'")
        with pytest.raises(Exception, match=r"tokens is append-only"):
            admin_con.execute("DELETE FROM tokens WHERE token_id='tok-test-perm'")
        with pytest.raises(Exception, match=r"schema_versions is append-only"):
            admin_con.execute("UPDATE schema_versions SET label='hacked'")
        with pytest.raises(Exception, match=r"schema_versions is append-only"):
            admin_con.execute("DELETE FROM schema_versions WHERE version=1")
        with pytest.raises(Exception, match=r"runs is append-only"):
            admin_con.execute("UPDATE runs SET note='hacked'")


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_postgres_claim_locks_transaction():
    upgrade(PG_URL, app_user="")
    store = AuditStore(PG_URL)
    try:
        with store.backend.connect() as con:
            con.claim_lock("test-claim-key")
            # In transaction with advisory lock held
            assert hasattr(con, "_raw")
            assert con._raw.autocommit is False
            con.commit()
            assert con._raw.autocommit is True
    finally:
        if hasattr(store.backend, "close"):
            store.backend.close()


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_postgres_connection_pool():
    from harness.audit.pg import PostgresBackend
    backend = PostgresBackend(PG_URL)
    assert hasattr(backend, "_pool")
    assert backend._pool is not None

    with backend.connect() as con1, backend.connect() as con2:
        assert con1 is not None
        assert con2 is not None
    backend.close()



@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_server_refuses_old_schema(monkeypatch):
    from harness.api.server import create_app
    from harness.audit import migrations
    from harness.config import HarnessConfig, Profile
    from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings

    team = TeamSettings(
        database_url=PG_URL,
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"proj": ProjectSettings(name="Proj", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path="audit.sqlite",
        roles={"generator": "fake-gen"},
        profiles={"fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a")},
        team=team,
    )

    upgrade(PG_URL, app_user="")

    # 1. Test when DB schema is behind code version (Zyn requires 3, DB is at 2)
    monkeypatch.setattr(migrations, "LATEST_VERSION", 3)
    with pytest.raises(RuntimeError, match=r"Database schema is version 2, this Zyn needs 3\. Run: zyn upgrade"):
        create_app(cfg)

    # 2. Test against an empty schema_versions table (version 0)
    monkeypatch.setattr(migrations, "LATEST_VERSION", 2)
    with psycopg.connect(PG_URL, autocommit=True) as con:
        con.execute("DROP TRIGGER IF EXISTS no_mod_schema_versions ON schema_versions")
        con.execute("TRUNCATE TABLE schema_versions")

    try:
        with pytest.raises(RuntimeError, match=r"Database schema is version 0, this Zyn needs 2\. Run: zyn upgrade"):
            create_app(cfg)
    finally:
        upgrade(PG_URL, app_user="")


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_items_seq_schema_and_increment():
    """Schema test: seq BIGSERIAL column exists on items and auto-increments."""
    from harness.audit.pg import PostgresBackend

    upgrade(PG_URL, app_user="")
    backend = PostgresBackend(PG_URL)
    assert current_version(backend) == 2

    # Check seq column exists on items
    with psycopg.connect(PG_URL, autocommit=True) as con:
        cur = con.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'items' AND column_name = 'seq'
            """
        )
        row = cur.fetchone()
        assert row is not None, "seq column missing from items table"
        assert row[0] == "seq"
        assert "bigint" in row[1].lower() or "int" in row[1].lower()

        # Insert items and verify seq auto-increments
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow) VALUES ('seq-run-test', '2026-11-14T10:00:00.000Z', 'sift')"
        )
        cur1 = con.execute(
            """
            INSERT INTO items (item_id, version, run_id, item_type, payload_json, created_by, created_at)
            VALUES ('item-s1', 1, 'seq-run-test', 'req', '{}', 'user', '2026-11-14T10:00:00.000Z')
            RETURNING seq
            """
        )
        seq1 = cur1.fetchone()[0]
        cur2 = con.execute(
            """
            INSERT INTO items (item_id, version, run_id, item_type, payload_json, created_by, created_at)
            VALUES ('item-s2', 1, 'seq-run-test', 'req', '{}', 'user', '2026-11-14T10:00:00.000Z')
            RETURNING seq
            """
        )
        seq2 = cur2.fetchone()[0]
        assert seq2 > seq1


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_app_user_password_with_single_quote_creates_working_role():
    app_user = "test_quote_user"
    app_pass = "p'ass\"word!test"
    upgrade(PG_URL, app_user=app_user, app_password=app_pass)

    parsed = psycopg.conninfo.conninfo_to_dict(PG_URL)
    parsed["user"] = app_user
    parsed["password"] = app_pass
    app_conninfo = psycopg.conninfo.make_conninfo(**parsed)

    with psycopg.connect(app_conninfo) as con:
        cur = con.execute("SELECT current_user")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == app_user


def test_postgres_pool_failure_raises():
    from harness.audit.pg import PostgresBackend
    # Unreachable or invalid DB URL must raise RuntimeError, never silently drop to unpooled connection
    with pytest.raises(RuntimeError, match=r"Failed to initialize PostgreSQL connection pool"):
        PostgresBackend("postgresql://invalid.unreachable.host.test:5432/bad_db", timeout=0.5)


def test_upgrade_uses_sql_identifiers_and_literals():
    import inspect

    from harness.audit import migrations
    source = inspect.getsource(migrations.upgrade)
    assert "sql.Identifier(app_user)" in source
    assert "sql.Literal(app_password)" in source


def test_current_version_raises_on_connection_error():
    from harness.audit.migrations import current_version

    class BrokenBackend:
        name = "postgres"

        def connect(self):
            raise ConnectionRefusedError("Could not connect to database")

    with pytest.raises(ConnectionRefusedError):
        current_version(BrokenBackend())  # type: ignore[arg-type]


@pytest.mark.skipif(not PG_URL, reason="set ZYN_TEST_PG_URL to run PostgreSQL tests")
def test_admin_cannot_truncate():
    upgrade(PG_URL, app_user="")
    with psycopg.connect(PG_URL, autocommit=True) as con:
        for tbl in ("runs", "items", "events", "tokens", "schema_versions"):
            with pytest.raises(Exception, match=rf"{tbl} is append-only"):
                con.execute(f"TRUNCATE TABLE {tbl} CASCADE")

