"""Unit tests for enterprise model connectors (Project 2 & Batch F).

Tests OpenAI/vLLM, Azure OpenAI, AWS Bedrock, and Google Vertex AI providers.
All external network calls use httpx.MockTransport or mocked SDK sessions.
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from harness.audit.store import AuditStore
from harness.config import HarnessConfig, Profile
from harness.models.azure_provider import AzureOpenAIProvider
from harness.models.base import ProviderError
from harness.models.bedrock_provider import BedrockProvider
from harness.models.openai_provider import OpenAIProvider
from harness.models.readiness import profile_readiness
from harness.models.runner import StructuredOutputFailure, structured_call
from harness.models.security import (
    models_match,
    sanitize_url,
    scrub_error_text,
    validate_and_pin_offline_host,
    validate_api_key_env,
)
from harness.models.vertex_provider import VertexAIProvider


class SimpleOutput(BaseModel):
    verdict: str


@pytest.fixture(autouse=True)
def clean_cloud_env(monkeypatch):
    """Ensure ambient developer credentials do not pollute test assertions."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("VERTEX_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)


# ==============================================================================
# Security & Secret Scrubbing (Finding 5)
# ==============================================================================


def test_sanitize_url():
    assert sanitize_url("http://admin:secret123@127.0.0.1:8000/v1") == "http://127.0.0.1:8000/v1"
    assert sanitize_url("https://key:pass@myapi.com/path?key=secret") == "https://myapi.com/path"
    assert sanitize_url("http://localhost:8080") == "http://localhost:8080"


def test_scrub_error_text():
    raw = "Error 401: Bearer eyJhbGciOiJIUzI1NiJ9.secret and api_key='sk-1234567890abcdef'"
    scrubbed = scrub_error_text(raw)
    assert "Bearer [REDACTED]" in scrubbed
    assert "api_key=[REDACTED]" in scrubbed
    assert "sk-1234567890abcdef" not in scrubbed


def test_validate_api_key_env():
    with pytest.raises(ValueError, match="forbidden"):
        validate_api_key_env("ZYN_DATABASE_PASSWORD")
    with pytest.raises(ValueError, match="forbidden"):
        validate_api_key_env("SESSION_SECRET")
    assert validate_api_key_env("MY_CORP_API_KEY") == "MY_CORP_API_KEY"


# ==============================================================================
# OpenAI / vLLM Provider (Findings 1, 4, 5, 10)
# ==============================================================================


def test_openai_provider_mock_transport():
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "model": "qwen-2.5-72b",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"verdict": "passed"}'},
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
        )

    profile = Profile(
        name="test-vllm",
        provider="openai",
        model="qwen-2.5-72b",
        base_url="http://127.0.0.1:8000/v1",
        api_key="vllm-secret",
    )
    provider = OpenAIProvider(profile, transport=httpx.MockTransport(handler))
    res = provider.generate("sys", [{"role": "user", "content": "hi"}], {"type": "object"})

    assert res.text == '{"verdict": "passed"}'
    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert req.headers["Authorization"] == "Bearer vllm-secret"
    assert req.url == "http://127.0.0.1:8000/v1/chat/completions"
    body = json.loads(req.content.decode("utf-8"))
    assert body["response_format"]["type"] == "json_schema"


def test_openai_provider_reasoning_models():
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": '{"verdict": "ok"}'}}],
            },
        )

    # For reasoning model (o1-mini), max_completion_tokens must be sent and temperature omitted
    profile = Profile(
        name="test-o1",
        provider="openai",
        model="o1-mini",
        base_url="http://127.0.0.1:8000/v1",
        max_tokens=2000,
        temperature=0.7,
    )
    provider = OpenAIProvider(profile, transport=httpx.MockTransport(handler))
    provider.generate("sys", [{"role": "user", "content": "hi"}], {})

    req = recorded_requests[0]
    body = json.loads(req.content.decode("utf-8"))
    assert "temperature" not in body  # Omitted for reasoning models
    assert body["max_completion_tokens"] == 2000
    assert "max_tokens" not in body


