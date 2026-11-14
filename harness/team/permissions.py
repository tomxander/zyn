"""Permissions, roles and the four-eyes rule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from harness.team.principal import Principal

if TYPE_CHECKING:
    from harness.audit.store import AuditStore
    from harness.team.settings import TeamSettings

ACTIONS = ("view", "run", "edit", "decide", "admin")

ROLE_ACTIONS = {
    "viewer": {"view"},
    "engineer": {"view", "run", "edit"},
    "approver": {"view", "run", "edit", "decide"},
}

ROLE_HIERARCHY = {"viewer": 1, "engineer": 2, "approver": 3}


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.ok


@dataclass(frozen=True)
class Access:
    principal: Principal
    roles: dict[str, str]  # project -> role
    admin: bool


PERSONAL_PRINCIPAL = Principal(id="", name="", email=None, kind="typed")
PERSONAL_ACCESS = Access(principal=PERSONAL_PRINCIPAL, roles={}, admin=True)


def access_for_groups(principal: Principal, groups: list[str], team: TeamSettings) -> Access:
    """Computes a person's project roles and admin rights from their sign-in groups."""
    is_admin = any(g in team.admins for g in groups)
    roles: dict[str, str] = {}
    for proj_id, proj_settings in team.projects.items():
        highest_role = None
        highest_rank = 0
        for role_name, group_list in proj_settings.roles.items():
            if any(g in group_list for g in groups):
                rank = ROLE_HIERARCHY.get(role_name, 0)
                if rank > highest_rank:
                    highest_rank = rank
                    highest_role = role_name
        if highest_role:
            roles[proj_id] = highest_role
    return Access(principal=principal, roles=roles, admin=is_admin)


def can(access: Access, project: str, action: str) -> Verdict:
    """Checks if the access grants an action on a project."""
    if access is PERSONAL_ACCESS:
        return Verdict(ok=True)
    if action == "admin":
        if access.admin:
            return Verdict(ok=True)
        return Verdict(ok=False, reason="Admin actions require admin role.")
    if action == "view" and access.admin:
        return Verdict(ok=True)
    if project not in access.roles:
        return Verdict(ok=False, reason=f"You do not have access to project '{project}'.")
    role = access.roles[project]
    if action in ROLE_ACTIONS.get(role, set()):
        return Verdict(ok=True)
    if action == "decide":
        return Verdict(ok=False, reason=f"Your role on this project is {role}; deciding needs approver.")
    if action in ("run", "edit"):
        return Verdict(ok=False, reason=f"Your role on this project is {role}; this needs engineer.")
    return Verdict(ok=False, reason=f"Your role on this project is {role}; this action is not allowed.")


def can_decide(
    access: Access,
    item: dict[str, Any],
    audit: AuditStore,
    team: TeamSettings,
) -> Verdict:
    """Checks role rights and the four-eyes rule on deciding an item."""
    if access is PERSONAL_ACCESS:
        return Verdict(ok=True)
    if access.principal.kind == "service":
        return Verdict(
            ok=False,
            reason="Service accounts cannot decide findings; only a named person decides.",
        )
    project = audit.run_project(item["run_id"]) or item.get("project")
    if not project:
        return Verdict(ok=False, reason="Run has no assigned project.")
    v = can(access, project, "decide")
    if not v.ok:
        return v

    proj_settings = team.projects.get(project)
    if proj_settings and proj_settings.four_eyes:
        actor_id = access.principal.id
        if actor_id:
            item_id = item["item_id"]
            if audit.touched_by(item_id, actor_id):
                return Verdict(ok=False, reason="You edited this; someone else must decide on it.")
            if item.get("item_type") == "finding" and audit.started_by(item["run_id"]) == actor_id:
                return Verdict(
                    ok=False,
                    reason="You started this run; someone else must decide on its findings.",
                )
    return Verdict(ok=True)
