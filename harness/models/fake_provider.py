"""Scripted provider for offline tests. Returns queued responses in order."""

from __future__ import annotations

from typing import Any, ClassVar

from harness.config import Profile
from harness.models.base import ProviderResult


class FakeProvider:
    queue: ClassVar[list[str]] = []  # shared so tests can preload before the provider is built
    calls: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, profile: Profile):
        self.profile = profile

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        FakeProvider.calls.append({"system": system, "messages": messages, "schema": schema})
        if not FakeProvider.queue:
            raise AssertionError("FakeProvider queue is empty")
        return ProviderResult(
            text=FakeProvider.queue.pop(0),
            model_served=self.profile.model,
            stop_reason="end_turn",
            tokens_in=10,
            tokens_out=10,
        )