def test_openai_provider_refusal_and_malformed():
    # 1. Model refusal
    def refusal_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"refusal": "I cannot answer this"}}],
            },
        )

    p1 = Profile(name="p1", provider="openai", model="gpt-4o", base_url="http://127.0.0.1:8000/v1")
    prov1 = OpenAIProvider(p1, transport=httpx.MockTransport(refusal_handler))
    with pytest.raises(ProviderError, match="refused"):
        prov1.generate("sys", [], {})

    # 2. Malformed JSON structure (not dict)
    def malformed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected", "list"])

    prov2 = OpenAIProvider(p1, transport=httpx.MockTransport(malformed_handler))
    with pytest.raises(ProviderError, match="Expected JSON object"):
        prov2.generate("sys", [], {})


# ==============================================================================
# Azure OpenAI Provider (Findings 4, 10)
# ==============================================================================


def test_azure_provider_request_shape():
    recorded = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": '{"verdict": "ok"}'}}],
            },
        )

    profile = Profile(
        name="test-az",
        provider="azure",
        model="gpt-4o",
        endpoint="https://mycorp.openai.azure.com",
        deployment="deploy-4o",
        api_key="secret-azure",
        api_version="2024-10-21",
    )
    provider = AzureOpenAIProvider(profile, transport=httpx.MockTransport(handler))
    provider.generate("sys", [{"role": "user", "content": "test"}], {})

    assert len(recorded) == 1
    req = recorded[0]
    assert req.headers["api-key"] == "secret-azure"
    assert "openai/deployments/deploy-4o/chat/completions?api-version=2024-10-21" in str(req.url)


# ==============================================================================
# AWS Bedrock Provider (Findings 6, 7, 8)
# ==============================================================================


def test_bedrock_requires_region():
    profile = Profile(name="test-bedrock", provider="bedrock", model="claude")
    with (
        patch.dict("sys.modules", {"boto3": MagicMock(), "botocore.exceptions": MagicMock()}),
        pytest.raises(ProviderError, match="explicit 'region'"),
    ):
        BedrockProvider(profile)


def test_bedrock_anthropic_tools_shape():
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_boto3.Session.return_value.client.return_value = mock_client

    recorded_body = {}

    def fake_invoke(modelId, contentType, accept, body):
        nonlocal recorded_body
        recorded_body = json.loads(body)
        resp_obj = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "return_structured_result",
                    "input": {"verdict": "bedrock-ok"},
                }
            ],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }
        return {"body": io.BytesIO(json.dumps(resp_obj).encode("utf-8")), "ResponseMetadata": {}}

    mock_client.invoke_model.side_effect = fake_invoke

    with patch.dict("sys.modules", {"boto3": mock_boto3, "botocore.exceptions": MagicMock()}):
        profile = Profile(
            name="b-claude",
            provider="bedrock",
            model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region="us-west-2",
        )
        provider = BedrockProvider(profile)
        res = provider.generate("sys", [{"role": "user", "content": "hi"}], {"type": "object"})

        assert res.text == '{"verdict": "bedrock-ok"}'
        assert "tools" in recorded_body
        assert recorded_body["tool_choice"]["name"] == "return_structured_result"
        assert models_match(profile.model, res.model_served)


def test_bedrock_converse_tool_config():
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_boto3.Session.return_value.client.return_value = mock_client

    recorded_kwargs = {}

    def fake_converse(**kwargs):
        nonlocal recorded_kwargs
        recorded_kwargs = kwargs
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "name": "return_structured_result",
                                "input": {"verdict": "converse-ok"},
                            }
                        }
                    ]
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 50, "outputTokens": 10},
        }

    mock_client.converse.side_effect = fake_converse

    with patch.dict("sys.modules", {"boto3": mock_boto3, "botocore.exceptions": MagicMock()}):
        profile = Profile(
            name="b-llama",
            provider="bedrock",
            model="meta.llama3-70b-instruct-v1:0",
            region="us-east-1",
        )
        provider = BedrockProvider(profile)
        res = provider.generate("sys", [{"role": "user", "content": "hi"}], {"type": "object"})

        assert res.text == '{"verdict": "converse-ok"}'
        assert "toolConfig" in recorded_kwargs
        assert recorded_kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == "return_structured_result"


# ==============================================================================
# Google Cloud Vertex AI Provider (Findings 3, 5, 9)
# ==============================================================================


