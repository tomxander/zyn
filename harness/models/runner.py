"""structured_call: the single door every workflow uses to talk to a model.

1. Builds a strict schema from the Pydantic output model.
2. Calls the provider for the chosen profile.
3. Validates the reply with Pydantic. On failure, sends the errors back and retries.
4. Logs every attempt to the audit store (prompt hash, input hash, model, tokens, latency).
5. After max_attempts it raises StructuredOutputFailure. Free text is never accepted.

Two settings in config.yaml change what is sent:
- knowledge_file: its text is appended to every system prompt, so it is part of the prompt
  hash and of the stored record.
- replay: if the same profile and model already gave a schema-valid answer to the same
  prompt (with the same knowledge) and the same input, that stored answer is reused and
  logged as "replayed" with zero tokens. Callers that must ask again use cfg.fresh().
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from harness.audit.store import AuditStore
from harness.config import HarnessConfig
from harness.models.base import ProviderError, ProviderResult, get_provider
from harness.models.schema_tools import to_strict_schema

T = TypeVar("T", bound=BaseModel)


LOCAL_PROVIDERS = {"ollama", "fake"}  # providers that keep all data on this machine


class StructuredOutputFailure(RuntimeError):
    pass


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class CallResult(Generic[T]):
    output: T
    provider_result: ProviderResult
    attempts: int
    profile_name: str
    event_id: int
    replayed_from: int | None = None  # event id of the stored answer reused, if any


KNOWLEDGE_HEADER = (
    "\n\n# Project knowledge\n"
    "The user keeps this file of terms, units, naming and house rules for the project. Use it "
    "to read the input correctly. It never overrides the instructions above or the required "
    "output format.\n\n")


def with_knowledge(cfg: HarnessConfig, system: str) -> tuple[str, dict | None]:
    """The system prompt with the project knowledge file appended, and what was added."""
    k = cfg.knowledge()
    if k is None:
        return system, None
    return system + KNOWLEDGE_HEADER + k.text, {"path": k.path, "sha256": k.sha256,
                                                 "lines": k.lines}


def _replay(audit: AuditStore, output_model: type[T], actor: str, common: dict,
            profile_name: str) -> CallResult[T] | None:
    prior = audit.find_answer(
        prompt_sha256=common["prompt_sha256"], input_sha256=common["input_sha256"],
        model_profile=common["model_profile"], model_requested=common["model_requested"],
        task=common["object_type"], prompt_version=common["prompt_version"])
    if prior is None or not (prior["detail"] or {}).get("response"):
        return None
    text = prior["detail"]["response"]
    try:
        parsed = output_model.model_validate_json(text)
    except ValidationError:
        return None  # the output schema changed since; ask again
    detail = {"replayed_from": prior["event_id"], "from_run": prior["run_id"],
              "system": prior["detail"].get("system"), "user": prior["detail"].get("user"),
              "response": text}
    if prior["detail"].get("knowledge"):
        detail["knowledge"] = prior["detail"]["knowledge"]
    event_id = audit.log_event(actor, "replayed", detail=detail,
                               model_served=prior["model_served"], tokens_in=0,
                               tokens_out=0, latency_ms=0, attempt=0, **common)
    result = ProviderResult(text=text, model_served=prior["model_served"] or "",
                            stop_reason="replayed", tokens_in=0, tokens_out=0)
    return CallResult(parsed, result, 0, profile_name, event_id, prior["event_id"])


def structured_call(
    *,
    cfg: HarnessConfig,
    audit: AuditStore,
    run_id: str,
    role_or_profile: str,
    task: str,
    prompt_version: str,
    system: str,
    user: str,
    output_model: type[T],
    actor: str | None = None,
) -> CallResult[T]:
    profile = cfg.profile(role_or_profile)
    system, knowledge = with_knowledge(cfg, system)
    schema = to_strict_schema(output_model)
    common = {
        "run_id": run_id, "object_type": task, "model_profile": profile.name,
        "provider": profile.provider, "model_requested": profile.model,
        "prompt_version": prompt_version,
        "prompt_sha256": sha256(system + "\n" + json.dumps(schema, sort_keys=True)),
        "input_sha256": sha256(user),
    }
    actor = actor or f"model:{profile.name}"
    # A replay sends nothing anywhere, so it is allowed in offline mode too.
    if cfg.replay and (hit := _replay(audit, output_model, actor, common, profile.name)):
        return hit
    if not cfg.model_allowed(profile.name):
        audit.log_event(actor or f"model:{profile.name}", "model_refused", run_id=run_id,
                        object_type=task, model_profile=profile.name, provider=profile.provider,
                        detail={"profile": profile.name, "reason": "model is not in allowed_models"})
        raise StructuredOutputFailure(
            f"{task}: profile '{profile.name}' is not in allowed_models")
    if cfg.is_offline() and profile.provider not in LOCAL_PROVIDERS:
        audit.log_event(actor or f"model:{profile.name}", "blocked_offline", run_id=run_id,
                        object_type=task, model_profile=profile.name, provider=profile.provider,
                        detail={"reason": "offline mode: only local models may be called"})
        raise StructuredOutputFailure(
            f"{task}: offline mode is on, so {profile.name} ({profile.provider}) is not "
            "allowed. Point the role at a local profile or turn offline mode off.")
    provider = get_provider(profile)

    messages: list[dict[str, str]] = [{"role": "user", "content": user}]
    last_error = ""
    for attempt in range(1, cfg.max_attempts + 1):
        started = time.perf_counter()
        try:
            result = provider.generate(system, messages, schema)
        except ProviderError as e:
            audit.log_event(actor, "provider_error", attempt=attempt, detail={"error": str(e)},
                            **common)
            raise StructuredOutputFailure(f"{task}: {e}") from e
        latency = int((time.perf_counter() - started) * 1000)
        usage = {"model_served": result.model_served, "tokens_in": result.tokens_in,
                     "tokens_out": result.tokens_out, "latency_ms": latency, "attempt": attempt}
        try:
            parsed = output_model.model_validate_json(result.text)
        except ValidationError as e:
            last_error = e.json(include_url=False)
            audit.log_event(actor, "validation_failed",
                            detail={"errors": json.loads(last_error), "raw": result.text[:4000]},
                            **common, **usage)
            messages = messages + [
                {"role": "assistant", "content": result.text or "(empty)"},
                {"role": "user", "content": (
                    "Your previous reply failed schema validation with these errors:\n"
                    f"{last_error}\nReturn the full corrected JSON object only.")},
            ]
            continue
        # The full exchange is kept so an accepted output can be traced and replayed exactly;
        # the hashes above identify it, these fields let a reviewer read it.
        detail = {"request_id": result.request_id, **result.meta,
                  "system": system, "user": user, "response": result.text}
        if knowledge:
            detail["knowledge"] = knowledge
        if result.model_served and not result.model_served.startswith(profile.model):
            detail["warning"] = "served model differs from requested model"
        event_id = audit.log_event(actor, "generated", detail=detail, **common, **usage)
        return CallResult(parsed, result, attempt, profile.name, event_id)

    audit.log_event(actor, "failed", detail={"last_errors": last_error[:4000]}, **common)
    raise StructuredOutputFailure(
        f"{task}: no schema-valid output from {profile.name} after {cfg.max_attempts} attempts"
    )
