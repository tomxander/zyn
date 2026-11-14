"""Azure OpenAI Service provider, with schema-constrained output.

Uses Azure deployment endpoints and API keys.
Requires httpx (already a core dependency).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult
from harness.models.security import sanitize_url, scrub_error_text, validate_api_key_env


class AzureOpenAIProvider:
    def __init__(self, profile: Profile, *, transport: httpx.BaseTransport | None = None):
        self.profile = profile
        self._transport = transport
        p = self.profile

        raw_endpoint = (
            p.setting("endpoint")
            or p.setting("azure_endpoint")
            or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        )
        if not raw_endpoint:
            raise ProviderError("Azure OpenAI requires 'endpoint' in profile settings or AZURE_OPENAI_ENDPOINT env.")
        self.endpoint = raw_endpoint.rstrip("/")
        self.clean_endpoint = sanitize_url(self.endpoint)

        self.deployment = p.setting("deployment") or p.model
        self.api_version = p.setting("api_version", "2024-08-01-preview")

        key_env_var = validate_api_key_env(p.setting("api_key_env", "AZURE_OPENAI_API_KEY"))
        self.api_key = p.setting("api_key") or os.environ.get(key_env_var, "")
        if not self.api_key:
            raise ProviderError(f"Azure OpenAI requires an API key in {key_env_var} or profile 'api_key'.")

        self.timeout = float(p.setting("timeout", 60.0))

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        chat_messages = [{"role": "system", "content": system}, *messages]

        response_format: dict[str, Any] = {
            "type": "json_schema",
            "json_schema": {
                "name": "azure_response",
                "strict": True,
                "schema": schema,
            },
        }

        is_reasoning = (
            p.model.startswith(("o1", "o3", "gpt-5"))
            or str(self.deployment).startswith(("o1", "o3", "gpt-5"))
            or bool(p.setting("reasoning", False))
        )

        payload: dict[str, Any] = {
            "messages": chat_messages,
            "response_format": response_format,
        }

        temp = p.setting("temperature")
        if not is_reasoning and temp is not None and not p.setting("omit_temperature", False):
            payload["temperature"] = float(temp)

        max_tokens_val = p.setting("max_tokens") or p.setting("max_completion_tokens")
        if max_tokens_val:
            if is_reasoning or p.setting("max_completion_tokens"):
                payload["max_completion_tokens"] = int(max_tokens_val)
            else:
                payload["max_tokens"] = int(max_tokens_val)

        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Could not connect to Azure OpenAI at {self.clean_endpoint}. Check network and proxy settings."
            ) from e
        except httpx.TimeoutException as e:
            raise ProviderError(
                f"Request to Azure OpenAI deployment '{self.deployment}' timed out after {self.timeout}s."
            ) from e
        except Exception as e:
            raise ProviderError(f"HTTP request to Azure OpenAI failed: {e}") from e

        if resp.status_code in (401, 403):
            raise ProviderError(
                f"Azure OpenAI authentication failed (HTTP {resp.status_code}). Check AZURE_OPENAI_API_KEY."
            )
        if resp.status_code == 404:
            raise ProviderError(
                f"Deployment '{self.deployment}' not found at {self.clean_endpoint} (HTTP 404)."
            )
        if resp.status_code == 429:
            raise ProviderError(
                f"Azure OpenAI TPM/RPM rate limit exceeded on deployment '{self.deployment}' (HTTP 429)."
            )
        if resp.is_error:
            error_msg = scrub_error_text(resp.text)
            raise ProviderError(
                f"Azure OpenAI error ({resp.status_code}): {error_msg}"
            )

        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(f"Invalid JSON from Azure OpenAI: {e}") from e

        if not isinstance(data, dict):
            raise ProviderError(f"Expected JSON object from Azure OpenAI, got {type(data).__name__}")

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise ProviderError("No choices returned by Azure OpenAI.")

        choice = choices[0]
        if not isinstance(choice, dict):
            raise ProviderError("Malformed choice in response from Azure OpenAI.")

        finish_reason = choice.get("finish_reason")
        msg = choice.get("message")
        if not isinstance(msg, dict):
            raise ProviderError("Missing message in response from Azure OpenAI.")

        refusal = msg.get("refusal")
        if refusal:
            raise ProviderError(f"Model refused request: {refusal}")

        if finish_reason == "content_filter":
            raise ProviderError("Azure content management policy filtered the response.")
        if finish_reason == "length":
            raise ProviderError("Output hit max_tokens before completing schema.")

        text = msg.get("content") or ""
        usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}

        return ProviderResult(
            text=text,
            model_served=data.get("model", self.deployment),
            stop_reason=finish_reason,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            request_id=data.get("id"),
        )