def test_vertex_unbound_local_error_fixed():
    """Finding 3: missing google-auth raises ProviderError without UnboundLocalError."""
    with patch.dict("sys.modules", {"google.auth": None}):
        profile = Profile(name="v-proj", provider="vertex", model="gemini-1.5-pro", project="my-project")
        with pytest.raises(ProviderError, match="requires 'google-auth'"):
            VertexAIProvider(profile)


def test_vertex_request_shape_and_header_key():
    """Finding 5 & 9: API key in header, responseJsonSchema, global location."""
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={
                "modelVersion": "gemini-1.5-pro-002",
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": '{"verdict": "vertex-ok"}'}]},
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 20,
                    "candidatesTokenCount": 10,
                    "thoughtsTokenCount": 5,
                },
            },
        )

    # 1. API key in header, not in URL query
    profile_key = Profile(name="v-key", provider="vertex", model="gemini-1.5-pro", api_key="secret-gemini-key")
    prov_key = VertexAIProvider(profile_key, transport=httpx.MockTransport(handler))
    res = prov_key.generate("sys", [{"role": "user", "content": "hi"}], {"type": "object"})

    assert res.text == '{"verdict": "vertex-ok"}'
    req = recorded_requests[0]
    assert req.headers["x-goog-api-key"] == "secret-gemini-key"
    assert "key=" not in str(req.url)
    body = json.loads(req.content.decode("utf-8"))
    assert "responseJsonSchema" in body["generationConfig"]
    assert res.tokens_out == 15  # 10 candidates + 5 thoughts

    # 2. Location 'global' uses aiplatform.googleapis.com
    recorded_requests.clear()
    profile_global = Profile(
        name="v-glob",
        provider="vertex",
        model="gemma-3-27b-it",  # non-gemini model name must not be prefixed
        project="test-proj",
        location="global",
    )
    with patch.dict("os.environ", {"VERTEX_BEARER_TOKEN": "mock-token"}):
        prov_glob = VertexAIProvider(profile_global, transport=httpx.MockTransport(handler))
        prov_glob.generate("sys", [], {})

        req = recorded_requests[0]
        assert "https://aiplatform.googleapis.com/v1/projects/test-proj/locations/global/publishers/google/models/gemma-3-27b-it" in str(req.url)


def test_vertex_safety_finish_reason():
    def safety_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [{"finishReason": "SAFETY", "content": {}}],
            },
        )

    profile = Profile(name="v-safe", provider="vertex", model="gemini-1.5-pro", api_key="key")
    prov = VertexAIProvider(profile, transport=httpx.MockTransport(safety_handler))
    with pytest.raises(ProviderError, match="SAFETY"):
        prov.generate("sys", [], {})


# ==============================================================================
# Runner Integration & Offline Rules (Findings 1, 2, 4)
# ==============================================================================


def test_runner_offline_mode_bypass_prevention(tmp_path):
    audit = AuditStore(tmp_path / "audit.sqlite")

    # 1. String "false" is rejected
    cfg1 = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        offline=True,
        roles={"reviewer": "bad-string"},
        profiles={
            "bad-string": Profile(name="bad-string", provider="openai", model="gpt-4o", local="false")
        },
    )
    with pytest.raises(StructuredOutputFailure, match="offline mode"):
        structured_call(
            cfg=cfg1,
            audit=audit,
            run_id="r1",
            role_or_profile="reviewer",
            task="t",
            prompt_version="v1",
            system="sys",
            user="usr",
            output_model=SimpleOutput,
        )

    # 2. Public base_url with local: True is blocked before network call
    cfg2 = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        offline=True,
        roles={"reviewer": "fake-local"},
        profiles={
            "fake-local": Profile(
                name="fake-local",
                provider="openai",
                model="gpt-4o",
                local=True,
                base_url="https://api.openai.com/v1",
            )
        },
    )
    with pytest.raises(StructuredOutputFailure, match="offline mode"):
        structured_call(
            cfg=cfg2,
            audit=audit,
            run_id="r1",
            role_or_profile="reviewer",
            task="t",
            prompt_version="v1",
            system="sys",
            user="usr",
            output_model=SimpleOutput,
        )

    # 3. Bedrock with local: True is rejected
    cfg3 = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        offline=True,
        roles={"reviewer": "b-local"},
        profiles={
            "b-local": Profile(name="b-local", provider="bedrock", model="claude", local=True, region="us-east-1")
        },
    )
    with pytest.raises(StructuredOutputFailure, match="offline mode"):
        structured_call(
            cfg=cfg3,
            audit=audit,
            run_id="r1",
            role_or_profile="reviewer",
            task="t",
            prompt_version="v1",
            system="sys",
            user="usr",
            output_model=SimpleOutput,
        )

    # 4. Ollama cloud model rejected in offline mode
    cfg4 = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        offline=True,
        roles={"reviewer": "ol-cloud"},
        profiles={
            "ol-cloud": Profile(name="ol-cloud", provider="ollama", model="deepseek-v3:cloud")
        },
    )
    with pytest.raises(StructuredOutputFailure, match="cloud model"):
        structured_call(
            cfg=cfg4,
            audit=audit,
            run_id="r1",
            role_or_profile="reviewer",
            task="t",
            prompt_version="v1",
            system="sys",
            user="usr",
            output_model=SimpleOutput,
        )


