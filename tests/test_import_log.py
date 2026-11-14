from __future__ import annotations

from pathlib import Path

import pytest

from harness.audit.store import AuditStore
from harness.evidence import audit_chain, verify_chain
from harness.team.importlog import import_log


def _populate_sample_store(path: Path, run_id: str = "run-1") -> AuditStore:
    store = AuditStore(path)
    with store.backend.connect() as con:
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow, project) VALUES (?,?,?,?)",
            (run_id, "2026-11-14T10:00:00.000Z", "sift", None),
        )
    item_id = store.add_item(
        run_id, "requirement", {"text": "Speed shall not exceed 120 km/h"}, "Alice"
    )
    store.log_event("Alice", "generated", run_id=run_id, object_id=item_id)
    store.decide(item_id, "approved", "Alice")
    return store


def test_import_keeps_ids_and_evidence_head(tmp_path: Path):
    src_path = tmp_path / "personal.sqlite"
    store_src = _populate_sample_store(src_path, "run-src-1")
    runs = store_src.list_runs()
    run_id = runs[0]["run_id"]

    chain_before = audit_chain(store_src, run_id)
    valid_before, _ = verify_chain(chain_before)
    assert valid_before is True

    target_path = tmp_path / "team.sqlite"
    store_target = AuditStore(target_path)

    res = import_log(src_path, store_target, project="brake")
    assert res["runs"] == 1
    assert res["event_offset"] == 0
    assert res["skipped_runs"] == []

    # Check evidence chain after import matches head
    chain_after = audit_chain(store_target, run_id)
    assert chain_after["head"] == chain_before["head"]
    valid_after, _ = verify_chain(chain_after)
    assert valid_after is True


def test_import_twice_skips_runs(tmp_path: Path):
    src_path = tmp_path / "personal.sqlite"
    store_src = _populate_sample_store(src_path, "run-src-1")
    run_id = store_src.list_runs()[0]["run_id"]

    target_path = tmp_path / "team.sqlite"
    store_target = AuditStore(target_path)

    res1 = import_log(src_path, store_target, project="brake")
    assert res1["runs"] == 1
    assert res1["skipped_runs"] == []

    res2 = import_log(src_path, store_target, project="brake")
    assert res2["runs"] == 0
    assert res2["skipped_runs"] == [run_id]


def test_second_log_shifted_and_offset_logged(tmp_path: Path):
    src1_path = tmp_path / "personal1.sqlite"
    store1 = _populate_sample_store(src1_path, "run-1")
    store1.list_runs()[0]["run_id"]

    src2_path = tmp_path / "personal2.sqlite"
    store2 = _populate_sample_store(src2_path, "run-2")
    run2 = store2.list_runs()[0]["run_id"]

    # Export evidence from second log before import
    chain2_before = audit_chain(store2, run2)
    valid2, _ = verify_chain(chain2_before)
    assert valid2 is True

    target_path = tmp_path / "team.sqlite"
    store_target = AuditStore(target_path)

    res1 = import_log(src1_path, store_target, project="brake")
    assert res1["event_offset"] == 0

    res2 = import_log(src2_path, store_target, project="brake")
    assert res2["event_offset"] > 0

    # Imported event log records log_imported event
    events = store_target.events()
    import_events = [e for e in events if e["action"] == "log_imported"]
    assert len(import_events) == 2
    assert import_events[1]["detail"]["event_offset"] == res2["event_offset"]


def test_imported_rows_have_no_actor_id(tmp_path: Path):
    src_path = tmp_path / "personal.sqlite"
    store_src = _populate_sample_store(src_path, "run-src-1")
    run_id = store_src.list_runs()[0]["run_id"]

    target_path = tmp_path / "team.sqlite"
    store_target = AuditStore(target_path)
    import_log(src_path, store_target, project="brake")

    runs = store_target.scoped("brake").list_runs()
    assert len(runs) == 1
    assert runs[0]["started_by_id"] is None

    items = store_target.scoped("brake").list_items(run_id)
    assert len(items) == 1
    assert items[0]["created_by_id"] is None

    events = store_target.scoped("brake").events(run_id=run_id)
    assert all(e["actor_id"] is None for e in events)



