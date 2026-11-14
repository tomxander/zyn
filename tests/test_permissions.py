from __future__ import annotations

from pathlib import Path

import pytest

from harness.audit.store import AuditStore
from harness.team.permissions import (
    PERSONAL_ACCESS,
    Access,
    access_for_groups,
    can,
    can_decide,
)
from harness.team.principal import Principal
from harness.team.settings import (
    OidcSettings,
    ProjectSettings,
    ServiceAccount,
    TeamSettings,
)

P_ALICE = Principal(id="oidc:corp#alice", name="Alice", email="alice@corp.test", kind="person")
P_BOB = Principal(id="oidc:corp#bob", name="Bob", email="bob@corp.test", kind="person")
P_CHARLIE = Principal(id="oidc:corp#charlie", name="Charlie", email="charlie@corp.test", kind="person")


@pytest.fixture
def sample_team() -> TeamSettings:
    return TeamSettings(
        database_url="postgresql://localhost/zyn",
        public_url="https://zyn.corp.test",
        session_secret="secret",
        oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        admins=["g-admin"],
        projects={
            "brake": ProjectSettings(
                name="Brake",
                four_eyes=True,
                roles={"viewer": ["g-brake-view"], "engineer": ["g-brake-eng"], "approver": ["g-brake-appr"]},
            ),
            "body": ProjectSettings(
                name="Body",
                four_eyes=False,
                roles={"viewer": ["g-body-view"], "engineer": ["g-body-eng"], "approver": ["g-body-appr"]},
            ),
        },
        allowed_models=["fake-gen"],
        service_accounts={
            "sa-ci": ServiceAccount(project="brake", role="engineer", token_sha256="hash123")
        },
    )


def test_table_groups_project_action(sample_team: TeamSettings):
    # Alice is brake approver and body viewer
    access_alice = access_for_groups(P_ALICE, ["g-brake-appr", "g-body-view"], sample_team)
    assert can(access_alice, "brake", "view").ok
    assert can(access_alice, "brake", "run").ok
    assert can(access_alice, "brake", "edit").ok
    assert can(access_alice, "brake", "decide").ok
    assert not can(access_alice, "brake", "admin").ok

    assert can(access_alice, "body", "view").ok
    assert not can(access_alice, "body", "run").ok
    v_edit = can(access_alice, "body", "edit")
    assert not v_edit.ok
    assert v_edit.reason == "Your role on this project is viewer; this needs engineer."
    v_decide = can(access_alice, "body", "decide")
    assert not v_decide.ok
    assert v_decide.reason == "Your role on this project is viewer; deciding needs approver."


def test_service_account_limited_to_its_project_and_role(sample_team: TeamSettings):
    sa_principal = Principal(id="service:sa-ci", name="sa-ci", email=None, kind="service")
    access = Access(principal=sa_principal, roles={"brake": "engineer"}, admin=False)

    assert can(access, "brake", "run").ok
    assert can(access, "brake", "edit").ok
    assert not can(access, "brake", "decide").ok
    assert not can(access, "body", "view").ok


def test_admin_sees_every_project(sample_team: TeamSettings):
    access_admin = access_for_groups(P_ALICE, ["g-admin"], sample_team)
    assert access_admin.admin is True
    # Admin gets view and admin across all projects
    assert can(access_admin, "brake", "view").ok
    assert can(access_admin, "brake", "admin").ok
    assert can(access_admin, "body", "view").ok
    assert can(access_admin, "body", "admin").ok
    assert can(access_admin, "any-other-project", "view").ok
    assert can(access_admin, "any-other-project", "admin").ok
    # But admin without project role CANNOT run, edit, or decide
    assert not can(access_admin, "brake", "run").ok
    assert not can(access_admin, "brake", "edit").ok
    assert not can(access_admin, "brake", "decide").ok


def test_service_account_cannot_decide(tmp_path: Path, sample_team: TeamSettings):
    sa_principal = Principal(id="service:sa-ci", name="sa-ci", email=None, kind="service")
    access = Access(principal=sa_principal, roles={"brake": "engineer"}, admin=False)

    store = AuditStore(tmp_path / "audit.sqlite")
    scoped = store.scoped("brake", P_ALICE)
    run_id = scoped.start_run("sift")
    item_id = scoped.add_item(run_id, "requirement", {"text": "req"}, "model:fake-gen")
    item = scoped.get_item(item_id)
    assert item is not None

    v = can_decide(access, item, scoped, sample_team)
    assert not v.ok
    assert v.reason == "Service accounts cannot decide findings; only a named person decides."