def test_runner_offline_allowed_local_openai(tmp_path):
    audit = AuditStore(tmp_path / "audit.sqlite")
    cfg = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        offline=True,
        roles={"reviewer": "vllm-box"},
        profiles={
            "vllm-box": Profile(
                name="vllm-box",
                provider="openai",
                model="qwen",
                local=True,
                base_url="http://127.0.0.1:8000/v1",
            )
        },
    )

    fake_resp = {
        "choices": [{"finish_reason": "stop", "message": {"content": '{"verdict": "local-pass"}'}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fake_resp)

    res = structured_call(
        cfg=cfg,
        audit=audit,
        run_id="r1",
        role_or_profile="reviewer",
        task="t",
        prompt_version="v1",
        system="sys",
        user="usr",
        output_model=SimpleOutput,
        transport=httpx.MockTransport(handler),
    )
    assert res.output.verdict == "local-pass"

    events = audit.events()
    gen = next(e for e in events if e["action"] == "generated")
    assert "offline_exemption" in gen["detail"]


def test_runner_provider_construction_error_logged(tmp_path):
    """Finding 2: provider construction failure logs provider_error and raises StructuredOutputFailure."""
    audit = AuditStore(tmp_path / "audit.sqlite")

    # Missing API key in Azure profile causes ProviderError on construction
    cfg = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        roles={"reviewer": "keyless-azure"},
        profiles={
            "keyless-azure": Profile(
                name="keyless-azure",
                provider="azure",
                model="gpt-4o",
                endpoint="https://mycorp.openai.azure.com",
            )
        },
    )

    with pytest.raises(StructuredOutputFailure, match="requires an API key"):
        structured_call(
            cfg=cfg,
            audit=audit,
            run_id="r1",
            role_or_profile="reviewer",
            task="t",
            prompt_version="v1",
            system="sys",
            user="usr",
            output_model=SimpleOutput,
        )

    events = audit.events()
    err_event = next(e for e in events if e["action"] == "provider_error")
    assert err_event["detail"]["phase"] == "construction"


def test_profile_readiness_consistency():
    """Finding 11: profile_readiness reports correct readiness across providers."""
    cfg = HarnessConfig(
        db_path="runs/audit.sqlite",
        offline=True,
        roles={"reviewer": "az"},
        profiles={
            "az": Profile(name="az", provider="azure", model="gpt-4o"),
            "vllm": Profile(name="vllm", provider="openai", model="qwen", local=True, base_url="http://127.0.0.1:8000/v1"),
        },
    )

    ok_az, reason_az = profile_readiness(cfg, "az")
    assert not ok_az
    assert "offline" in reason_az

    ok_vllm, reason_vllm = profile_readiness(cfg, "vllm")
    assert ok_vllm
    assert reason_vllm == "configured"


def test_batch_i_wildcard_and_metadata_addresses_refused():
    """Batch I finding 4: Refuse 0.0.0.0, ::, and metadata addresses 169.254.169.254 and fd00:ec2::254."""
    from harness.models.security import is_offline_host

    assert is_offline_host("0.0.0.0")[0] is False
    assert is_offline_host("http://0.0.0.0:8000")[0] is False
    assert is_offline_host("::")[0] is False
    assert is_offline_host("http://[::]:8000")[0] is False

    assert is_offline_host("169.254.169.254")[0] is False
    assert is_offline_host("http://169.254.169.254/latest/meta-data/")[0] is False
    assert is_offline_host("fd00:ec2::254")[0] is False
    assert is_offline_host("http://[fd00:ec2::254]/")[0] is False


def test_batch_i_models_match_size_and_family():
    """Batch I finding 5: models_match normalises prefixes/suffixes but distinguishes size and family."""
    # Different family / size must warn (return False)
    assert models_match("gpt-4o", "gpt-4") is False
    assert models_match("gpt-4o", "gpt-4o-mini") is False
    assert models_match("llama3:70b", "llama3:8b") is False
    assert models_match("claude-3-5-sonnet", "claude-3-5-haiku") is False
    assert models_match("claude-3-haiku", "claude-3-opus") is False

    # Normalised prefixes match
    assert models_match("anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-3-5-sonnet-20241022") is True
    assert models_match("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-3-5-sonnet-20241022") is True
    assert models_match("publishers/google/models/gemini-1.5-pro", "gemini-1.5-pro") is True


def test_batch_i_scrub_error_text_bare_keys():
    """Batch I finding 6: scrub_error_text redacts bare keys (sk-proj, sk-ant, AKIA, AIza)."""
    assert "sk-proj-" not in scrub_error_text("Failed with key sk-proj-abc1234567890xyz12345")
    assert "[REDACTED_API_KEY]" in scrub_error_text("Failed with key sk-proj-abc1234567890xyz12345")

    assert "sk-ant-" not in scrub_error_text("Error: sk-ant-api03-abcdefghijklmn12345")
    assert "[REDACTED_API_KEY]" in scrub_error_text("Error: sk-ant-api03-abcdefghijklmn12345")

    assert "AKIA" not in scrub_error_text("AWS key AKIAIOSFODNN7EXAMPLE rejected")
    assert "[REDACTED_AWS_KEY]" in scrub_error_text("AWS key AKIAIOSFODNN7EXAMPLE rejected")

    assert "AIza" not in scrub_error_text("Google key AIzaSyD12345678901234567890123456789012 invalid")
    assert "[REDACTED_GOOGLE_KEY]" in scrub_error_text("Google key AIzaSyD12345678901234567890123456789012 invalid")


def test_batch_i_offline_allowed_hosts_config():
    """Batch I finding 3: offline_allowed_hosts in config model permits listed host and rejects others."""
    from harness.models.security import is_offline_host

    cfg = HarnessConfig(
        db_path="runs/audit.sqlite",
        offline=True,
        offline_allowed_hosts=["custom-vllm.corp.local"],
        roles={"reviewer": "vllm"},
        profiles={
            "vllm": Profile(name="vllm", provider="openai", model="qwen", local=True, base_url="http://custom-vllm.corp.local:8000/v1"),
        },
    )
    assert cfg.offline_allowed_hosts == ["custom-vllm.corp.local"]
    ok, _ = is_offline_host("http://custom-vllm.corp.local:8000/v1", cfg.offline_allowed_hosts)
    assert ok is True

    # Other external host is blocked
    ok_ext, _ = is_offline_host("http://external-api.corp.local:8000/v1", cfg.offline_allowed_hosts)
    assert ok_ext is False


def test_batch_i_proxy_and_dns_pinning(monkeypatch):
    """Batch I findings 1 and 2: local provider sets trust_env=False and pins target."""
    monkeypatch.setenv("HTTP_PROXY", "http://corporate-proxy:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://corporate-proxy:8080")

    p = Profile(name="local", provider="openai", model="qwen", local=True, base_url="http://127.0.0.1:8000/v1")
    prov = OpenAIProvider(p)
    assert prov.is_local is True

    # Ollama client also sets trust_env=False
    p_ollama = Profile(name="ol", provider="ollama", model="llama3")
    from harness.models.ollama_provider import OllamaProvider
    prov_ol = OllamaProvider(p_ollama)
    assert prov_ol.client._client.trust_env is False


def test_batch_k_dns_pinning_single_lookup_and_no_fallback(monkeypatch):
    """Batch K finding 1: single DNS resolution, checks all returned IPs, pins to that IP, no unpinned fallback."""
    import socket

    from harness.models.base import ProviderError
    from harness.models.security import validate_and_pin_offline_host

    # 1. Single lookup checks all IPs; if any is public, fails
    mock_addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.5", 80)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80)),
    ]
    lookup_count = 0

    def mock_getaddrinfo(host, port):
        nonlocal lookup_count
        lookup_count += 1
        return mock_addrs

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
    ok, reason, _host, pin = validate_and_pin_offline_host("http://internal.company.com:8000")
    assert lookup_count == 1
    assert ok is False
    assert "public IP address" in reason
    assert pin is None

    # 2. OpenAI with local: true pointing to invalid/public endpoint raises ProviderError without fallback
    p = Profile(name="bad_local", provider="openai", model="qwen", local=True, base_url="http://internal.company.com:8000/v1")
    with pytest.raises(ProviderError, match="Offline validation failed"):
        OpenAIProvider(p)