def test_import_is_atomic_on_failure(tmp_path: Path, monkeypatch):
    src_path = tmp_path / "personal_atomic.sqlite"
    _populate_sample_store(src_path, "run-src-atomic")

    target_path = tmp_path / "team_atomic.sqlite"
    store_target = AuditStore(target_path)

    # Monkeypatch execute during event insertion to simulate a mid-import failure
    original_execute = store_target.backend.connect

    class FailingConn:
        def __init__(self, con):
            self.con = con
            self.insert_count = 0

        def execute(self, sql, args=()):
            if "INSERT INTO events" in sql:
                self.insert_count += 1
                if self.insert_count > 1:
                    raise RuntimeError("Simulated failure mid-events insertion")
            return self.con.execute(sql, args)

        def insert(self, sql, args=()):
            return self.con.insert(sql, args)

        def claim_lock(self):
            return self.con.claim_lock()

        def commit(self):
            return self.con.commit()

        def rollback(self):
            return self.con.rollback()

    from contextlib import contextmanager

    @contextmanager
    def failing_connect():
        with original_execute() as c:
            yield FailingConn(c)

    monkeypatch.setattr(store_target.backend, "connect", failing_connect)

    with pytest.raises(RuntimeError, match="Simulated failure"):
        import_log(src_path, store_target, project="brake")

    # Verify that target has 0 runs, 0 items, 0 events (everything rolled back)
    restore_target = AuditStore(target_path)
    assert len(restore_target.list_runs()) == 0
    assert len(restore_target.items_of_type("requirement")) == 0


def test_import_keeps_ids_when_no_collision(tmp_path: Path):
    # Target already has events 100..102
    target_path = tmp_path / "team_disjoint.sqlite"
    store_target = AuditStore(target_path)
    with store_target.backend.connect() as con:
        con.execute(
            "INSERT INTO events (event_id, ts, actor, action) VALUES (100, '2026-11-14T10:00:00.000Z', 'System', 'init')"
        )

    # Source has events 1..2 (no overlap with target!)
    src_path = tmp_path / "personal_disjoint.sqlite"
    _populate_sample_store(src_path, "run-disjoint")

    res = import_log(src_path, store_target, project="brake")
    # Because there was no collision between source events and target events, offset must be 0!
    assert res["event_offset"] == 0


def test_import_includes_runless_events(tmp_path: Path):
    src_path = tmp_path / "personal_runless.sqlite"
    store_src = _populate_sample_store(src_path, "run-with-runless")
    # Add a run-less event (run_id is None)
    with store_src.backend.connect() as con:
        con.execute(
            "INSERT INTO events (event_id, ts, run_id, actor, action) VALUES (999, '2026-11-14T10:05:00.000Z', NULL, 'Admin', 'config_changed')"
        )

    target_path = tmp_path / "team_runless.sqlite"
    store_target = AuditStore(target_path)
    import_log(src_path, store_target, project="brake")

    # Verify the runless event was imported
    all_events = store_target.events()
    runless = [e for e in all_events if e["action"] == "config_changed"]
    assert len(runless) == 1
    assert runless[0]["run_id"] is None


def test_import_log_cli_requires_admin_url_in_team_mode(tmp_path: Path, monkeypatch, capsys):
    from harness.__main__ import main
    from harness.config import HarnessConfig, Profile
    from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings

    team_db = tmp_path / "team_cli.sqlite"
    team = TeamSettings(
        database_url=f"sqlite:///{team_db}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"brake": ProjectSettings(name="Brake", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(team_db),
        roles={"generator": "fake-gen"},
        profiles={"fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a")},
        team=team,
    )
    monkeypatch.setattr("harness.__main__.load_config", lambda *args, **kwargs: cfg)

    src_file = tmp_path / "source.sqlite"
    _populate_sample_store(src_file)

    # Calling import-log without --admin-url in team mode must exit 2
    code = main(["import-log", str(src_file), "--project", "brake"])
    assert code == 2
    err = capsys.readouterr().err
    assert "admin-url" in err.lower()


def test_import_log_event_inside_same_transaction_and_rolls_back_on_failure(tmp_path: Path, monkeypatch):
    src_path = tmp_path / "personal_tx.sqlite"
    _populate_sample_store(src_path, "run-src-tx")

    target_path = tmp_path / "team_tx.sqlite"
    store_target = AuditStore(target_path)

    original_connect = store_target.backend.connect

    class FailingConn:
        def __init__(self, con):
            self.con = con

        def execute(self, sql, args=()):
            if "log_imported" in str(args):
                raise RuntimeError("Simulated failure during log_imported write")
            return self.con.execute(sql, args)

        def insert(self, sql, args=()):
            return self.con.insert(sql, args)

        def claim_lock(self):
            return self.con.claim_lock()

        def commit(self):
            return self.con.commit()

        def rollback(self):
            return self.con.rollback()

    from contextlib import contextmanager

    @contextmanager
    def failing_connect():
        with original_connect() as c:
            yield FailingConn(c)

    monkeypatch.setattr(store_target.backend, "connect", failing_connect)

    with pytest.raises(RuntimeError, match="Simulated failure during log_imported write"):
        import_log(src_path, store_target, project="brake")

    # Entire transaction was rolled back: no runs, no items, no imported events
    assert store_target.list_runs() == []
    assert store_target.items_of_type("req") == []
    assert [e for e in store_target.events() if e.get("action") not in ("initial_schema",)] == []


