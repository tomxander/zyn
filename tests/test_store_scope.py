from __future__ import annotations

import threading

import pytest

from harness.audit.store import AuditStore
from harness.team.principal import Principal

P1 = Principal(id="oidc:corp#u1", name="Alice", email="alice@corp.test", kind="person")
P2 = Principal(id="oidc:corp#u2", name="Bob", email="bob@corp.test", kind="person")


def test_projects_are_walls(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)
    b = store.scoped("body", P2)

    run_a = a.start_run("sift")
    item_a = a.add_item(run_a, "finding", {"title": "f1"}, "Alice")
    a.decide(item_a, "approved", "Alice")

    # b sees nothing from a
    assert b.list_runs() == []
    assert b.items_of_type("finding") == []
    assert b.latest_decisions() == {}

    # a sees its own
    assert len(a.list_runs()) == 1
    assert a.list_runs()[0]["run_id"] == run_a
    assert len(a.items_of_type("finding")) == 1
    assert item_a in a.latest_decisions()


def test_replay_never_crosses_projects(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)
    b = store.scoped("body", P2)

    run_a = a.start_run("sift")
    a.log_event(
        "ai-reviewer",
        "generated",
        run_id=run_a,
        input_sha256="hash-in",
        prompt_sha256="hash-pr",
        model_profile="claude",
        model_requested="claude-3-7-sonnet",
        object_type="finding",
        prompt_version="v1",
        detail={"result": "valid"},
    )

    # Replay lookup in project a works
    ans_a = a.find_answer(
        input_sha256="hash-in",
        prompt_sha256="hash-pr",
        model_profile="claude",
        model_requested="claude-3-7-sonnet",
        task="finding",
        prompt_version="v1",
    )
    assert ans_a is not None
    assert ans_a["detail"] == {"result": "valid"}

    # Replay lookup in project b gets None even with identical hashes
    ans_b = b.find_answer(
        input_sha256="hash-in",
        prompt_sha256="hash-pr",
        model_profile="claude",
        model_requested="claude-3-7-sonnet",
        task="finding",
        prompt_version="v1",
    )
    assert ans_b is None


def test_scoped_writes_stamp_project_and_person(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)

    run_a = a.start_run("sift")
    run_row = a.list_runs()[0]
    assert run_row["project"] == "brake"
    assert run_row["started_by_id"] == P1.id

    assert store.run_project(run_a) == "brake"
    assert store.started_by(run_a) == P1.id

    item_id = a.add_item(run_a, "finding", {"title": "orig"}, "Alice")
    item_v1 = a.get_item(item_id, 1)
    assert item_v1 is not None
    assert item_v1["created_by_id"] == P1.id
    assert store.touched_by(item_id, P1.id) is True
    assert store.touched_by(item_id, P2.id) is False

    # Edit item with P2
    a2 = store.scoped("brake", P2)
    a2.edit_item(item_id, {"title": "edited"}, "Bob")
    item_v2 = a2.get_item(item_id, 2)
    assert item_v2 is not None
    assert item_v2["created_by_id"] == P2.id

    # Now both P1 and P2 have touched item_id
    assert store.touched_by(item_id, P1.id) is True
    assert store.touched_by(item_id, P2.id) is True

    # Check event actor_id
    events = a.events(run_id=run_a)
    assert len(events) >= 1
    # The 'edited' event logged by Bob should have Bob's actor_id
    edit_events = [e for e in events if e["action"] == "edited"]
    assert len(edit_events) == 1
    assert edit_events[0]["actor_id"] == P2.id


def test_model_created_item_has_no_created_by_id(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)

    run_a = a.start_run("sift")
    # AI model extracts requirement or creates finding
    item_id = a.add_item(run_a, "finding", {"title": "ai finding"}, "model:fake-gen")
    item_v1 = a.get_item(item_id, 1)
    assert item_v1 is not None
    assert item_v1["created_by_id"] is None
    # P1 started the run, but did NOT create the item
    assert store.touched_by(item_id, P1.id) is False

    # AI logs event
    a.log_event("ai-reviewer", "ai_reviewed", run_id=run_a, object_id=item_id)
    ev = next(e for e in a.events(run_id=run_a) if e["action"] == "ai_reviewed")
    assert ev["actor_id"] is None

    # Human Alice edits the item
    a.edit_item(item_id, {"title": "human corrected"}, "Alice")
    item_v2 = a.get_item(item_id, 2)
    assert item_v2 is not None
    assert item_v2["created_by_id"] == P1.id
    assert store.touched_by(item_id, P1.id) is True


def test_cross_project_reads_isolated(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)
    b = store.scoped("body", P2)

    run_b = b.start_run("sift")
    item_b = b.add_item(run_b, "finding", {"title": "b finding"}, "Bob")
    b.decide(item_b, "approved", "Bob")
    b.log_event("Bob", "custom_action", run_id=run_b, object_id=item_b)

    # Scoped store A must get None / KeyError / empty on B's identifiers
    assert a.get_item(item_b) is None
    assert a.list_items(run_b) == []
    with pytest.raises(KeyError):
        a.status(item_b)
    assert a.latest_decision(item_b) is None
    assert a.events(run_id=run_b) == []


def test_scoped_none_filters_project_none(store_backend):
    store = store_backend
    run_none = store.scoped(None, P1).start_run("sift")
    run_brake = store.scoped("brake", P1).start_run("sift")

    none_store = store.scoped(None, P1)
    runs_none = [r["run_id"] for r in none_store.list_runs()]
    assert run_none in runs_none
    assert run_brake not in runs_none

    # Unscoped store (ALL_PROJECTS) sees both
    runs_all = [r["run_id"] for r in store.list_runs()]
    assert run_none in runs_all
    assert run_brake in runs_all


def test_job_thread_keeps_scope(store_backend):
    store = store_backend
    a = store.scoped("brake", P1)
    run_a = a.start_run("sift")

    error: list[Exception] = []

    def worker(scoped_store: AuditStore, r_id: str):
        try:
            scoped_store.log_event("Alice", "job_finished", run_id=r_id)
        except Exception as ex:  # noqa: BLE001
            error.append(ex)

    t = threading.Thread(target=worker, args=(a, run_a))
    t.start()
    t.join()

    assert not error
    events = a.events(run_id=run_a)
    job_events = [e for e in events if e["action"] == "job_finished"]
    assert len(job_events) == 1
    assert job_events[0]["actor_id"] == P1.id