def test_batch_k_ollama_pinned_transport_and_readiness():
    """Batch K finding 2: Ollama provider receives pinned transport, and readiness check sets trust_env=False."""
    import inspect

    import httpx

    from harness.models import readiness
    from harness.models.ollama_provider import OllamaProvider

    custom_transport = httpx.HTTPTransport(trust_env=False)
    p = Profile(name="ol", provider="ollama", model="llama3")
    prov = OllamaProvider(p, transport=custom_transport)
    assert prov.client._client._transport is custom_transport
    assert prov.client._client.trust_env is False

    # Readiness check source contains trust_env=False
    src = inspect.getsource(readiness.profile_readiness)
    assert "ollama.Client(host=host, timeout=3, trust_env=False)" in src


def test_batch_k_pinned_pool_preserves_settings():
    """Batch K finding 3: PinnedHTTPTransport preserves limits, retries, and http2 settings."""
    import httpx

    from harness.models.security import PinnedHTTPTransport

    limits = httpx.Limits(max_connections=50, max_keepalive_connections=15)
    transport = PinnedHTTPTransport(
        "api.local",
        "127.0.0.1",
        limits=limits,
        retries=3,
        http2=True,
    )
    assert transport._pool._max_connections == 50
    assert transport._pool._retries == 3
    assert transport._pool._http2 is True


