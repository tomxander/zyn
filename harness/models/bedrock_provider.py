"""AWS Bedrock runtime provider, with schema-constrained output.

Connects to AWS Bedrock (e.g. Anthropic Claude or Converse API) inside the customer's AWS account.
Uses boto3 if installed; imports lazily.
"""

from __future__ import annotations

import json
import os
from typing import Any

from harness.config import Profile
from harness.models.base import ProviderError, ProviderResult
from harness.models.security import scrub_error_text


class BedrockProvider:
    def __init__(self, profile: Profile):
        self.profile = profile
        p = self.profile

        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as e:
            raise ProviderError(
                "AWS Bedrock provider requires 'boto3'. Install it with: pip install 'zyn-harness[bedrock]' or pip install boto3"
            ) from e

        self._boto3 = boto3
        self._ClientError = ClientError
        self._BotoCoreError = BotoCoreError

        region = p.setting("region") or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            raise ProviderError(
                "AWS Bedrock requires an explicit 'region' setting in config or AWS_REGION environment variable (data residency)."
            )
        self.region = region

        aws_profile = p.setting("aws_profile") or os.environ.get("AWS_PROFILE")
        try:
            if aws_profile:
                session = boto3.Session(profile_name=aws_profile, region_name=region)
            else:
                session = boto3.Session(region_name=region)
            self.client = session.client("bedrock-runtime", region_name=region)
        except Exception as e:
            raise ProviderError(f"Failed to create AWS Bedrock client in region {self.region}: {e}") from e

    def generate(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> ProviderResult:
        p = self.profile
        model_id = p.model
        max_tokens = int(p.setting("max_tokens", 4096))
        temperature = float(p.setting("temperature", 0.0))

        is_anthropic = "anthropic" in model_id.lower() or "claude" in model_id.lower()

        if is_anthropic:
            # Bedrock Claude messages API uses tool_choice to force structured JSON schema
            tools = [
                {
                    "name": "return_structured_result",
                    "description": "Output structured result matching schema",
                    "input_schema": schema,
                }
            ]
            body_dict: dict[str, Any] = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
                "temperature": temperature,
                "tools": tools,
                "tool_choice": {"type": "tool", "name": "return_structured_result"},
            }

            try:
                response = self.client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body_dict),
                )
            except self._ClientError as e:
                code = e.response.get("Error", {}).get("Code", "Unknown")
                raw_msg = e.response.get("Error", {}).get("Message", str(e))
                msg = scrub_error_text(raw_msg)
                if code == "AccessDeniedException":
                    raise ProviderError(f"AWS Bedrock access denied for model '{model_id}': {msg}") from e
                if code == "ResourceNotFoundException":
                    raise ProviderError(f"AWS Bedrock model '{model_id}' not found in region {self.region}: {msg}") from e
                if code == "ThrottlingException":
                    raise ProviderError(f"AWS Bedrock rate limit exceeded (throttled): {msg}") from e
                raise ProviderError(f"AWS Bedrock error ({code}): {msg}") from e
            except self._BotoCoreError as e:
                raise ProviderError(f"AWS Bedrock connection error: {scrub_error_text(str(e))}") from e
            except Exception as e:
                raise ProviderError(f"AWS Bedrock invoke_model error: {e}") from e

            try:
                raw_bytes = response["body"].read() if hasattr(response["body"], "read") else response["body"]
                raw_body = json.loads(raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else raw_bytes)
            except Exception as e:
                raise ProviderError(f"Malformed JSON from AWS Bedrock invoke_model: {e}") from e

            stop_reason = raw_body.get("stop_reason")
            if stop_reason == "refusal":
                raise ProviderError("Model refused the request on AWS Bedrock.")
            if stop_reason == "max_tokens":
                raise ProviderError("Output hit max_tokens on AWS Bedrock.")

            content_blocks = raw_body.get("content", [])
            text = ""
            for b in content_blocks:
                if isinstance(b, dict):
                    if b.get("type") == "tool_use" and b.get("name") == "return_structured_result":
                        text = json.dumps(b.get("input", {}))
                        break
                    if b.get("type") == "text":
                        text = b.get("text", "")

            usage = raw_body.get("usage", {})
            return ProviderResult(
                text=text,
                model_served=raw_body.get("model", model_id),
                stop_reason=stop_reason,
                tokens_in=usage.get("input_tokens"),
                tokens_out=usage.get("output_tokens"),
                request_id=response.get("ResponseMetadata", {}).get("RequestId"),
            )
        else:
            # Bedrock Converse API with forced tool configuration
            converse_messages = [
                {"role": m["role"], "content": [{"text": m["content"]}]}
                for m in messages
            ]
            system_prompts = [{"text": system}] if system else []

            tool_config = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": "return_structured_result",
                            "description": "Return structured result matching schema",
                            "inputSchema": {
                                "json": schema,
                            },
                        }
                    }
                ],
                "toolChoice": {
                    "tool": {
                        "name": "return_structured_result",
                    }
                },
            }

            try:
                response = self.client.converse(
                    modelId=model_id,
                    messages=converse_messages,
                    system=system_prompts,
                    toolConfig=tool_config,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    },
                )
            except self._ClientError as e:
                code = e.response.get("Error", {}).get("Code", "Unknown")
                raw_msg = e.response.get("Error", {}).get("Message", str(e))
                msg = scrub_error_text(raw_msg)
                raise ProviderError(f"AWS Bedrock converse error ({code}): {msg}") from e
            except self._BotoCoreError as e:
                raise ProviderError(f"AWS Bedrock connection error: {scrub_error_text(str(e))}") from e
            except Exception as e:
                raise ProviderError(f"AWS Bedrock converse error: {e}") from e

            stop_reason = response.get("stopReason")
            if stop_reason == "max_tokens":
                raise ProviderError("Output hit maxTokens on AWS Bedrock.")
            if stop_reason in ("guardrail_intervened", "content_filtered"):
                raise ProviderError(f"AWS Bedrock content filtered (stopReason: {stop_reason}).")

            output = response.get("output", {}).get("message", {})
            content = output.get("content", [])
            text = ""
            for c in content:
                if isinstance(c, dict):
                    if "toolUse" in c and c["toolUse"].get("name") == "return_structured_result":
                        text = json.dumps(c["toolUse"].get("input", {}))
                        break
                    if "text" in c:
                        text = c["text"]

            usage = response.get("usage", {})
            return ProviderResult(
                text=text,
                model_served=response.get("metrics", {}).get("modelId", model_id),
                stop_reason=stop_reason,
                tokens_in=usage.get("inputTokens"),
                tokens_out=usage.get("outputTokens"),
                request_id=response.get("ResponseMetadata", {}).get("RequestId"),
            )
