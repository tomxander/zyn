"""Imports a personal SQLite audit log into a team project."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.audit.store import AuditStore
    from harness.team.settings import TeamSettings

RUNLESS_ACTION_ALLOWLIST = frozenset({
    "config_changed",
    "replayed",
    "rules_learned",
    "metrics_viewed",
    "calibration_viewed",
})


def import_log(
    sqlite_path: Path,
    target: AuditStore,
    project: str,
    team: TeamSettings | None = None,
) -> dict[str, Any]:
    if team and project not in team.projects:
        raise ValueError(
            f"Unknown project '{project}'. Configured projects: {', '.join(sorted(team.projects))}"
        )
    file_bytes = sqlite_path.read_bytes()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    con_src = sqlite3.connect(sqlite_path)
    con_src.row_factory = sqlite3.Row
    try:
        cur_runs = con_src.execute("SELECT * FROM runs ORDER BY started_at")
        src_runs = [dict(r) for r in cur_runs.fetchall()]

        cur_items = con_src.execute("SELECT * FROM items ORDER BY created_at, rowid")
        src_items = [dict(r) for r in cur_items.fetchall()]

        cur_events = con_src.execute("SELECT * FROM events ORDER BY event_id")
        src_events = [dict(r) for r in cur_events.fetchall()]
    finally:
        con_src.close()

    with target.backend.connect() as con:
        # Atomic transaction across all inserts
        con.claim_lock()
        try:
            existing_runs = {r["run_id"] for r in con.execute("SELECT run_id FROM runs")}
            existing_event_ids = {r["event_id"] for r in con.execute("SELECT event_id FROM events")}
            existing_item_ids = {r["item_id"] for r in con.execute("SELECT DISTINCT item_id FROM items")}
            existing_item_versions = {
                (r["item_id"], r["version"]) for r in con.execute("SELECT item_id, version FROM items")
            }

            skipped_runs: list[str] = []
            copied_runs: list[dict[str, Any]] = []
            for r in src_runs:
                if r["run_id"] in existing_runs:
                    skipped_runs.append(r["run_id"])
                else:
                    copied_runs.append(r)

            copied_run_ids = {r["run_id"] for r in copied_runs}
            copied_items = [i for i in src_items if i["run_id"] in copied_run_ids]

            # F1: Refuse the whole import if any imported item_id, or any (item_id, version), already exists
            for i in copied_items:
                iid = i["item_id"]
                iver = i["version"]
                if iid in existing_item_ids or (iid, iver) in existing_item_versions:
                    raise ValueError(
                        f"Cannot import item '{iid}' (version {iver}): item already exists in database."
                    )

            copied_item_ids = {i["item_id"] for i in copied_items}

            copied_events: list[dict[str, Any]] = []
            dropped_events = 0

            for e in src_events:
                rid = e.get("run_id")
                obj_id = e.get("object_id")
                if rid in copied_run_ids:
                    # F1: Refuse the whole import when an imported event's object_id names an item that is not in the imported runs
                    if obj_id and obj_id not in copied_item_ids and obj_id not in copied_run_ids:
                        raise ValueError(
                            f"Cannot import event {e.get('event_id')}: object_id '{obj_id}' is not in the imported runs."
                        )
                    copied_events.append(e)
                elif rid is None:
                    if e.get("action") in RUNLESS_ACTION_ALLOWLIST:
                        if obj_id and (obj_id in existing_item_ids or obj_id in copied_item_ids):
                            raise ValueError(
                                f"Cannot import runless event {e.get('event_id')}: object_id '{obj_id}' references an item."
                            )
                        copied_events.append(e)
                    else:
                        dropped_events += 1
                else:
                    dropped_events += 1

            # Shift event_ids only if there is an overlap with existing event_ids
            src_event_ids = {e["event_id"] for e in copied_events}
            if existing_event_ids.intersection(src_event_ids):
                offset = max(existing_event_ids) if existing_event_ids else 0
            else:
                offset = 0

            for r in copied_runs:
                con.execute(
                    "INSERT INTO runs (run_id, started_at, workflow, note, project, started_by_id) "
                    "VALUES (?,?,?,?,?,?)",
                    (r["run_id"], r["started_at"], r["workflow"], r.get("note"), project, None),
                )

            for i in copied_items:
                con.execute(
                    "INSERT INTO items (item_id, version, run_id, item_type, payload_json, "
                    "created_by, created_at, created_by_id) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        i["item_id"],
                        i["version"],
                        i["run_id"],
                        i["item_type"],
                        i["payload_json"],
                        i["created_by"],
                        i["created_at"],
                        None,
                    ),
                )

            for e in copied_events:
                new_event_id = e["event_id"] + offset
                con.execute(
                    "INSERT INTO events (event_id, ts, run_id, actor, action, object_type, "
                    "object_id, object_version, model_profile, provider, model_requested, "
                    "model_served, prompt_version, prompt_sha256, input_sha256, tokens_in, "
                    "tokens_out, latency_ms, attempt, detail_json, actor_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        new_event_id,
                        e["ts"],
                        e.get("run_id"),
                        e["actor"],
                        e["action"],
                        e.get("object_type"),
                        e.get("object_id"),
                        e.get("object_version"),
                        e.get("model_profile"),
                        e.get("provider"),
                        e.get("model_requested"),
                        e.get("model_served"),
                        e.get("prompt_version"),
                        e.get("prompt_sha256"),
                        e.get("input_sha256"),
                        e.get("tokens_in"),
                        e.get("tokens_out"),
                        e.get("latency_ms"),
                        e.get("attempt"),
                        e.get("detail_json"),
                        None,
                    ),
                )

            if target.backend.name == "postgres":
                con.execute(
                    "SELECT setval(pg_get_serial_sequence('events', 'event_id'), "
                    "COALESCE((SELECT MAX(event_id) FROM events), 1))"
                )

            now_ts = datetime.now(UTC).isoformat(timespec="milliseconds")
            detail_str = json.dumps(
                {
                    "file_sha256": file_sha256,
                    "event_offset": offset,
                    "runs": [r["run_id"] for r in copied_runs],
                },
                sort_keys=True,
            )
            con.execute(
                "INSERT INTO events (ts, actor, action, detail_json, actor_id) "
                "VALUES (?,?,?,?,?)",
                (now_ts, "importer", "log_imported", detail_str, None),
            )

            con.commit()
        except Exception:
            con.rollback()
            raise

    return {
        "runs": len(copied_runs),
        "items": len(copied_items),
        "events": len(copied_events),
        "skipped_runs": skipped_runs,
        "event_offset": offset,
        "dropped_events": dropped_events,
    }
