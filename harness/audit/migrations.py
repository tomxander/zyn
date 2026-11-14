"""Database migrations and upgrade tooling for PostgreSQL and SQLite."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.audit.backend import Backend

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "initial_schema",
        [
            """CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                workflow TEXT NOT NULL,
                note TEXT,
                project TEXT,
                started_by_id TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS items (
                item_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                item_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by_id TEXT,
                PRIMARY KEY (item_id, version)
            )""",
            """CREATE TABLE IF NOT EXISTS events (
                event_id BIGSERIAL PRIMARY KEY,
                ts TEXT NOT NULL,
                run_id TEXT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                object_type TEXT,
                object_id TEXT,
                object_version INTEGER,
                model_profile TEXT,
                provider TEXT,
                model_requested TEXT,
                model_served TEXT,
                prompt_version TEXT,
                prompt_sha256 TEXT,
                input_sha256 TEXT,
                tokens_in INTEGER,
                tokens_out INTEGER,
                latency_ms INTEGER,
                attempt INTEGER,
                detail_json TEXT,
                actor_id TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS events_answer ON events(input_sha256, prompt_sha256)",
            "CREATE INDEX IF NOT EXISTS events_object ON events(object_id, event_id)",
            "CREATE INDEX IF NOT EXISTS events_action_object ON events(action, object_id)",
            "CREATE INDEX IF NOT EXISTS events_action_actor ON events(action, actor_id)",
            """CREATE TABLE IF NOT EXISTS tokens (
                token_id TEXT PRIMARY KEY,
                sha256 TEXT UNIQUE NOT NULL,
                owner_id TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                label TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )""",
        ],
    ),
    (
        2,
        "items_seq",
        [
            "ALTER TABLE items ADD COLUMN IF NOT EXISTS seq BIGSERIAL",
        ],
    ),
]

LATEST_VERSION = max(v for v, _, _ in MIGRATIONS)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def current_version(backend: Backend) -> int:
    """Returns the latest applied schema version, or 0 if schema_versions does not exist."""
    try:
        with backend.connect() as con:
            rows = con.execute("SELECT MAX(version) AS v FROM schema_versions")
            if rows and rows[0]["v"] is not None:
                return int(rows[0]["v"])
            return 0
    except Exception as e:
        msg = str(e).lower()
        if "schema_versions" in msg and ("does not exist" in msg or "no such table" in msg):
            return 0
        if getattr(e, "pgcode", None) == "42P01":
            return 0
        raise


def upgrade(admin_url: str, app_user: str, app_password: str = "") -> list[int]:
    """Applies missing migrations, triggers and grants on PostgreSQL using admin rights."""
    import psycopg

    applied: list[int] = []
    with psycopg.connect(admin_url, autocommit=True) as con:
        # Ensure schema_versions table exists
        con.execute(
            """CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                label TEXT NOT NULL
            )"""
        )
        cur = con.execute("SELECT version FROM schema_versions")
        existing_versions = {r[0] for r in cur.fetchall()}

        for ver, label, stmts in MIGRATIONS:
            if ver in existing_versions:
                continue
            with con.transaction():
                for stmt in stmts:
                    con.execute(stmt)
                con.execute(
                    "INSERT INTO schema_versions (version, applied_at, label) VALUES (%s, %s, %s)",
                    (ver, _now(), label),
                )
            applied.append(ver)

        # Trigger function for append-only
        con.execute(
            """CREATE OR REPLACE FUNCTION no_mod_append_only() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;"""
        )
        for tbl in ("runs", "items", "events", "tokens", "schema_versions"):
            con.execute(f"DROP TRIGGER IF EXISTS no_mod_{tbl} ON {tbl}")
            con.execute(
                f"""CREATE TRIGGER no_mod_{tbl}
                BEFORE UPDATE OR DELETE OR TRUNCATE ON {tbl}
                FOR EACH STATEMENT EXECUTE FUNCTION no_mod_append_only();"""
            )

        # Permissions and role for app_user
        if app_user:
            from psycopg import sql

            cur = con.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if not cur.fetchone():
                if app_password:
                    con.execute(
                        sql.SQL("CREATE ROLE {role} LOGIN PASSWORD {pw}").format(
                            role=sql.Identifier(app_user),
                            pw=sql.Literal(app_password),
                        )
                    )
                else:
                    con.execute(
                        sql.SQL("CREATE ROLE {role} LOGIN").format(
                            role=sql.Identifier(app_user)
                        )
                    )
            elif app_password:
                con.execute(
                    sql.SQL("ALTER ROLE {role} WITH PASSWORD {pw}").format(
                        role=sql.Identifier(app_user),
                        pw=sql.Literal(app_password),
                    )
                )

            con.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON runs, items, events, tokens, schema_versions TO {role}"
                ).format(role=sql.Identifier(app_user))
            )
            con.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"
                ).format(role=sql.Identifier(app_user))
            )

    return applied
