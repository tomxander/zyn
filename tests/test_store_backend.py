from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from harness.audit.store import AuditStore
from harness.evidence import _canon

OLD_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    workflow TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    item_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (item_id, version)
);
CREATE TABLE IF NOT EXISTS events (
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
    detail_json TEXT
);
"""

OLD_TRIGGERS = [
    f"CREATE TRIGGER IF NOT EXISTS no_{op}_{tbl} BEFORE {op.upper()} ON {tbl} "
    f"BEGIN SELECT RAISE(ABORT, '{tbl} is append-only'); END;"
    for tbl in ("runs", "items", "events")
    for op in ("update", "delete")
]


def test_old_sqlite_file_gains_columns_and_keeps_rows(tmp_path: Path):
    db_file = tmp_path / "old_audit.sqlite"
    # Create DB with old schema and triggers
    con = sqlite3.connect(db_file)
    con.executescript(OLD_SCHEMA)
    for trig in OLD_TRIGGERS:
        con.execute(trig)
    con.execute("INSERT INTO runs VALUES (?,?,?,?)", ("run-old-1", "2026-11-13T10:00:00.000Z", "sift", "test note"))
    con.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?)",
                ("item-1", 1, "run-old-1", "req", json.dumps({"text": "old req"}), "author", "2026-11-13T10:01:00.000Z"))
    con.execute("INSERT INTO events (ts, run_id, actor, action) VALUES (?,?,?,?)",
                ("2026-11-13T10:02:00.000Z", "run-old-1", "author", "generated"))
    con.commit()
    con.close()

    # Open with AuditStore
    store = AuditStore(db_file)
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-old-1"
    assert "project" in runs[0]
    assert "started_by_id" in runs[0]
    assert runs[0]["project"] is None
    assert runs[0]["started_by_id"] is None

    items = store.list_items("run-old-1")
    assert len(items) == 1
    assert "created_by_id" in items[0]
    assert items[0]["created_by_id"] is None

    events = store.events(run_id="run-old-1")
    assert len(events) == 1
    assert "actor_id" in events[0]
    assert events[0]["actor_id"] is None


def test_append_only_still_enforced(tmp_path: Path):
    db_file = tmp_path / "append_only.sqlite"
    store = AuditStore(db_file)
    run_id = store.start_run("sift")
    item_id = store.add_item(run_id, "finding", {"title": "f1"}, "test_user")
    event_id = store.log_event("test_user", "action1", run_id=run_id)

    with store.backend.connect() as con:
        # UPDATE runs
        with pytest.raises(Exception) as excinfo:
            con.execute("UPDATE runs SET workflow='hacked' WHERE run_id=?", (run_id,))
        assert "append-only" in str(excinfo.value).lower()

        # DELETE runs
        with pytest.raises(Exception) as excinfo:
            con.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        assert "append-only" in str(excinfo.value).lower()

        # UPDATE items
        with pytest.raises(Exception) as excinfo:
            con.execute("UPDATE items SET payload_json='{}' WHERE item_id=?", (item_id,))
        assert "append-only" in str(excinfo.value).lower()

        # DELETE items
        with pytest.raises(Exception) as excinfo:
            con.execute("DELETE FROM items WHERE item_id=?", (item_id,))
        assert "append-only" in str(excinfo.value).lower()

        # UPDATE events
        with pytest.raises(Exception) as excinfo:
            con.execute("UPDATE events SET action='hacked' WHERE event_id=?", (event_id,))
        assert "append-only" in str(excinfo.value).lower()

        # DELETE events
        with pytest.raises(Exception) as excinfo:
            con.execute("DELETE FROM events WHERE event_id=?", (event_id,))
        assert "append-only" in str(excinfo.value).lower()


def test_evidence_chain_of_pre_team_events_is_unchanged(tmp_path: Path):
    # Event dict without actor_id simulating export before this change
    e_without = {
        "event_id": 1,
        "ts": "2026-11-13T10:00:00.000Z",
        "run_id": "run-1",
        "actor": "Alice",
        "action": "generated",
        "object_type": "finding",
        "object_id": "f-1",
        "object_version": 1,
        "model_profile": None,
        "provider": None,
        "model_requested": None,
        "model_served": None,
        "prompt_version": None,
        "prompt_sha256": None,
        "input_sha256": None,
        "tokens_in": None,
        "tokens_out": None,
        "latency_ms": None,
        "attempt": None,
        "detail": None,
    }
    # Event dict with actor_id=None as returned by the new store schema
    e_with_none = dict(e_without)
    e_with_none["actor_id"] = None

    assert _canon(e_without) == _canon(e_with_none)

    # And with an explicit actor_id, it is included
    e_with_actor = dict(e_without)
    e_with_actor["actor_id"] = "oidc:user42"
    assert "actor_id" in _canon(e_with_actor)


def test_items_preserve_write_order_within_same_millisecond(store_backend, monkeypatch):
    """Items written in the same millisecond preserve write order on both backends."""
    run_id = store_backend.start_run("test-order-workflow")

    # Freeze timestamp so all items share the exact same millisecond
    monkeypatch.setattr("harness.audit.store._now", lambda: "2026-11-14T10:00:00.123Z")

    # Insert items with IDs in reverse alphabetical order
    written_ids = ["Z-REQ-003", "M-REQ-002", "A-REQ-001", "B-REQ-004"]
    for iid in written_ids:
        store_backend.add_item(
            run_id,
            "requirement",
            {"text": f"Requirement {iid}"},
            "Alice",
            item_id=iid,
        )

    # list_items must return items in write order, NOT item_id alphabetical order
    items = store_backend.list_items(run_id)
    retrieved_ids = [i["item_id"] for i in items]
    assert retrieved_ids == written_ids

    # items_of_type must also return in write order
    typed_items = store_backend.items_of_type("requirement")
    retrieved_typed_ids = [i["item_id"] for i in typed_items]
    assert retrieved_typed_ids == written_ids


def test_sqlite_url_parsing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "test_store.sqlite"
    url = f"sqlite:///{target.as_posix()}"
    store = AuditStore(url)
    assert store.path == target or store.path.resolve() == target.resolve()
    assert store.backend.name == "sqlite"

    # Relative URL
    rel_store = AuditStore("sqlite:///relative_test.sqlite")
    assert rel_store.path == Path("relative_test.sqlite")

    # Bad schemes and invalid syntax refused with clear error
    with pytest.raises(ValueError, match="Invalid sqlite database URL"):
        AuditStore("sqlite://invalid/path")

    with pytest.raises(ValueError, match="Unsupported database URL scheme"):
        AuditStore("mysql://localhost/zyn")

