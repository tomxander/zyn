"""Google Cloud Vertex AI & Gemini provider, with schema-constrained output.

Supports Google Cloud Vertex AI (via Project & Location) and Gemini API endpoints.
Uses httpx (already a core dependency).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult
from harness.models.security import sanitize_url, scrub_error_text, validate_api_key_env


class VertexAIProvider:
    def __init__(self, profile: Profile, *, transport: httpx.BaseTransport | None = None):
        self.profile = profile
        self._transport = transport
        p = self.profile

        self.project = (
            p.setting("project")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT", "")
        )
        self.location = p.setting("location", "us-central1")
        self.timeout = float(p.setting("timeout", 60.0))

        key_env_var = validate_api_key_env(p.setting("api_key_env", "GEMINI_API_KEY"))
        self.api_key = p.setting("api_key") or os.environ.get(key_env_var, "")
        self.bearer_token = (
            os.environ.get("VERTEX_BEARER_TOKEN")
            or os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "")
        )

        # Try to obtain token from google-auth if installed and project given without explicit key/token
        if not self.api_key and not self.bearer_token and self.project:
            try:
                import google.auth
                import google.auth.transport.requests

                creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                auth_req = google.auth.transport.requests.Request()
                creds.refresh(auth_req)
                self.bearer_token = creds.token
            except ImportError:
                # google-auth is not installed
                self.bearer_token = ""
            except Exception:  # noqa: BLE001
                self.bearer_token = ""

        if not self.api_key and not self.bearer_token:
            if self.project:
                raise ProviderError(
                    "Google Vertex AI requires 'google-auth' to authenticate with project credentials. "
                    "Install it with: pip install 'zyn-harness[vertex]' or provide an API key in GEMINI_API_KEY."
                )
            raise ProviderError(
                "Google Vertex/Gemini requires GEMINI_API_KEY or (project + credentials) in environment."
            )

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        model_name = p.model
        max_tokens = int(p.setting("max_tokens", 8192))
        temperature = float(p.setting("temperature", 0.0))

        headers = {"Content-Type": "application/json"}

        if self.project and self.bearer_token:
            # Vertex AI regional endpoint (global uses aiplatform.googleapis.com)
            host = (
                "aiplatform.googleapis.com"
                if self.location == "global"
                else f"{self.location}-aiplatform.googleapis.com"
            )
            url = (
                f"https://{host}/v1/projects/{self.project}/locations/{self.location}/"
                f"publishers/google/models/{model_name}:generateContent"
            )
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            # Direct Gemini endpoint (pass key in header, not query string)
            # Only prefix gemini- if the model clearly is a bare Gemini version number
            if model_name.startswith("gemini-") or not any(model_name.startswith(pfx) for pfx in ("gemini", "gemma", "claude")):
                clean_model = model_name if model_name.startswith("gemini-") else f"gemini-{model_name}"
            else:
                clean_model = model_name
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent"
            headers["x-goog-api-key"] = self.api_key
        else:
            raise ProviderError("No valid credentials for Google Vertex/Gemini.")

        clean_url = sanitize_url(url)

        # Build Gemini contents structure
        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("user", "system") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.get("content", "")}],
            })

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}],
            }

        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.ConnectError as e:
            raise ProviderError(f"Could not connect to Google Vertex/Gemini at {clean_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to Google Vertex/Gemini timed out after {self.timeout}s.") from e
        except Exception as e:
            raise ProviderError(f"Google Vertex/Gemini HTTP error: {e}") from e

        if resp.status_code in (401, 403):
            raise ProviderError(
                f"Google Vertex/Gemini authentication failed (HTTP {resp.status_code}). Check your credentials."
            )
        if resp.status_code == 429:
            raise ProviderError("Google Vertex/Gemini quota or rate limit exceeded (HTTP 429).")
        if resp.is_error:
            error_body = scrub_error_text(resp.text)
            raise ProviderError(f"Google Vertex/Gemini error ({resp.status_code}): {error_body}")

        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(f"Invalid JSON response from Google Vertex/Gemini: {e}") from e

        if not isinstance(data, dict):
            raise ProviderError(f"Expected JSON object from Google Vertex, got {type(data).__name__}")

        candidates = data.get("candidates")
        if not candidates or not isinstance(candidates, list):
            feedback = data.get("promptFeedback", {}) if isinstance(data.get("promptFeedback"), dict) else {}
            block_reason = feedback.get("blockReason")
            if block_reason:
                raise ProviderError(f"Request blocked by Google safety filters (reason: {block_reason}).")
            raise ProviderError("No completion candidates returned by Google Vertex/Gemini.")

        cand = candidates[0]
        if not isinstance(cand, dict):
            raise ProviderError("Malformed candidate in Google Vertex response.")

        finish_reason = cand.get("finishReason")
        if finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
            raise ProviderError(f"Model refused request on Google Vertex (reason: {finish_reason}).")
        if finish_reason == "MAX_TOKENS":
            raise ProviderError("Output hit maxOutputTokens before completing schema.")

        content = cand.get("content", {}) if isinstance(cand.get("content"), dict) else {}
        parts = content.get("parts", []) if isinstance(content.get("parts"), list) else []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))

        usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata"), dict) else {}
        served_model = data.get("modelVersion") or data.get("model") or model_name

        tokens_in = usage.get("promptTokenCount")
        tokens_out = usage.get("candidatesTokenCount")
        thoughts_tokens = usage.get("thoughtsTokenCount", 0)
        if thoughts_tokens and tokens_out is not None:
            tokens_out += thoughts_tokens

        return ProviderResult(
            text=text,
            model_served=served_model,
            stop_reason=finish_reason,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            meta={"thoughts_token_count": thoughts_tokens, "total_token_count": usage.get("totalTokenCount")},
        )
