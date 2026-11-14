"""OpenAI and OpenAI-compatible endpoints (vLLM, LiteLLM, self-hosted gateways).

Supports structured outputs using strict JSON Schema (or json_object fallback).
Requires httpx (already a core dependency).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult
from harness.models.security import (
    build_offline_transport,
    sanitize_url,
    scrub_error_text,
    validate_api_key_env,
)


class OpenAIProvider:
    def __init__(self, profile: Profile, *, transport: httpx.BaseTransport | None = None):
        self.profile = profile
        self._transport = transport
        p = self.profile

        raw_base = p.setting("base_url", "https://api.openai.com/v1")
        self.base_url = raw_base.rstrip("/")
        self.clean_url = sanitize_url(self.base_url)

        local_val = p.setting("local", False)
        self.is_local = isinstance(local_val, bool) and local_val is True
        if self._transport is None and self.is_local:
            verify_opt = p.setting("ca_bundle") or p.setting("verify", True)
            pinned_t, err = build_offline_transport(
                self.base_url,
                verify=verify_opt,
                retries=int(p.setting("retries", 0)),
                http2=bool(p.setting("http2", False)),
            )
            if pinned_t is None:
                raise ProviderError(f"Offline validation failed for {self.clean_url}: {err}")
            self._transport = pinned_t

        key_env_var = validate_api_key_env(p.setting("api_key_env", "OPENAI_API_KEY"))
        self.api_key = p.setting("api_key") or os.environ.get(key_env_var, "")
        self.timeout = float(p.setting("timeout", 60.0))

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        url = f"{self.base_url}/chat/completions"

        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        chat_messages = [{"role": "system", "content": system}, *messages]

        # Use strict JSON schema if supported, else json_object
        structured_mode = p.setting("structured_mode", "json_schema")
        if structured_mode == "json_schema":
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": schema,
                },
            }
        else:
            response_format = {"type": "json_object"}

        is_reasoning = p.model.startswith(("o1", "o3", "gpt-5")) or bool(p.setting("reasoning", False))

        payload: dict[str, Any] = {
            "model": p.model,
            "messages": chat_messages,
            "response_format": response_format,
        }

        # Temperature: omit for reasoning models or when requested
        temp = p.setting("temperature")
        if not is_reasoning and temp is not None and not p.setting("omit_temperature", False):
            payload["temperature"] = float(temp)

        # Max tokens vs max_completion_tokens
        max_tokens_val = p.setting("max_tokens") or p.setting("max_completion_tokens")
        if max_tokens_val:
            if is_reasoning or p.setting("max_completion_tokens"):
                payload["max_completion_tokens"] = int(max_tokens_val)
            else:
                payload["max_tokens"] = int(max_tokens_val)

        try:
            with httpx.Client(
                timeout=self.timeout,
                transport=self._transport,
                trust_env=not self.is_local,
            ) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Could not connect to model endpoint at {self.clean_url}. "
                "Check server status, network, and proxy settings."
            ) from e
        except httpx.TimeoutException as e:
            raise ProviderError(
                f"Request to {self.clean_url} timed out after {self.timeout}s."
            ) from e
        except Exception as e:
            raise ProviderError(f"HTTP request to {self.clean_url} failed: {e}") from e

        if resp.status_code in (401, 403):
            raise ProviderError(
                f"Authentication failed for {self.clean_url} (HTTP {resp.status_code}). "
                "Check your API key configuration."
            )
        if resp.status_code == 404:
            raise ProviderError(
                f"Model '{p.model}' or endpoint not found at {self.clean_url} (HTTP 404)."
            )
        if resp.status_code == 429:
            raise ProviderError(
                f"Rate limit exceeded at {self.clean_url} (HTTP 429)."
            )
        if resp.is_error:
            error_body = scrub_error_text(resp.text)
            raise ProviderError(
                f"Model provider error from {self.clean_url} ({resp.status_code}): {error_body}"
            )

        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(f"Invalid JSON received from {self.clean_url}: {e}") from e

        if not isinstance(data, dict):
            raise ProviderError(f"Expected JSON object response from {self.clean_url}, got {type(data).__name__}")

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise ProviderError(f"No completion choices returned by {self.clean_url}.")

        choice = choices[0]
        if not isinstance(choice, dict):
            raise ProviderError(f"Malformed choice in response from {self.clean_url}.")

        finish_reason = choice.get("finish_reason")
        msg = choice.get("message")
        if not isinstance(msg, dict):
            raise ProviderError(f"Missing message structure in response from {self.clean_url}.")

        # Check for model refusal
        refusal = msg.get("refusal")
        if refusal:
            raise ProviderError(f"Model refused request: {refusal}")

        if finish_reason == "length":
            raise ProviderError("Output hit max_tokens before completing schema.")
        if finish_reason == "content_filter":
            raise ProviderError("Response content was filtered by safety policy.")

        text = msg.get("content") or ""
        usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}

        return ProviderResult(
            text=text,
            model_served=data.get("model", p.model),
            stop_reason=finish_reason,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            request_id=data.get("id"),
        )
