"""Local open-weight models via Ollama, with schema-constrained output."""

from __future__ import annotations

from typing import Any

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult


class OllamaProvider:
    def __init__(self, profile: Profile, *, transport: Any = None):
        import ollama

        from harness.models.security import build_offline_transport

        self.profile = profile
        self._ollama = ollama
        host = profile.setting("host", "http://localhost:11434")
        self._transport = transport
        if self._transport is None:
            verify_opt = profile.setting("ca_bundle") or profile.setting("verify", True)
            pinned_t, _ = build_offline_transport(
                host,
                verify=verify_opt,
                retries=int(profile.setting("retries", 0)),
                http2=bool(profile.setting("http2", False)),
            )
            self._transport = pinned_t

        client_kwargs: dict[str, Any] = {
            "host": host,
            "trust_env": False,
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        self.client = ollama.Client(**client_kwargs)

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        options: dict[str, Any] = {}
        if p.setting("temperature") is not None:
            options["temperature"] = p.setting("temperature")
        if p.setting("num_ctx") is not None:
            options["num_ctx"] = p.setting("num_ctx")
        try:
            response = self.client.chat(
                model=p.model,
                messages=[{"role": "system", "content": system}, *messages],
                format=schema,
                options=options or None,
            )
        except self._ollama.ResponseError as e:
            raise ProviderError(f"Ollama error for '{p.model}': {e}") from e
        except ConnectionError as e:
            raise ProviderError("Could not reach Ollama. Is the Ollama app running?") from e
        except Exception as e:  # httpx connection errors surface with varied types
            if "connect" in str(e).lower():
                raise ProviderError("Could not reach Ollama. Is the Ollama app running?") from e
            raise

        return ProviderResult(
            text=response.message.content or "",
            model_served=getattr(response, "model", None) or p.model,
            stop_reason=getattr(response, "done_reason", None),
            tokens_in=getattr(response, "prompt_eval_count", None),
            tokens_out=getattr(response, "eval_count", None),
        )
