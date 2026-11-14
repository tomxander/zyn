"""Configuration and settings for team mode."""

from __future__ import annotations

import os
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def _resolve_env(val: Any) -> Any:
    if isinstance(val, str):
        if val.startswith("env:"):
            var_name = val[4:].strip()
            if not var_name or var_name not in os.environ or not os.environ[var_name]:
                raise ValueError(f"Team setting needs environment variable {var_name}")
            return os.environ[var_name]

        def _replace_var(match: re.Match) -> str:
            vname = match.group(1).strip()
            if not vname or vname not in os.environ or not os.environ[vname]:
                raise ValueError(f"Team setting needs environment variable {vname}")
            return os.environ[vname]

        if "${" in val:
            val = re.sub(r"\$\{([A-Za-z0-9_]+)\}", _replace_var, val)
        return val
    if isinstance(val, dict):
        return {k: _resolve_env(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_resolve_env(x) for x in val]
    return val


class ProjectSettings(BaseModel):
    name: str
    rule_profile: str = "default"
    four_eyes: bool = True
    roles: dict[Literal["viewer", "engineer", "approver"], list[str]]


class OidcSettings(BaseModel):
    issuer: str
    client_id: str
    client_secret: str
    internal_url: str | None = None
    groups_claim: str = "groups"
    scopes: list[str] = ["openid", "profile", "email"]


class ServiceAccount(BaseModel):
    project: str
    role: Literal["viewer", "engineer"]
    token_sha256: str


class TeamSettings(BaseModel):
    database_url: str
    public_url: str
    session_secret: str
    session_hours: int = 12
    oidc: OidcSettings
    admins: list[str]
    projects: dict[str, ProjectSettings]
    allowed_models: list[str]
    offline_allowed_hosts: list[str] = Field(default_factory=list)
    service_accounts: dict[str, ServiceAccount] = {}
    token_days: int = 90
    max_upload_mb: int = 50
    allow_insecure_http: bool = False
    trial: bool = False

    @model_validator(mode="before")
    @classmethod
    def resolve_env_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if os.environ.get("ZYN_DATABASE_URL"):
                data["database_url"] = os.environ["ZYN_DATABASE_URL"]
            if os.environ.get("ZYN_SESSION_SECRET"):
                data["session_secret"] = os.environ["ZYN_SESSION_SECRET"]
            oidc = data.get("oidc")
            if isinstance(oidc, dict):
                if os.environ.get("ZYN_OIDC_ISSUER"):
                    oidc["issuer"] = os.environ["ZYN_OIDC_ISSUER"]
                if os.environ.get("ZYN_OIDC_CLIENT_ID"):
                    oidc["client_id"] = os.environ["ZYN_OIDC_CLIENT_ID"]
                if os.environ.get("ZYN_OIDC_CLIENT_SECRET"):
                    oidc["client_secret"] = os.environ["ZYN_OIDC_CLIENT_SECRET"]
                if os.environ.get("ZYN_OIDC_INTERNAL_URL"):
                    oidc["internal_url"] = os.environ["ZYN_OIDC_INTERNAL_URL"]
        return _resolve_env(data)

    @model_validator(mode="after")
    def validate_secrets(self) -> TeamSettings:
        if not self.session_secret or not self.session_secret.strip():
            raise ValueError("Team mode requires session_secret to be set.")
        if not self.database_url or not self.database_url.strip():
            raise ValueError("Team mode requires database_url to be set.")
        if not self.trial:
            trial_markers = (
                "trial-only",
                "trial-only-session-secret",
                "trial-only-app-password",
                "trial-only-admin-password",
                "zyn-trial-client-secret",
            )
            for marker in trial_markers:
                if marker in self.session_secret:
                    raise ValueError("Production mode cannot use trial-only credentials in session_secret.")
                if marker in self.database_url:
                    raise ValueError("Production mode cannot use trial-only credentials in database_url.")
                if self.oidc and self.oidc.client_secret and marker in self.oidc.client_secret:
                    raise ValueError("Production mode cannot use trial-only credentials in oidc.client_secret.")
            for sa_name, sa in self.service_accounts.items():
                for marker in trial_markers:
                    if marker in sa.token_sha256:
                        raise ValueError(f"Production mode cannot use trial-only credentials in service account '{sa_name}'.")
        return self
