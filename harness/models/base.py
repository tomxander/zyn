"""Provider interface. Each provider turns (system, messages, schema) into JSON text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from harness.config import Profile


class ProviderError(RuntimeError):
    """The provider could not produce a usable response (network, auth, refusal, cut-off)."""


@dataclass
class ProviderResult:
    text: str
    model_served: str
    stop_reason: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    request_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    profile: Profile

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult: ...


def get_provider(profile: Profile, *, transport: Any = None) -> Provider:
    """Builds the provider named in the profile. Imports lazily so a missing
    optional backend does not break the others."""
    try:
        if profile.provider == "anthropic":
            from harness.models.anthropic_provider import AnthropicProvider

            return AnthropicProvider(profile)
        if profile.provider == "ollama":
            from harness.models.ollama_provider import OllamaProvider

            return OllamaProvider(profile, transport=transport)
        if profile.provider == "fake":
            from harness.models.fake_provider import FakeProvider

            return FakeProvider(profile)
        if profile.provider == "openai":
            from harness.models.openai_provider import OpenAIProvider

            return OpenAIProvider(profile, transport=transport)
        if profile.provider == "azure":
            from harness.models.azure_provider import AzureOpenAIProvider

            return AzureOpenAIProvider(profile, transport=transport)
        if profile.provider == "bedrock":
            from harness.models.bedrock_provider import BedrockProvider

            return BedrockProvider(profile)
        if profile.provider == "vertex":
            from harness.models.vertex_provider import VertexAIProvider

            return VertexAIProvider(profile, transport=transport)
        raise ProviderError(f"Unknown provider '{profile.provider}' in profile '{profile.name}'")
    except ProviderError:
        raise
    except Exception as e:
        raise ProviderError(f"Failed to initialize provider '{profile.provider}': {e}") from e
