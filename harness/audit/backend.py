"""Pluggable audit store backends (SQLite, PostgreSQL)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

SCHEMA = [
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
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    label TEXT NOT NULL
)""",
    "INSERT OR IGNORE INTO schema_versions (version, applied_at, label) VALUES (1, '2026-11-14T00:00:00.000Z', 'initial_schema')",
    "INSERT OR IGNORE INTO schema_versions (version, applied_at, label) VALUES (2, '2026-11-14T00:00:00.000Z', 'items_seq')",
]

TRIGGERS = [
    f"CREATE TRIGGER IF NOT EXISTS no_{op}_{tbl} BEFORE {op.upper()} ON {tbl} "
    f"BEGIN SELECT RAISE(ABORT, '{tbl} is append-only'); END;"
    for tbl in ("runs", "items", "events", "tokens", "schema_versions")
    for op in ("update", "delete")
]


@runtime_checkable
class Conn(Protocol):
    def execute(self, sql: str, args: Sequence[Any] = ()) -> list[dict[str, Any]]: ...
    def insert(self, sql: str, args: Sequence[Any] = ()) -> int: ...
    def claim_lock(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@runtime_checkable
class Backend(Protocol):
    name: str

    def connect(self) -> AbstractContextManager[Conn]: ...
    def schema(self) -> list[str]: ...


class SqliteConn:
    def __init__(self, raw: sqlite3.Connection):
        self._raw = raw

    def execute(self, sql: str, args: Sequence[Any] = ()) -> list[dict[str, Any]]:
        cur = self._raw.execute(sql, args)
        if cur.description is None:
            return []
        return [dict(r) for r in cur.fetchall()]

    def insert(self, sql: str, args: Sequence[Any] = ()) -> int:
        cur = self._raw.execute(sql, args)
        return int(cur.lastrowid or 0)

    def claim_lock(self) -> None:
        self._raw.execute("BEGIN IMMEDIATE")

    def commit(self) -> None:
        if self._raw.in_transaction:
            self._raw.execute("COMMIT")

    def rollback(self) -> None:
        if self._raw.in_transaction:
            self._raw.execute("ROLLBACK")


class SqliteBackend:
    name: str = "sqlite"

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[Conn]:
        raw = sqlite3.connect(self.path, timeout=30)
        raw.row_factory = sqlite3.Row
        raw.isolation_level = None  # Autocommit by default; explicit transactions when BEGIN is called
        conn = SqliteConn(raw)
        try:
            yield conn
            if raw.in_transaction:
                raw.execute("COMMIT")
        except Exception:
            if raw.in_transaction:
                raw.execute("ROLLBACK")
            raise
        finally:
            raw.close()

    def schema(self) -> list[str]:
        return [*SCHEMA, *TRIGGERS]