def test_batch_k_models_match_strict_versions_and_empty_served(tmp_path, monkeypatch):
    """Batch K finding 4: models_match distinguishes version/dated releases; empty served model warns."""
    # -vN versions must NOT match
    assert models_match("deepseek-v2", "deepseek-v3") is False
    assert models_match("mistral-large-2407", "mistral-large-2411") is False

    # Empty served model must not match
    assert models_match("gpt-4o", "") is False
    assert models_match("", "gpt-4o") is False
    assert models_match("", "") is False

    # Runner records "not reported" and warns on empty served model
    from pydantic import BaseModel

    from harness.audit.store import AuditStore
    from harness.config import HarnessConfig, Profile
    from harness.models.base import ProviderResult
    from harness.models.fake_provider import FakeProvider
    from harness.models.runner import structured_call

    class Dummy(BaseModel):
        ans: str

    monkeypatch.setattr(
        FakeProvider,
        "generate",
        lambda self, sys, msgs, sch: ProviderResult(
            text='{"ans": "ok"}',
            model_served="",
            stop_reason="end_turn",
            tokens_in=5,
            tokens_out=5,
        ),
    )
    cfg = HarnessConfig(
        db_path=str(tmp_path / "audit.sqlite"),
        roles={"tester": "p"},
        profiles={"p": Profile(name="p", provider="fake", model="test-model")},
    )
    audit = AuditStore(tmp_path / "audit.sqlite")
    res = structured_call(
        cfg=cfg,
        audit=audit,
        run_id="run-1",
        role_or_profile="tester",
        task="test",
        prompt_version="v1",
        system="sys",
        user="usr",
        output_model=Dummy,
        actor="Tom",
    )
    assert res.provider_result.model_served == ""
    # Generated event records model_served as "not reported" and records warning
    gen_events = [e for e in audit.events(run_id="run-1") if e["action"] == "generated"]
    assert len(gen_events) == 1
    assert gen_events[0]["model_served"] == "not reported"
    assert gen_events[0]["detail"]["warning"] == "served model differs from requested model"


