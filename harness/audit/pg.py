"""PostgreSQL backend for AuditStore using psycopg 3 and psycopg_pool."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from harness.audit.backend import Conn

try:
    from psycopg_pool import ConnectionPool
except ImportError:
    ConnectionPool = None  # type: ignore[assignment,misc]


def _to_pg(sql: str) -> str:
    """Converts SQLite style '?' placeholders to PostgreSQL '%s' placeholders."""
    return sql.replace("?", "%s")


class PostgresConn:
    def __init__(self, raw: psycopg.Connection):
        self._raw = raw

    def execute(self, sql: str, args: Sequence[Any] = ()) -> list[dict[str, Any]]:
        pg_sql = _to_pg(sql)
        cur = self._raw.execute(pg_sql, args)
        if cur.description is None:
            return []
        return [dict(r) for r in cur.fetchall()]

    def insert(self, sql: str, args: Sequence[Any] = ()) -> int:
        pg_sql = _to_pg(sql)
        if "returning" not in pg_sql.lower():
            if "insert into events" in pg_sql.lower():
                pg_sql += " RETURNING event_id"
            else:
                pg_sql += " RETURNING 1"
        cur = self._raw.execute(pg_sql, args)
        row = cur.fetchone()
        if not row:
            return 0
        if isinstance(row, dict):
            return int(next(iter(row.values())))
        return int(row[0])

    def claim_lock(self, key: str = "work_claim") -> None:
        if self._raw.autocommit:
            self._raw.autocommit = False
        self._raw.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (key,))

    def commit(self) -> None:
        if not self._raw.autocommit:
            self._raw.commit()
            self._raw.autocommit = True

    def rollback(self) -> None:
        if not self._raw.autocommit:
            self._raw.rollback()
            self._raw.autocommit = True


class PostgresBackend:
    name: str = "postgres"

    def __init__(
        self,
        url: str,
        min_size: int = 1,
        max_size: int = 10,
        timeout: float = 5.0,
    ):
        self.url = url
        if ConnectionPool is None:
            raise RuntimeError(
                "psycopg_pool is required for PostgreSQL support. Install with: pip install 'zyn[team]'"
            )
        try:
            self._pool = ConnectionPool(
                self.url,
                min_size=min_size,
                max_size=max_size,
                kwargs={"row_factory": dict_row, "autocommit": True},
                open=False,
            )
            self._pool.open(wait=True, timeout=timeout)
        except Exception as e:
            self.close()
            raise RuntimeError(
                f"Failed to initialize PostgreSQL connection pool for {url}: {e}"
            ) from e

    def close(self) -> None:
        if self._pool is not None:
            try:
                self._pool.close()
            finally:
                self._pool = None

    @contextmanager
    def connect(self) -> Iterator[Conn]:
        if self._pool is None:
            raise RuntimeError("PostgreSQL connection pool is not open")
        with self._pool.connection() as raw:
            wrapped = PostgresConn(raw)
            try:
                yield wrapped
                if not raw.autocommit:
                    raw.commit()
                    raw.autocommit = True
            except Exception:
                if not raw.autocommit:
                    raw.rollback()
                    raw.autocommit = True
                raise

    def schema(self) -> list[str]:
        # Migrations handle PostgreSQL schema creation
        return []