def test_no_group_no_projects(sample_team: TeamSettings):
    access = access_for_groups(P_ALICE, ["g-unknown"], sample_team)
    assert access.roles == {}
    assert not can(access, "brake", "view").ok


def test_personal_mode_allows_everything():
    assert can(PERSONAL_ACCESS, "any-proj", "decide").ok
    assert can(PERSONAL_ACCESS, "any-proj", "admin").ok


def test_four_eyes_editor_refused(tmp_path: Path, sample_team: TeamSettings):
    store = AuditStore(tmp_path / "audit.sqlite")
    scoped_a = store.scoped("brake", P_ALICE)
    run_id = scoped_a.start_run("sift")

    # Item created by model, but Alice edits it
    item_id = scoped_a.add_item(run_id, "requirement", {"text": "req1"}, "model:fake-gen")
    scoped_a.edit_item(item_id, {"text": "req1 edited"}, "Alice")

    item = scoped_a.get_item(item_id)
    assert item is not None

    access_alice = access_for_groups(P_ALICE, ["g-brake-appr"], sample_team)
    v_alice = can_decide(access_alice, item, scoped_a, sample_team)
    assert not v_alice.ok
    assert v_alice.reason == "You edited this; someone else must decide on it."

    # Bob (approver who didn't touch it) can decide
    access_bob = access_for_groups(P_BOB, ["g-brake-appr"], sample_team)
    v_bob = can_decide(access_bob, item, scoped_a, sample_team)
    assert v_bob.ok


def test_four_eyes_run_starter_refused_on_findings_only(tmp_path: Path, sample_team: TeamSettings):
    store = AuditStore(tmp_path / "audit.sqlite")
    scoped_a = store.scoped("brake", P_ALICE)
    run_id = scoped_a.start_run("sift")

    # Finding created by model
    finding_id = scoped_a.add_item(run_id, "finding", {"title": "f1"}, "model:fake-gen")
    finding_item = scoped_a.get_item(finding_id)
    assert finding_item is not None

    # Requirement created by model in the same run
    req_id = scoped_a.add_item(run_id, "requirement", {"text": "r1"}, "model:fake-gen")
    req_item = scoped_a.get_item(req_id)
    assert req_item is not None

    access_alice = access_for_groups(P_ALICE, ["g-brake-appr"], sample_team)

    # Alice started the run: refused on findings!
    v_find = can_decide(access_alice, finding_item, scoped_a, sample_team)
    assert not v_find.ok
    assert v_find.reason == "You started this run; someone else must decide on its findings."

    # But Alice CAN decide on requirements in that run (since she didn't edit them)
    v_req = can_decide(access_alice, req_item, scoped_a, sample_team)
    assert v_req.ok


def test_four_eyes_off_allows_self(tmp_path: Path, sample_team: TeamSettings):
    store = AuditStore(tmp_path / "audit.sqlite")
    # Body project has four_eyes = False
    scoped_b = store.scoped("body", P_ALICE)
    run_id = scoped_b.start_run("sift")
    finding_id = scoped_b.add_item(run_id, "finding", {"title": "f1"}, "model:fake-gen")
    scoped_b.edit_item(finding_id, {"title": "f1 edit"}, "Alice")
    item = scoped_b.get_item(finding_id)
    assert item is not None

    access_alice = access_for_groups(P_ALICE, ["g-body-appr"], sample_team)
    v = can_decide(access_alice, item, scoped_b, sample_team)
    assert v.ok


def test_can_decide_null_project_fails_closed(tmp_path: Path, sample_team: TeamSettings):
    store = AuditStore(tmp_path / "audit.sqlite")
    # Run with no project (NULL project)
    run_id = store.start_run("sift", project=None)
    item_id = store.add_item(run_id, "requirement", {"text": "r1"}, "model:fake-gen")
    item = store.get_item(item_id)
    assert item is not None

    access_alice = access_for_groups(P_ALICE, ["g-brake-appr"], sample_team)
    v = can_decide(access_alice, item, store, sample_team)
    assert not v.ok
    assert v.reason == "Run has no assigned project."