def test_probe_item_id_collision_refuses_whole_import(tmp_path: Path):
    """F1: A crafted file with an item req-b1 at version 99 under a new run in proj-a,
    plus an approved event, cannot take over the proj-b item.
    Refuse the whole import (nothing written)."""
    target_path = tmp_path / "team_target.sqlite"
    store_target = AuditStore(target_path)

    # 1. Target database has proj-b with run-b1 and item req-b1 (version 1)
    with store_target.backend.connect() as con:
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow, project) VALUES (?,?,?,?)",
            ("run-b1", "2026-11-14T10:00:00.000Z", "sift", "proj-b"),
        )
    store_target.add_item(
        "run-b1",
        "requirement",
        {"text": "Original requirement in proj-b"},
        "Bob",
        item_id="req-b1",
    )
    orig_item = store_target.get_item("req-b1")
    assert orig_item is not None
    assert orig_item["version"] == 1
    assert orig_item["payload"]["text"] == "Original requirement in proj-b"

    # 2. Crafted source file: new run run-a1 in proj-a, item req-b1 at version 99, approved event
    crafted_path = tmp_path / "crafted_collision.sqlite"
    store_crafted = AuditStore(crafted_path)
    with store_crafted.backend.connect() as con:
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow, project) VALUES (?,?,?,?)",
            ("run-a1", "2026-11-14T11:00:00.000Z", "sift", None),
        )
        con.execute(
            """
            INSERT INTO items (item_id, version, run_id, item_type, payload_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "req-b1",
                99,
                "run-a1",
                "requirement",
                '{"text": "Hijacked requirement in proj-a"}',
                "Eve",
                "2026-11-14T11:00:01.000Z",
            ),
        )
    store_crafted.log_event(
        actor="Eve",
        action="approved",
        run_id="run-a1",
        object_id="req-b1",
    )

    # 3. Attempt import into proj-a: MUST raise ValueError and write nothing
    with pytest.raises(ValueError, match="already exists"):
        import_log(crafted_path, store_target, project="proj-a")

    # 4. Target database unchanged: req-b1 still belongs to run-b1 in proj-b
    item_after = store_target.get_item("req-b1")
    assert item_after is not None
    assert item_after["version"] == 1
    assert item_after["payload"]["text"] == "Original requirement in proj-b"
    assert item_after["run_id"] == "run-b1"
    assert store_target.run_project(item_after["run_id"]) == "proj-b"
    assert not any(r["run_id"] == "run-a1" for r in store_target.list_runs())


def test_import_refuses_event_naming_item_outside_imported_runs(tmp_path: Path):
    """F1: Refuse the whole import when an imported event's object_id names an item
    not in the imported runs."""
    target_path = tmp_path / "team_target2.sqlite"
    store_target = AuditStore(target_path)

    # Target has proj-b with req-b1
    with store_target.backend.connect() as con:
        con.execute(
            "INSERT INTO runs (run_id, started_at, workflow, project) VALUES (?,?,?,?)",
            ("run-b1", "2026-11-14T10:00:00.000Z", "sift", "proj-b"),
        )
    store_target.add_item("run-b1", "requirement", {"text": "Req B"}, "Bob", item_id="req-b1")

    # Source has run-a1 with req-a1, but an event pointing at req-b1
    src_path = tmp_path / "foreign_event.sqlite"
    store_src = _populate_sample_store(src_path, "run-a1")
    store_src.log_event(
        actor="Eve",
        action="approved",
        run_id="run-a1",
        object_id="req-b1",
    )

    with pytest.raises(ValueError, match="not in the imported runs"):
        import_log(src_path, store_target, project="proj-a")

    # Nothing written
    assert not any(r["run_id"] == "run-a1" for r in store_target.list_runs())


def test_import_log_cli_rejects_unconfigured_project(tmp_path: Path, monkeypatch, capsys):
    from harness.__main__ import main
    from harness.config import HarnessConfig, Profile
    from harness.team.settings import OidcSettings, ProjectSettings, TeamSettings

    team_db = tmp_path / "team_cli2.sqlite"
    team = TeamSettings(
        database_url=f"sqlite:///{team_db}",
        public_url="http://testserver",
        session_secret="very-secret-session-key-32-chars-long",
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={"brake": ProjectSettings(name="Brake", rule_profile="default", roles={"viewer": ["g-v"]})},
        allowed_models=["fake-gen"],
    )
    cfg = HarnessConfig(
        db_path=str(team_db),
        roles={"generator": "fake-gen"},
        profiles={"fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a")},
        team=team,
    )
    monkeypatch.setattr("harness.__main__.load_config", lambda *args, **kwargs: cfg)

    src_file = tmp_path / "source2.sqlite"
    _populate_sample_store(src_file)

    # Calling import-log with unknown project must exit 2
    code = main([
        "import-log",
        str(src_file),
        "--project",
        "nonexistent",
        "--admin-url",
        f"sqlite:///{team_db}",
    ])
    assert code == 2
    err = capsys.readouterr().err
    assert "Unknown project 'nonexistent'" in err
