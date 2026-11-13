"""Claude via the official Anthropic SDK, with schema-constrained output."""

from __future__ import annotations

from typing import Any

import anthropic

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    def __init__(self, profile: Profile):
        self.profile = profile
        # Credentials resolve from ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = anthropic.Anthropic()

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if p.setting("effort"):
            output_config["effort"] = p.setting("effort")
        kwargs: dict[str, Any] = {
            "model": p.model,
            "max_tokens": int(p.setting("max_tokens", 16000)),
            "system": system,
            "messages": messages,
            "output_config": output_config,
        }
        try:
            if p.setting("refusal_fallback", False):
                response = self.client.beta.messages.create(
                    betas=[FALLBACK_BETA], fallbacks="default", **kwargs
                )
            else:
                response = self.client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise ProviderError("Anthropic authentication failed. Check ANTHROPIC_API_KEY.") from e
        except anthropic.NotFoundError as e:
            raise ProviderError(f"Model '{p.model}' not found: {e.message}") from e
        except anthropic.RateLimitError as e:
            raise ProviderError(f"Rate limited after SDK retries: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"Anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("Could not reach the Anthropic API. Check the network.") from e
        except TypeError as e:
            if "authentication" not in str(e).lower():
                raise
            raise ProviderError("No Anthropic credentials found. Add ANTHROPIC_API_KEY to .env "
                                "(the harness loads it at start-up).") from e

        stop = response.stop_reason
        if stop == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise ProviderError(f"Model refused (category: {category})")
        if stop == "max_tokens":
            raise ProviderError("Output hit max_tokens before finishing; raise max_tokens.")

        text = next((b.text for b in response.content if b.type == "text"), "")
        usage = response.usage
        return ProviderResult(
            text=text,
            model_served=response.model,
            stop_reason=stop,
            tokens_in=getattr(usage, "input_tokens", None),
            tokens_out=getattr(usage, "output_tokens", None),
            request_id=getattr(response, "_request_id", None),
            meta={"fallback_requested": bool(p.setting("refusal_fallback", False))},
        )
