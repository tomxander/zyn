"""Append-only audit store on SQLite.

Nothing is ever updated or deleted. Database triggers enforce this.
- runs:   one row per workflow run
- items:  every generated or edited object; an edit is a new version, the old one stays
- events: every action (generated, validation_failed, ai_reviewed, edited, approved,
          rejected, exported) with model, prompt hash and token usage

An item's status is derived from events: the latest decision on its latest version.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
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

_TRIGGERS = [
    f"CREATE TRIGGER IF NOT EXISTS no_{op}_{tbl} BEFORE {op.upper()} ON {tbl} "
    f"BEGIN SELECT RAISE(ABORT, '{tbl} is append-only'); END;"
    for tbl in ("runs", "items", "events")
    for op in ("update", "delete")
]

DECISIONS = {"approved", "rejected"}
# Undoing a decision is a new event, never a deletion: "reopened" puts the item back to
# awaiting a decision, and the earlier decision stays in the record.
REOPEN = "reopened"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class AuditStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con, con:
            con.executescript(SCHEMA)
            con.execute("CREATE INDEX IF NOT EXISTS events_answer "
                        "ON events(input_sha256, prompt_sha256)")
            # Decision lookups by item; without it each one reads the whole event log.
            con.execute("CREATE INDEX IF NOT EXISTS events_object "
                        "ON events(object_id, event_id)")
            for trig in _TRIGGERS:
                con.execute(trig)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30)  # workflows write from worker threads
        con.row_factory = sqlite3.Row
        return con

    # ---- writes -------------------------------------------------------------

    def start_run(self, workflow: str, note: str | None = None) -> str:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        with closing(self._connect()) as con, con:
            con.execute(
                "INSERT INTO runs VALUES (?,?,?,?)", (run_id, _now(), workflow, note)
            )
        return run_id

    def log_event(self, actor: str, action: str, **fields: Any) -> int:
        detail = fields.pop("detail", None)
        cols = ["ts", "actor", "action", *fields.keys(), "detail_json"]
        vals = [_now(), actor, action, *fields.values(),
                json.dumps(detail, ensure_ascii=False) if detail is not None else None]
        with closing(self._connect()) as con, con:
            cur = con.execute(
                f"INSERT INTO events ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                vals,
            )
            return int(cur.lastrowid)

    def claim(self, run_id: str, key: str, actor: str, stale_after_s: int = 1800) -> bool:
        """Atomically claims a piece of work (e.g. one section's extraction) for one process.
        Returns False if another live claim holds it. A claim older than stale_after_s is
        treated as abandoned (crashed process) and can be taken over."""
        con = self._connect()
        try:
            con.isolation_level = None
            con.execute("BEGIN IMMEDIATE")  # write lock: check-and-insert cannot interleave
            row = con.execute(
                "SELECT action, ts FROM events WHERE run_id=? AND object_id=? "
                "AND action IN ('claimed','claim_released') ORDER BY event_id DESC LIMIT 1",
                (run_id, key)).fetchone()
            if row and row["action"] == "claimed":
                age = (datetime.now(UTC) - datetime.fromisoformat(row["ts"])).total_seconds()
                if age < stale_after_s:
                    con.execute("ROLLBACK")
                    return False
            con.execute(
                "INSERT INTO events (ts, run_id, actor, action, object_type, object_id) "
                "VALUES (?,?,?,?,?,?)", (_now(), run_id, actor, "claimed", "work", key))
            con.execute("COMMIT")
            return True
        finally:
            con.close()

    def release(self, run_id: str, key: str, actor: str) -> None:
        self.log_event(actor, "claim_released", run_id=run_id, object_type="work", object_id=key)

    def add_item(
        self, run_id: str, item_type: str, payload: dict[str, Any], created_by: str,
        item_id: str | None = None,
    ) -> str:
        item_id = item_id or f"{item_type}-{uuid.uuid4().hex[:8]}"
        with closing(self._connect()) as con, con:
            con.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?)",
                (item_id, 1, run_id, item_type, json.dumps(payload, ensure_ascii=False),
                 created_by, _now()),
            )
        return item_id

    def edit_item(self, item_id: str, new_payload: dict[str, Any], actor: str,
                  comment: str | None = None, source: str = "human") -> int:
        """Stores an edit as a new version and logs before/after.
        source: 'human' for a manual edit, 'ai_suggestion' when the reviewer's fix was applied."""
        current = self.get_item(item_id)
        if current is None:
            raise KeyError(item_id)
        new_version = current["version"] + 1
        with closing(self._connect()) as con, con:
            con.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?)",
                (item_id, new_version, current["run_id"], current["item_type"],
                 json.dumps(new_payload, ensure_ascii=False), actor, _now()),
            )
        self.log_event(
            actor, "edited", run_id=current["run_id"], object_type=current["item_type"],
            object_id=item_id, object_version=new_version,
            detail={"before": current["payload"], "after": new_payload, "comment": comment,
                    "source": source},
        )
        return new_version

    def latest_ai_review(self, item_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT * FROM events WHERE object_id=? AND action='ai_reviewed' "
                "ORDER BY event_id DESC LIMIT 1", (item_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
        return d

    def needs_override_reason(self, item_id: str) -> bool:
        """True when the AI reviewer objected and the current version is not the AI's own fix.
        Approving such an item requires a written reason."""
        review = self.latest_ai_review(item_id)
        if not review or not review["detail"] or review["detail"].get("verdict") == "accept":
            return False
        current = self.get_item(item_id)
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT detail_json FROM events WHERE object_id=? AND object_version=? "
                "AND action='edited' ORDER BY event_id DESC LIMIT 1",
                (item_id, current["version"])).fetchone()
        if not row:
            return True
        d = json.loads(row["detail_json"])
        before, after = d.get("before") or {}, d.get("after") or {}
        changed = any(before.get(k) != after.get(k) for k in ("text", "req_type", "quality_flags"))
        # Only an AI fix that changed text, type or flags counts as addressing the objection.
        return not (d.get("source") == "ai_suggestion" and changed)

    def decide(self, item_id: str, decision: str, actor: str, comment: str | None = None) -> None:
        """Records a human decision on the item's latest version."""
        if decision not in DECISIONS | {REOPEN}:
            raise ValueError(f"decision must be one of {sorted(DECISIONS | {REOPEN})}")
        if not actor or actor.strip().lower() in {"model", "ai"} or actor.startswith("ai-"):
            raise ValueError("Approvals and rejections must name a human reviewer")
        current = self.get_item(item_id)
        if current is None:
            raise KeyError(item_id)
        status = self.status(item_id)
        if status == decision or (decision == REOPEN and status not in DECISIONS):
            return  # repeat click on the same version: nothing new to record
        override = decision == "approved" and self.needs_override_reason(item_id)
        if override and not (comment and comment.strip()):
            raise ValueError("The AI reviewer objected to this item. Approving it needs a reason.")
        self.log_event(
            actor, decision, run_id=current["run_id"], object_type=current["item_type"],
            object_id=item_id, object_version=current["version"],
            detail={"comment": comment, "ai_override": override},
        )

    # ---- reads --------------------------------------------------------------

    def get_item(self, item_id: str, version: int | None = None) -> dict[str, Any] | None:
        q = "SELECT * FROM items WHERE item_id=? "
        args: list[Any] = [item_id]
        if version is None:
            q += "ORDER BY version DESC LIMIT 1"
        else:
            q += "AND version=?"
            args.append(version)
        with closing(self._connect()) as con:
            row = con.execute(q, args).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["payload"] = json.loads(d.pop("payload_json"))
        return d

    def status(self, item_id: str) -> str:
        """proposed | approved | rejected | edited (edited and awaiting a decision)."""
        item = self.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT action FROM events WHERE object_id=? AND object_version=? "
                "AND action IN ('approved','rejected','reopened') ORDER BY event_id DESC LIMIT 1",
                (item_id, item["version"]),
            ).fetchone()
        if row and row["action"] != REOPEN:
            return row["action"]
        return "edited" if item["version"] > 1 else "proposed"

    def list_runs(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as con:
            return [dict(r) for r in con.execute("SELECT * FROM runs ORDER BY started_at DESC")]

    def list_items(self, run_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
        q = ("SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
             "GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v WHERE i.run_id=?")
        args: list[Any] = [run_id]
        if item_type:
            q += " AND i.item_type=?"
            args.append(item_type)
        q += " ORDER BY i.created_at, i.item_id"
        with closing(self._connect()) as con:
            rows = [dict(r) for r in con.execute(q, args)]
        for r in rows:
            r["payload"] = json.loads(r.pop("payload_json"))
            r["status"] = self.status(r["item_id"])
        return rows

    def items_of_type(self, item_type: str) -> list[dict[str, Any]]:
        """Latest version of every item of one type, across all runs (no status lookup)."""
        q = ("SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
             "GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v "
             "WHERE i.item_type=? ORDER BY i.created_at")
        with closing(self._connect()) as con:
            rows = [dict(r) for r in con.execute(q, (item_type,))]
        for r in rows:
            r["payload"] = json.loads(r.pop("payload_json"))
        return rows

    def latest_decision(self, item_id: str) -> dict[str, Any] | None:
        """The most recent approve/reject event on an item, any version. None once reopened."""
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT * FROM events WHERE object_id=? AND action IN "
                "('approved','rejected','reopened') ORDER BY event_id DESC LIMIT 1",
                (item_id,)).fetchone()
        if row is None or row["action"] == REOPEN:
            return None
        d = dict(row)
        d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
        return d

    def latest_decisions(self) -> dict[str, dict[str, Any]]:
        """latest_decision for every decided item, in one query. Items whose latest
        decision event is a reopen are left out, as latest_decision returns None for them."""
        q = ("SELECT e.* FROM events e JOIN (SELECT object_id, MAX(event_id) m FROM events "
             "WHERE action IN ('approved','rejected','reopened') GROUP BY object_id) l "
             "ON e.event_id=l.m")
        with closing(self._connect()) as con:
            rows = [dict(r) for r in con.execute(q)]
        out = {}
        for d in rows:
            if d["action"] == REOPEN:
                continue
            d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
            out[d["object_id"]] = d
        return out

    def approved_items(self, run_id: str, item_type: str) -> list[dict[str, Any]]:
        """The only thing a downstream workflow step may consume."""
        return [i for i in self.list_items(run_id, item_type) if i["status"] == "approved"]

    def find_answer(self, *, prompt_sha256: str, input_sha256: str, model_profile: str,
                    model_requested: str, task: str, prompt_version: str) -> dict | None:
        """The latest schema-valid answer the same model gave to the same prompt and input,
        in any run. Only first-hand answers count, never a replay of one."""
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT * FROM events WHERE action='generated' AND input_sha256=? "
                "AND prompt_sha256=? AND model_profile=? AND model_requested=? "
                "AND object_type=? AND prompt_version=? ORDER BY event_id DESC LIMIT 1",
                (input_sha256, prompt_sha256, model_profile, model_requested, task,
                 prompt_version)).fetchone()
        if row is None:
            return None
        r = dict(row)
        r["detail"] = json.loads(r.pop("detail_json")) if r.get("detail_json") else None
        return r

    def events(self, run_id: str | None = None, object_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM events WHERE 1=1", []
        if run_id:
            q += " AND run_id=?"
            args.append(run_id)
        if object_id:
            q += " AND object_id=?"
            args.append(object_id)
        q += " ORDER BY event_id"
        with closing(self._connect()) as con:
            rows = [dict(r) for r in con.execute(q, args)]
        for r in rows:
            r["detail"] = json.loads(r.pop("detail_json")) if r.get("detail_json") else None
        return rows
