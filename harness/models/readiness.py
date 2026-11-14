"""Unified readiness check for model profiles across runner, bench, and CLI."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from harness.models.security import is_offline_host

if TYPE_CHECKING:
    from harness.config import HarnessConfig

LOCAL_PROVIDERS = {"ollama", "fake"}


def profile_readiness(cfg: HarnessConfig, profile_or_name: Any) -> tuple[bool, str]:
    """Evaluates whether a model profile can be called under the current configuration and environment.

    Checks:
    - Data rule / allowed_models
    - Offline constraints (loopback/private IP/host validation, cloud model refusal)
    - Credentials and optional SDK availability
    """
    if hasattr(profile_or_name, "provider"):
        p = profile_or_name
    else:
        p = cfg.profile(str(profile_or_name))

    if not cfg.model_allowed(p.name):
        return False, "not allowed by team data rule"

    # Offline evaluation
    allowed_hosts: list[str] = list(getattr(cfg, "offline_allowed_hosts", []) or [])
    if cfg.team and getattr(cfg.team, "offline_allowed_hosts", None):
        allowed_hosts.extend(cfg.team.offline_allowed_hosts)

    if cfg.is_offline():
        if p.provider == "fake":
            return True, "ready"

        if p.provider == "ollama":
            if p.model.endswith("-cloud") or ":cloud" in p.model:
                return False, "offline mode: cloud model disallowed"
            host = p.setting("host", "http://localhost:11434")
            ok, reason = is_offline_host(host, allowed_hosts)
            if not ok:
                return False, f"offline mode: {reason}"

        elif p.provider == "openai":
            local_val = p.setting("local", False)
            if not (isinstance(local_val, bool) and local_val is True):
                return False, "offline mode: non-local provider disallowed"
            base_url = p.setting("base_url")
            if not base_url:
                return False, "offline mode: local openai provider requires explicit base_url"
            ok, reason = is_offline_host(base_url, allowed_hosts)
            if not ok:
                return False, f"offline mode: {reason}"

        else:
            # All other providers (anthropic, azure, bedrock, vertex) are cloud providers
            return False, "offline mode"

    # Credentials and configuration checks
    if p.provider == "anthropic":
        ok = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        return (True, "ready") if ok else (False, "no API key")

    if p.provider == "ollama":
        try:
            import ollama

            host = p.setting("host", "http://localhost:11434")
            names = [m.model for m in ollama.Client(host=host, timeout=3, trust_env=False).list().models]
        except Exception:  # noqa: BLE001
            return False, "Ollama not running or not installed"
        if any(n == p.model or n.split(":")[0] == p.model for n in names):
            return True, "ready"
        return False, f"not pulled (ollama pull {p.model})"

    if p.provider == "openai":
        base_url = p.setting("base_url", "https://api.openai.com/v1")
        key_env = p.setting("api_key_env", "OPENAI_API_KEY")
        key = p.setting("api_key") or os.environ.get(key_env, "")
        local_val = p.setting("local", False)
        is_local = isinstance(local_val, bool) and local_val is True
        if is_local:
            return True, "configured"
        if not key and not ("localhost" in base_url or "127.0.0.1" in base_url):
            return False, "no API key"
        return True, "ready"

    if p.provider == "azure":
        endpoint = p.setting("endpoint") or p.setting("azure_endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        if not endpoint:
            return False, "no endpoint"
        key_env = p.setting("api_key_env", "AZURE_OPENAI_API_KEY")
        key = p.setting("api_key") or os.environ.get(key_env, "")
        if not key:
            return False, "no API key"
        return True, "ready"

    if p.provider == "bedrock":
        region = p.setting("region") or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "")
        if not region:
            return False, "no region"
        try:
            import boto3  # noqa: F401
            return True, "ready"
        except ImportError:
            return False, "boto3 not installed"

    if p.provider == "vertex":
        project = p.setting("project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT", "")
        key_env = p.setting("api_key_env", "GEMINI_API_KEY")
        key = p.setting("api_key") or os.environ.get(key_env, "")
        token = os.environ.get("VERTEX_BEARER_TOKEN") or os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "")
        if not key and not token and not project:
            return False, "no credentials or GEMINI_API_KEY"
        return True, "ready"

    if p.provider == "fake":
        return True, "ready"

    return False, f"unknown provider '{p.provider}'"
