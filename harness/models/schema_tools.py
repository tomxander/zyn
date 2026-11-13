"""Turns a Pydantic model into a strict JSON schema that both Claude and Ollama accept.

Constrained decoding engines support a subset of JSON Schema. This module:
- inlines $ref/$defs (no recursive models allowed),
- marks every object closed (additionalProperties: false) with all keys required,
- drops keywords that decoders may reject (numeric bounds, lengths, titles, defaults).

Dropped constraints are not lost: every response is re-validated by the full
Pydantic model afterwards, so a value that breaks a bound still fails.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

_DROP_KEYS = {
    "title",
    "default",
    "examples",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "pattern",
    "format",
    "uniqueItems",
}


def _inline(node: Any, defs: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"].split("/")[-1]
            if ref in stack:
                raise ValueError(f"Recursive schema reference '{ref}' is not supported")
            merged = {**copy.deepcopy(defs[ref]), **{k: v for k, v in node.items() if k != "$ref"}}
            return _inline(merged, defs, stack + (ref,))
        return {k: _inline(v, defs, stack) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline(v, defs, stack) for v in node]
    return node


def _close(node: Any) -> Any:
    if isinstance(node, dict):
        node = {k: _close(v) for k, v in node.items() if k not in _DROP_KEYS}
        if node.get("type") == "object" or "properties" in node:
            node["type"] = "object"
            props = node.setdefault("properties", {})
            node["required"] = list(props.keys())
            node["additionalProperties"] = False
        return node
    if isinstance(node, list):
        return [_close(v) for v in node]
    return node


def to_strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    raw = model.model_json_schema()
    defs = raw.get("$defs", {})
    return _close(_inline(raw, defs))
