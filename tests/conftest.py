from __future__ import annotations

import pytest

from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.models.fake_provider import FakeProvider


@pytest.fixture
def cfg(tmp_path) -> HarnessConfig:
    return HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        max_attempts=3,
        roles={"generator": "fake-gen", "reviewer": "fake-rev"},
        profiles={
            "fake-gen": Profile(name="fake-gen", provider="fake", model="fake-model-a"),
            "fake-rev": Profile(name="fake-rev", provider="fake", model="fake-model-b"),
        },
    )


@pytest.fixture
def audit(cfg) -> AuditStore:
    return AuditStore(cfg.resolved_db_path())


@pytest.fixture(autouse=True)
def reset_fake():
    FakeProvider.queue.clear()
    FakeProvider.calls.clear()
    yield
    FakeProvider.queue.clear()
    FakeProvider.calls.clear()