def test_batch_l_models_match_date_and_build_suffixes():
    """Batch L finding 1: models_match matches date (-YYYY-MM-DD, -YYYYMMDD), build (-NNN), and :latest suffixes."""
    # Date suffixes match
    assert models_match("gpt-4o", "gpt-4o-2024-08-06") is True
    assert models_match("claude-sonnet-4-5", "claude-sonnet-4-5-20250929") is True
    # Build suffix matches
    assert models_match("gemini-2.5-pro", "gemini-2.5-pro-002") is True
    # :latest tag matches
    assert models_match("llama3", "llama3:latest") is True
    # Reverse order (requested fixed snapshot, served moving alias) must NOT match (Batch M finding 2)
    assert models_match("gpt-4o-2024-08-06", "gpt-4o") is False
    assert models_match("llama3:latest", "llama3") is False

    # But -vN, size, and family variants remain mismatches
    assert models_match("deepseek-v2", "deepseek-v3") is False
    assert models_match("mistral-large-2407", "mistral-large-2411") is False
    assert models_match("gpt-4o", "gpt-4") is False
    assert models_match("gpt-4o", "gpt-4o-mini") is False
    assert models_match("llama3:70b", "llama3:8b") is False


def test_batch_l_offline_allowed_hosts_ip_address():
    """Batch L finding 2: offline_allowed_hosts checks allow-list before IP literal check (admin list overrides)."""
    # Public IP literal explicitly allowed by admin must be accepted in offline mode
    public_ip = "93.184.216.34"
    ok, reason, host, pin = validate_and_pin_offline_host(f"http://{public_ip}:8080/v1", extra_allowed=[public_ip])
    assert ok is True
    assert host == public_ip
    assert reason == f"admin allowed host: {public_ip}"
    assert pin == public_ip

    # Unlisted public IP literal must still be rejected
    unlisted_ip = "93.184.216.35"
    ok, reason, _host, pin = validate_and_pin_offline_host(f"http://{unlisted_ip}:8080/v1", extra_allowed=[public_ip])
    assert ok is False
    assert "public IP address" in reason


def test_batch_m_models_match_never_in_reverse():
    """Batch M finding 2: models_match only allows served model to add a suffix, never drop one."""
    # Moving requested with pinned served matches
    assert models_match("gpt-4o", "gpt-4o-2024-08-06") is True
    # Pinned requested with moving served must NOT match
    assert models_match("gpt-4o-2024-08-06", "gpt-4o") is False
    assert models_match("claude-sonnet-4-5-20250929", "claude-sonnet-4-5") is False
    assert models_match("llama3:latest", "llama3") is False
    assert models_match("gemini-2.5-pro-002", "gemini-2.5-pro") is False


def test_batch_m_offline_allowed_hosts_bracketed_ipv6_and_metadata():
    """Batch M finding 3: offline_allowed_hosts accepts bracketed IPv6 and refuses metadata addresses even when listed."""
    # Bracketed IPv6 allowed
    ipv6 = "2606:4700::1111"
    ok, reason, host, pin = validate_and_pin_offline_host(
        f"http://[{ipv6}]:8080/v1", extra_allowed=[f"[{ipv6}]"]
    )
    assert ok is True
    assert host == ipv6
    assert pin == ipv6
    assert reason == f"admin allowed host: {ipv6}"

    # Cloud metadata addresses forbidden even when listed
    for meta_entry, meta_host in [
        ("169.254.169.254", "http://169.254.169.254/latest/meta-data"),
        ("[fd00:ec2::254]", "http://[fd00:ec2::254]/latest/meta-data"),
    ]:
        ok, reason, _, _ = validate_and_pin_offline_host(meta_host, extra_allowed=[meta_entry])
        assert ok is False
        assert "cloud metadata address" in reason
