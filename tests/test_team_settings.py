from __future__ import annotations

import pytest
from pydantic import BaseModel

from harness.audit.store import AuditStore
from harness.config import HarnessConfig
from harness.models.fake_provider import FakeProvider
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.team.settings import (
    TeamSettings,
)


class DummyOutput(BaseModel):
    message: str


def test_env_indirection_and_missing_env(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "super-secret-key")

    data = {
        "database_url": "postgresql://localhost/zyn",
        "public_url": "https://zyn.corp.test",
        "session_secret": "env:TEST_SECRET",
        "oidc": {
            "issuer": "https://idp.corp.test",
            "client_id": "zyn-app",
            "client_secret": "env:MISSING_SECRET",
        },
        "admins": ["admin@corp.test"],
        "projects": {
            "brake": {
                "name": "Brake System",
                "roles": {"viewer": ["g-view"], "engineer": ["g-eng"], "approver": ["g-appr"]},
            }
        },
        "allowed_models": ["fake-gen"],
    }

    # Missing env variable raises ValueError
    with pytest.raises(ValueError, match="Team setting needs environment variable MISSING_SECRET"):
        TeamSettings.model_validate(data)

    # When set, env: is resolved
    monkeypatch.setenv("MISSING_SECRET", "resolved-secret")
    settings = TeamSettings.model_validate(data)
    assert settings.session_secret == "super-secret-key"
    assert settings.oidc.client_secret == "resolved-secret"


def test_model_not_allowed_is_refused_before_sending(cfg_team: HarnessConfig, audit: AuditStore):
    run_id = audit.start_run("test_workflow")
    FakeProvider.queue.append('{"message": "should not be called"}')

    # Profile 'fake-rev' is not in allowed_models (which only allows 'fake-gen')
    with pytest.raises(StructuredOutputFailure, match="allowed_models"):
        structured_call(
            cfg=cfg_team,
            audit=audit,
            run_id=run_id,
            role_or_profile="fake-rev",
            task="testing",
            prompt_version="v1",
            system="system prompt",
            user="user prompt",
            output_model=DummyOutput,
        )

    # Before FakeProvider.calls grows
    assert len(FakeProvider.calls) == 0

    # Event action 'model_refused' is logged
    events = audit.events(run_id=run_id)
    refused = [e for e in events if e["action"] == "model_refused"]
    assert len(refused) == 1
    assert refused[0]["detail"]["profile"] == "fake-rev"


def test_empty_allowed_models_means_offline(cfg_team: HarnessConfig):
    assert cfg_team.team is not None
    cfg_empty = cfg_team.model_copy(
        update={"team": cfg_team.team.model_copy(update={"allowed_models": []})}
    )
    assert cfg_empty.model_allowed("fake-gen") is False
    assert cfg_empty.model_allowed("fake-rev") is False


def test_personal_mode_unchanged(cfg: HarnessConfig):
    assert cfg.team is None
    assert cfg.is_team() is False
    assert cfg.model_allowed("fake-gen") is True
    assert cfg.model_allowed("fake-rev") is True


def test_service_account_rejects_approver():
    from pydantic import ValidationError

    from harness.team.settings import ServiceAccount

    with pytest.raises(ValidationError):
        ServiceAccount(project="brake", role="approver", token_sha256="abc")  # type: ignore[arg-type]

    sa_eng = ServiceAccount(project="brake", role="engineer", token_sha256="abc")
    assert sa_eng.role == "engineer"
    sa_view = ServiceAccount(project="brake", role="viewer", token_sha256="abc")
    assert sa_view.role == "viewer"


def test_session_hours_default_is_12():
    from harness.team.settings import OidcSettings

    data = {
        "database_url": "postgresql://zyn:secret@localhost/zyn",
        "public_url": "https://zyn.corp.test",
        "session_secret": "session-secret-at-least-32-chars-long",
        "oidc": OidcSettings(issuer="https://idp", client_id="cid", client_secret="csec"),
        "admins": ["admin@corp.test"],
        "projects": {},
        "allowed_models": ["fake-gen"],
    }
    settings = TeamSettings.model_validate(data)
    assert settings.session_hours == 12


def test_trial_credentials_rejected_in_production():
    from pydantic import ValidationError

    from harness.team.settings import OidcSettings, ServiceAccount

    base_data = {
        "database_url": "postgresql://zyn:realpass@localhost/zyn",
        "public_url": "https://zyn.corp.test",
        "session_secret": "real-session-secret-32-chars-long",
        "oidc": OidcSettings(issuer="https://idp", client_id="cid", client_secret="realcsec"),
        "admins": ["admin@corp.test"],
        "projects": {},
        "allowed_models": ["fake-gen"],
        "trial": False,
    }

    # 1. Trial in database_url
    d1 = dict(base_data, database_url="postgresql://zyn:trial-only-app-password@localhost/zyn")
    with pytest.raises(ValidationError, match="Production mode cannot use trial-only credentials"):
        TeamSettings.model_validate(d1)

    # 2. Trial in session_secret
    d2 = dict(base_data, session_secret="trial-only-session-secret-at-least-32-chars-long")
    with pytest.raises(ValidationError, match="Production mode cannot use trial-only credentials"):
        TeamSettings.model_validate(d2)

    # 3. Trial in oidc.client_secret
    d3 = dict(base_data, oidc=OidcSettings(issuer="https://idp", client_id="cid", client_secret="zyn-trial-client-secret"))
    with pytest.raises(ValidationError, match="Production mode cannot use trial-only credentials"):
        TeamSettings.model_validate(d3)

    # 4. Trial in service account
    d4 = dict(base_data, service_accounts={"ci": ServiceAccount(project="p", role="engineer", token_sha256="trial-only-token")})
    with pytest.raises(ValidationError, match="Production mode cannot use trial-only credentials"):
        TeamSettings.model_validate(d4)

    # 5. Allowed when trial: True
    d_trial = dict(base_data, database_url="postgresql://zyn:trial-only-app-password@localhost/zyn", trial=True)
    assert TeamSettings.model_validate(d_trial).trial is True
