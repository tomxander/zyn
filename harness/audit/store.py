"""Append-only audit store with pluggable backends (SQLite, PostgreSQL).

Nothing is ever updated or deleted. Database triggers enforce this.
- runs:   one row per workflow run
- items:  every generated or edited object; an edit is a new version, the old one stays
- events: every action (generated, validation_failed, ai_reviewed, edited, approved,
          rejected, exported) with model, prompt hash and token usage

An item's status is derived from events: the latest decision on its latest version.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.audit.backend import Backend, Conn, SqliteBackend

if TYPE_CHECKING:
    from harness.team.principal import Principal

DECISIONS = {"approved", "rejected"}
REOPEN = "reopened"

# Explicit sentinel for the all-projects view (personal mode and admin views).
ALL_PROJECTS = object()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _ensure_sqlite_columns(con: Conn) -> None:
    """Adds new nullable identity columns to existing SQLite files if missing."""
    cols_runs = {r["name"] for r in con.execute("PRAGMA table_info(runs)")}
    if cols_runs and "project" not in cols_runs:
        con.execute("ALTER TABLE runs ADD COLUMN project TEXT")
    if cols_runs and "started_by_id" not in cols_runs:
        con.execute("ALTER TABLE runs ADD COLUMN started_by_id TEXT")

    cols_items = {r["name"] for r in con.execute("PRAGMA table_info(items)")}
    if cols_items and "created_by_id" not in cols_items:
        con.execute("ALTER TABLE items ADD COLUMN created_by_id TEXT")

    cols_events = {r["name"] for r in con.execute("PRAGMA table_info(events)")}
    if cols_events and "actor_id" not in cols_events:
        con.execute("ALTER TABLE events ADD COLUMN actor_id TEXT")

    cols_sv = {r["name"] for r in con.execute("PRAGMA table_info(schema_versions)")}
    if cols_sv:
        con.execute(
            "INSERT OR IGNORE INTO schema_versions (version, applied_at, label) VALUES (2, '2026-11-14T00:00:00.000Z', 'items_seq')"
        )


def _parse_sqlite_url(url: str) -> Path:
    if not url.startswith("sqlite:///"):
        raise ValueError(
            f"Invalid sqlite database URL '{url}'. Expected sqlite:///relative, "
            "sqlite:////absolute, or sqlite:///C:/..."
        )
    raw = url[len("sqlite:///"):]
    if not raw:
        raise ValueError(
            f"Invalid sqlite database URL '{url}': path component is empty. "
            "Expected sqlite:///relative, sqlite:////absolute, or sqlite:///C:/..."
        )
    import re

    if re.match(r"^[a-zA-Z]:[/\\].*", raw):
        return Path(raw)
    if url.startswith("sqlite:////"):
        return Path("/" + raw.lstrip("/"))
    return Path(raw)


class AuditStore:
    def __init__(self, target: Path | str | Backend):
        if isinstance(target, Backend):
            self.backend = target
        elif isinstance(target, str) and target.startswith(
            ("postgresql://", "postgres://")
        ):
            from harness.audit.pg import PostgresBackend

            self.backend = PostgresBackend(target)
        elif isinstance(target, str) and target.startswith("sqlite://"):
            self.backend = SqliteBackend(_parse_sqlite_url(target))
        elif isinstance(target, str) and "://" in target:
            raise ValueError(
                f"Unsupported database URL scheme in '{target}'. "
                "Supported: postgresql://, postgres://, sqlite://"
            )
        else:
            self.backend = SqliteBackend(Path(target))

        self.path: Path | None = getattr(self.backend, "path", None)
        self._project: Any = ALL_PROJECTS
        self._principal: Principal | None = None

        with self.backend.connect() as con:
            if self.backend.name == "sqlite":
                _ensure_sqlite_columns(con)
            for stmt in self.backend.schema():
                con.execute(stmt)

    def scoped(self, project: Any, principal: Principal | None = None) -> AuditStore:
        """Returns a store view scoped to a project and principal sharing the backend."""
        clone = object.__new__(AuditStore)
        clone.backend = self.backend
        clone.path = self.path
        clone._project = project
        clone._principal = principal
        return clone

    # ---- helpers for roles and four-eyes ------------------------------------

    def run_project(self, run_id: str) -> str | None:
        with self.backend.connect() as con:
            rows = con.execute("SELECT project FROM runs WHERE run_id=?", (run_id,))
        return rows[0]["project"] if rows else None

    def touched_by(self, item_id: str, actor_id: str) -> bool:
        """True if any version of item_id was created or edited by actor_id."""
        with self.backend.connect() as con:
            rows = con.execute(
                "SELECT 1 FROM items WHERE item_id=? AND created_by_id=? LIMIT 1",
                (item_id, actor_id),
            )
        return bool(rows)

    def started_by(self, run_id: str) -> str | None:
        """The principal ID that started run_id, or None."""
        with self.backend.connect() as con:
            rows = con.execute("SELECT started_by_id FROM runs WHERE run_id=?", (run_id,))
        return rows[0]["started_by_id"] if rows else None

    # ---- writes -------------------------------------------------------------

    def start_run(
        self,
        workflow: str,
        note: str | None = None,
        run_id: str | None = None,
        project: str | None = None,
        started_by_id: str | None = None,
    ) -> str:
        run_id = run_id or (datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6])
        if project is None:
            project = None if self._project is ALL_PROJECTS else self._project
        if started_by_id is None:
            started_by_id = self._principal.id if self._principal else None
        with self.backend.connect() as con:
            con.execute(
                "INSERT INTO runs (run_id, started_at, workflow, note, project, started_by_id) "
                "VALUES (?,?,?,?,?,?)",
                (run_id, _now(), workflow, note, project, started_by_id),
            )
        return run_id

    def log_event(self, actor: str, action: str, **fields: Any) -> int:
        detail = fields.pop("detail", None)
        if isinstance(detail, dict):
            detail = dict(detail)
        elif detail is None and self._principal and self._principal.token_id:
            detail = {}
        if "actor_id" not in fields:
            is_human = bool(self._principal and self._principal.id and actor == self._principal.name)
            fields["actor_id"] = self._principal.id if is_human else None
        if self._principal and self._principal.token_id and isinstance(detail, dict) and "token_id" not in detail:
            detail["token_id"] = self._principal.token_id
        cols = ["ts", "actor", "action", *fields.keys(), "detail_json"]
        vals = [
            _now(),
            actor,
            action,
            *fields.values(),
            json.dumps(detail, ensure_ascii=False) if detail is not None else None,
        ]
        with self.backend.connect() as con:
            return con.insert(
                f"INSERT INTO events ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                vals,
            )

    def claim(self, run_id: str, key: str, actor: str, stale_after_s: int = 1800) -> bool:
        """Atomically claims a piece of work (e.g. one section's extraction) for one process.
        Returns False if another live claim holds it. A claim older than stale_after_s is
        treated as abandoned (crashed process) and can be taken over."""
        with self.backend.connect() as con:
            con.claim_lock()
            rows = con.execute(
                "SELECT action, ts FROM events WHERE run_id=? AND object_id=? "
                "AND action IN ('claimed','claim_released') ORDER BY event_id DESC LIMIT 1",
                (run_id, key),
            )
            if rows and rows[0]["action"] == "claimed":
                age = (datetime.now(UTC) - datetime.fromisoformat(rows[0]["ts"])).total_seconds()
                if age < stale_after_s:
                    con.rollback()
                    return False
            is_human = bool(self._principal and self._principal.id and actor == self._principal.name)
            actor_id = self._principal.id if is_human else None
            con.execute(
                "INSERT INTO events (ts, run_id, actor, action, object_type, object_id, actor_id) "
                "VALUES (?,?,?,?,?,?,?)",
                (_now(), run_id, actor, "claimed", "work", key, actor_id),
            )
            con.commit()
            return True

    def release(self, run_id: str, key: str, actor: str) -> None:
        self.log_event(actor, "claim_released", run_id=run_id, object_type="work", object_id=key)

    def add_item(
        self,
        run_id: str,
        item_type: str,
        payload: dict[str, Any],
        created_by: str,
        item_id: str | None = None,
    ) -> str:
        item_id = item_id or f"{item_type}-{uuid.uuid4().hex[:8]}"
        is_human = bool(self._principal and self._principal.id and created_by == self._principal.name)
        created_by_id = self._principal.id if is_human else None
        with self.backend.connect() as con:
            con.execute(
                "INSERT INTO items (item_id, version, run_id, item_type, payload_json, "
                "created_by, created_at, created_by_id) VALUES (?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    1,
                    run_id,
                    item_type,
                    json.dumps(payload, ensure_ascii=False),
                    created_by,
                    _now(),
                    created_by_id,
                ),
            )
        return item_id

    def edit_item(
        self,
        item_id: str,
        new_payload: dict[str, Any],
        actor: str,
        comment: str | None = None,
        source: str = "human",
    ) -> int:
        """Stores an edit as a new version and logs before/after.
        source: 'human' for a manual edit, 'ai_suggestion' when the reviewer's fix was applied."""
        current = self.get_item(item_id)
        if current is None:
            raise KeyError(item_id)
        new_version = current["version"] + 1
        is_human = bool(self._principal and self._principal.id and actor == self._principal.name)
        created_by_id = self._principal.id if is_human else None
        with self.backend.connect() as con:
            con.execute(
                "INSERT INTO items (item_id, version, run_id, item_type, payload_json, "
                "created_by, created_at, created_by_id) VALUES (?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    new_version,
                    current["run_id"],
                    current["item_type"],
                    json.dumps(new_payload, ensure_ascii=False),
                    actor,
                    _now(),
                    created_by_id,
                ),
            )
        self.log_event(
            actor,
            "edited",
            run_id=current["run_id"],
            object_type=current["item_type"],
            object_id=item_id,
            object_version=new_version,
            detail={
                "before": current["payload"],
                "after": new_payload,
                "comment": comment,
                "source": source,
            },
        )
        return new_version

    def latest_ai_review(self, item_id: str) -> dict[str, Any] | None:
        if self._project is not ALL_PROJECTS and self.get_item(item_id) is None:
            return None
        with self.backend.connect() as con:
            rows = con.execute(
                "SELECT * FROM events WHERE object_id=? AND action='ai_reviewed' "
                "ORDER BY event_id DESC LIMIT 1",
                (item_id,),
            )
        if not rows:
            return None
        d = dict(rows[0])
        d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
        return d

    def needs_override_reason(self, item_id: str) -> bool:
        """True when the AI reviewer objected and the current version is not the AI's own fix.
        Approving such an item requires a written reason."""
        review = self.latest_ai_review(item_id)
        if not review or not review["detail"] or review["detail"].get("verdict") == "accept":
            return False
        current = self.get_item(item_id)
        if current is None:
            return False
        with self.backend.connect() as con:
            rows = con.execute(
                "SELECT detail_json FROM events WHERE object_id=? AND object_version=? "
                "AND action='edited' ORDER BY event_id DESC LIMIT 1",
                (item_id, current["version"]),
            )
        if not rows:
            return True
        d = json.loads(rows[0]["detail_json"])
        before, after = d.get("before") or {}, d.get("after") or {}
        changed = any(before.get(k) != after.get(k) for k in ("text", "req_type", "quality_flags"))
        return not (d.get("source") == "ai_suggestion" and changed)

    def decide(
        self,
        item_id: str,
        decision: str,
        actor: str,
        comment: str | None = None,
        extra: dict | None = None,
    ) -> None:
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
        detail = {"comment": comment, "ai_override": override}
        if extra:
            detail.update(extra)
        self.log_event(
            actor,
            decision,
            run_id=current["run_id"],
            object_type=current["item_type"],
            object_id=item_id,
            object_version=current["version"],
            detail=detail,
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
        with self.backend.connect() as con:
            rows = con.execute(q, args)
        if not rows:
            return None
        # Enforce project isolation on single-item lookup
        if self._project is not ALL_PROJECTS:
            run_proj = self.run_project(rows[0]["run_id"])
            if run_proj != self._project:
                return None
        d = dict(rows[0])
        d.pop("seq", None)
        d["payload"] = json.loads(d.pop("payload_json"))
        return d

    def status(self, item_id: str) -> str:
        """proposed | approved | rejected | edited (edited and awaiting a decision)."""
        item = self.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        with self.backend.connect() as con:
            rows = con.execute(
                "SELECT action FROM events WHERE object_id=? AND object_version=? "
                "AND action IN ('approved','rejected','reopened') ORDER BY event_id DESC LIMIT 1",
                (item_id, item["version"]),
            )
        if rows and rows[0]["action"] != REOPEN:
            return rows[0]["action"]
        return "edited" if item["version"] > 1 else "proposed"

    def list_runs(self) -> list[dict[str, Any]]:
        q = "SELECT * FROM runs"
        args: list[Any] = []
        if self._project is not ALL_PROJECTS:
            if self._project is None:
                q += " WHERE project IS NULL"
            else:
                q += " WHERE project=?"
                args.append(self._project)
        q += " ORDER BY started_at DESC"
        with self.backend.connect() as con:
            return con.execute(q, args)

    def _items_order_by(self, table_alias: str = "i") -> str:
        tiebreak = f"{table_alias}.seq" if self.backend.name == "postgres" else f"{table_alias}.rowid"
        return f"ORDER BY {table_alias}.created_at, {tiebreak}"

    def list_items(self, run_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
        if self._project is not ALL_PROJECTS and self.run_project(run_id) != self._project:
            return []
        q = (
            "SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
            "GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v WHERE i.run_id=?"
        )
        args: list[Any] = [run_id]
        if item_type:
            q += " AND i.item_type=?"
            args.append(item_type)
        q += f" {self._items_order_by('i')}"
        with self.backend.connect() as con:
            rows = con.execute(q, args)
        for r in rows:
            r.pop("seq", None)
            r["payload"] = json.loads(r.pop("payload_json"))
            r["status"] = self.status(r["item_id"])
        return rows

    def items_of_type(self, item_type: str) -> list[dict[str, Any]]:
        """Latest version of every item of one type, across all runs (no status lookup)."""
        order_clause = self._items_order_by("i")
        if self._project is not ALL_PROJECTS:
            if self._project is None:
                q = (
                    "SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
                    "GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v "
                    f"JOIN runs r ON i.run_id=r.run_id WHERE i.item_type=? AND r.project IS NULL "
                    f"{order_clause}"
                )
                args: tuple[Any, ...] = (item_type,)
            else:
                q = (
                    "SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
                    "GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v "
                    f"JOIN runs r ON i.run_id=r.run_id WHERE i.item_type=? AND r.project=? "
                    f"{order_clause}"
                )
                args = (item_type, self._project)
        else:
            q = (
                "SELECT i.* FROM items i JOIN (SELECT item_id, MAX(version) v FROM items "
                f"GROUP BY item_id) m ON i.item_id=m.item_id AND i.version=m.v "
                f"WHERE i.item_type=? {order_clause}"
            )
            args = (item_type,)
        with self.backend.connect() as con:
            rows = con.execute(q, args)
        for r in rows:
            r.pop("seq", None)
            r["payload"] = json.loads(r.pop("payload_json"))
        return rows

    def latest_decision(self, item_id: str) -> dict[str, Any] | None:
        """The most recent approve/reject event on an item, any version. None once reopened."""
        if self._project is not ALL_PROJECTS and self.get_item(item_id) is None:
            return None
        with self.backend.connect() as con:
            rows = con.execute(
                "SELECT * FROM events WHERE object_id=? AND action IN "
                "('approved','rejected','reopened') ORDER BY event_id DESC LIMIT 1",
                (item_id,),
            )
        if not rows or rows[0]["action"] == REOPEN:
            return None
        d = dict(rows[0])
        d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
        return d

    def latest_decisions(self) -> dict[str, dict[str, Any]]:
        """latest_decision for every decided item, in one query. Items whose latest
        decision event is a reopen are left out, as latest_decision returns None for them."""
        if self._project is not ALL_PROJECTS:
            if self._project is None:
                q = (
                    "SELECT e.* FROM events e JOIN (SELECT object_id, MAX(event_id) m FROM events "
                    "WHERE action IN ('approved','rejected','reopened') GROUP BY object_id) l "
                    "ON e.event_id=l.m JOIN runs r ON e.run_id=r.run_id WHERE r.project IS NULL"
                )
                args: tuple[Any, ...] = ()
            else:
                q = (
                    "SELECT e.* FROM events e JOIN (SELECT object_id, MAX(event_id) m FROM events "
                    "WHERE action IN ('approved','rejected','reopened') GROUP BY object_id) l "
                    "ON e.event_id=l.m JOIN runs r ON e.run_id=r.run_id WHERE r.project=?"
                )
                args = (self._project,)
        else:
            q = (
                "SELECT e.* FROM events e JOIN (SELECT object_id, MAX(event_id) m FROM events "
                "WHERE action IN ('approved','rejected','reopened') GROUP BY object_id) l "
                "ON e.event_id=l.m"
            )
            args = ()
        with self.backend.connect() as con:
            rows = con.execute(q, args)
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

    def find_answer(
        self,
        *,
        prompt_sha256: str,
        input_sha256: str,
        model_profile: str,
        model_requested: str,
        task: str,
        prompt_version: str,
    ) -> dict | None:
        """The latest schema-valid answer the same model gave to the same prompt and input,
        in any run. Only first-hand answers count, never a replay of one."""
        if self._project is not ALL_PROJECTS:
            if self._project is None:
                q = (
                    "SELECT events.* FROM events JOIN runs ON events.run_id=runs.run_id "
                    "WHERE events.action='generated' AND events.input_sha256=? "
                    "AND events.prompt_sha256=? AND events.model_profile=? AND events.model_requested=? "
                    "AND events.object_type=? AND events.prompt_version=? AND runs.project IS NULL "
                    "ORDER BY events.event_id DESC LIMIT 1"
                )
                args: tuple[Any, ...] = (
                    input_sha256,
                    prompt_sha256,
                    model_profile,
                    model_requested,
                    task,
                    prompt_version,
                )
            else:
                q = (
                    "SELECT events.* FROM events JOIN runs ON events.run_id=runs.run_id "
                    "WHERE events.action='generated' AND events.input_sha256=? "
                    "AND events.prompt_sha256=? AND events.model_profile=? AND events.model_requested=? "
                    "AND events.object_type=? AND events.prompt_version=? AND runs.project=? "
                    "ORDER BY events.event_id DESC LIMIT 1"
                )
                args = (
                    input_sha256,
                    prompt_sha256,
                    model_profile,
                    model_requested,
                    task,
                    prompt_version,
                    self._project,
                )
        else:
            q = (
                "SELECT * FROM events WHERE action='generated' AND input_sha256=? "
                "AND prompt_sha256=? AND model_profile=? AND model_requested=? "
                "AND object_type=? AND prompt_version=? ORDER BY event_id DESC LIMIT 1"
            )
            args = (
                input_sha256,
                prompt_sha256,
                model_profile,
                model_requested,
                task,
                prompt_version,
            )
        with self.backend.connect() as con:
            rows = con.execute(q, args)
        if not rows:
            return None
        r = dict(rows[0])
        r["detail"] = json.loads(r.pop("detail_json")) if r.get("detail_json") else None
        return r

    def events(self, run_id: str | None = None, object_id: str | None = None) -> list[dict]:
        args: list[Any] = []
        if self._project is not ALL_PROJECTS:
            if run_id is not None:
                if self.run_project(run_id) != self._project:
                    return []
                q = "SELECT * FROM events WHERE run_id=?"
                args.append(run_id)
                if object_id:
                    q += " AND object_id=?"
                    args.append(object_id)
                q += " ORDER BY event_id"
            else:
                if self._project is None:
                    q = "SELECT e.* FROM events e JOIN runs r ON e.run_id=r.run_id WHERE r.project IS NULL"
                else:
                    q = "SELECT e.* FROM events e JOIN runs r ON e.run_id=r.run_id WHERE r.project=?"
                    args.append(self._project)
                if object_id:
                    q += " AND e.object_id=?"
                    args.append(object_id)
                q += " ORDER BY e.event_id"
        else:
            q = "SELECT * FROM events WHERE 1=1"
            if run_id:
                q += " AND run_id=?"
                args.append(run_id)
            if object_id:
                q += " AND object_id=?"
                args.append(object_id)
            q += " ORDER BY event_id"
        with self.backend.connect() as con:
            rows = con.execute(q, args)
        for r in rows:
            r["detail"] = json.loads(r.pop("detail_json")) if r.get("detail_json") else None
        return rows
