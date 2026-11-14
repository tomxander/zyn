"""Personal access tokens and service accounts."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from harness.team.permissions import Access, access_for_groups
from harness.team.principal import Principal

if TYPE_CHECKING:
    from harness.audit.store import AuditStore
    from harness.team.settings import TeamSettings


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _parse_ts(ts_str: str) -> datetime:
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=UTC)


def create_token(
    audit: AuditStore,
    owner: Principal,
    label: str,
    days: int = 90,
    max_days: int | None = None,
) -> tuple[str, str]:
    """Creates a personal access token. Returns (token_id, secret) where secret is shown once."""
    if max_days is not None:
        days = min(max(1, days), max_days)
    else:
        days = min(max(1, days), 90)
    token_id = f"tok-{uuid.uuid4().hex[:8]}"
    secret = "zyn_" + secrets.token_urlsafe(32)
    secret_sha256 = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    created_at = _now()
    expires_at = (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="milliseconds")

    with audit.backend.connect() as con:
        con.execute(
            "INSERT INTO tokens (token_id, sha256, owner_id, owner_name, label, created_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (token_id, secret_sha256, owner.id, owner.name, label, created_at, expires_at),
        )
    return token_id, secret


def revoke_token(audit: AuditStore, token_id: str, by: Principal) -> None:
    """Revokes a personal access token by logging a token_revoked event."""
    audit.log_event(
        actor=by.name,
        action="token_revoked",
        object_id=token_id,
        actor_id=by.id,
        detail={"token_id": token_id, "revoked_by": by.id},
    )


def resolve_token(audit: AuditStore, team: TeamSettings, secret: str) -> Access | None:
    """Resolves a bearer secret into an Access object, checking validity and groups."""
    secret_sha256 = hashlib.sha256(secret.encode("utf-8")).hexdigest()

    # Check service accounts
    if team.service_accounts:
        for sa_name, sa in team.service_accounts.items():
            sa_hash = (
                sa.token_sha256 if hasattr(sa, "token_sha256") else sa.get("token_sha256")
            )
            sa_proj = sa.project if hasattr(sa, "project") else sa.get("project")
            sa_role = sa.role if hasattr(sa, "role") else sa.get("role")
            if sa_hash == secret_sha256:
                p = Principal(id=f"service:{sa_name}", name=sa_name, email=None, kind="service")
                return Access(principal=p, roles={sa_proj: sa_role}, admin=False)

    # Check personal tokens
    with audit.backend.connect() as con:
        rows = con.execute("SELECT * FROM tokens WHERE sha256=?", (secret_sha256,))
        if not rows:
            return None
        token = rows[0]

        # Expiration check
        if datetime.fromisoformat(token["expires_at"]) < datetime.now(UTC):
            return None

        # Revocation check for token (using indexed object_id query first)
        t_rev = con.execute(
            "SELECT 1 FROM events WHERE action = 'token_revoked' AND object_id = ? LIMIT 1",
            (token["token_id"],),
        )
        if t_rev:
            return None
        t_legacy = con.execute(
            "SELECT detail_json FROM events WHERE action = 'token_revoked' AND object_id IS NULL"
        )
        for r in t_legacy:
            if r["detail_json"]:
                dtl = json.loads(r["detail_json"])
                if dtl.get("token_id") == token["token_id"]:
                    return None

        # Revocation check for owner (person_revoked using indexed queries)
        p_rev = con.execute(
            "SELECT ts FROM events WHERE action = 'person_revoked' AND (object_id = ? OR actor_id = ?) ORDER BY event_id DESC",
            (token["owner_id"], token["owner_id"]),
        )
        revocations = [_parse_ts(r["ts"]) for r in p_rev]
        p_legacy = con.execute(
            "SELECT ts, detail_json FROM events WHERE action = 'person_revoked' AND object_id IS NULL AND actor_id IS NULL"
        )
        for r in p_legacy:
            dtl = json.loads(r["detail_json"]) if r["detail_json"] else {}
            if dtl.get("person_id") == token["owner_id"]:
                revocations.append(_parse_ts(r["ts"]))

        if revocations:
            latest_rev = max(revocations)
            token_created = _parse_ts(token["created_at"])
            if latest_rev >= token_created:
                return None
            s_rows = con.execute(
                "SELECT ts FROM events WHERE action = 'signed_in' AND actor_id = ? ORDER BY event_id DESC LIMIT 1",
                (token["owner_id"],),
            )
            if not s_rows or _parse_ts(s_rows[0]["ts"]) <= latest_rev:
                return None

        # Fetch owner's latest groups from signed_in events
        s_rows = con.execute(
            "SELECT detail_json FROM events WHERE action = 'signed_in' AND actor_id = ? ORDER BY event_id DESC LIMIT 1",
            (token["owner_id"],),
        )
        groups = []
        if s_rows and s_rows[0]["detail_json"]:
            dtl = json.loads(s_rows[0]["detail_json"])
            groups = dtl.get("groups", [])

    p = Principal(
        id=token["owner_id"],
        name=token["owner_name"],
        email=None,
        kind="token",
        token_id=token["token_id"],
    )
    return access_for_groups(p, groups, team)
