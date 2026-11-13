"""Code checks on a proposed test spec, before a person sees it.

A spec is "ready" only when its template has every parameter it needs, every signal and
message exists in the DBC with the right direction, every value is inside the signal's
range, and every number can be traced to the requirement text (or is an on/off or state
value from the DBC). Anything the requirement does not give stays listed as missing."""

from __future__ import annotations

import re

from harness.anvil.dbc import CanDb
from harness.sift import checks

NEEDS = {
    "threshold": ["input_signal", "threshold", "direction", "output_signal", "expected_value"],
    "event_response": ["input_signal", "input_value", "output_signal", "expected_value"],
    "timeout": ["message", "timeout_ms", "output_signal", "expected_value"],
    "periodic_tx": ["message", "period_ms"],
    "tracking": ["input_signal", "output_signal"],
    "not_automatable": [],
}
SOURCED = ["threshold", "input_value", "max_latency_ms", "hold_ms", "timeout_ms", "period_ms"]
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> set[float]:
    out = set()
    for n in _NUM.findall(text):
        try:
            out.add(float(n.replace(",", ".")))
        except ValueError:
            pass
    return out


def grounded_number(value: float, text: str, ms: bool) -> bool:
    """The value, or for times the value in seconds, appears in the requirement text."""
    nums = _numbers(text)
    if value in nums:
        return True
    return ms and round(value / 1000, 6) in nums


def validate(spec: dict, requirement_text: str, db: CanDb) -> list[str]:
    problems = []
    t = spec["template"]
    for p in NEEDS[t]:
        if spec.get(p) in (None, ""):
            problems.append(f"{t} needs {p}")
    if t == "not_automatable":
        if not spec.get("manual_test_idea"):
            problems.append("not_automatable needs a manual test idea")
        return problems
    for name in ("input_signal", "output_signal"):
        s = spec.get(name)
        if not s:
            continue
        if s not in db.signals:
            problems.append(f"{name} '{s}' is not in {db.filename}")
            continue
        sig = db.signals[s]
        if name == "input_signal" and not sig.cluster_receives:
            problems.append(f"{s} is sent by the cluster; it cannot be the input")
        if name == "output_signal" and sig.cluster_receives:
            problems.append(f"{s} is an input to the cluster; it cannot show the result")
    msg = spec.get("message")
    if msg:
        if msg not in db.messages:
            problems.append(f"message '{msg}' is not in {db.filename}")
        elif t == "periodic_tx" and not db.messages[msg].cluster_sends:
            problems.append(f"{msg} is not sent by the cluster")
        elif t == "timeout" and db.messages[msg].cluster_sends:
            problems.append(f"{msg} is sent by the cluster; the test cannot stop it")
    for key, sig_name in (("threshold", "input_signal"), ("input_value", "input_signal"),
                          ("initial_value", "input_signal"),
                          ("expected_value", "output_signal")):
        v, s = spec.get(key), spec.get(sig_name)
        if v is None or s not in db.signals:
            continue
        sig = db.signals[s]
        if not sig.minimum <= v <= sig.maximum:
            problems.append(f"{key} {v} is outside {s}'s range {sig.minimum}..{sig.maximum}")
    for key in SOURCED:
        v = spec.get(key)
        if v is None:
            continue
        sig = db.signals.get(spec.get("input_signal") or "")
        if key == "input_value" and sig and (sig.boolean or int(v) in sig.choices):
            continue
        if not grounded_number(float(v), requirement_text, key.endswith("_ms")):
            problems.append(f"{key} {v:g} does not appear in the requirement text")
    if t == "tracking":
        problems += _tracking_problems(spec, requirement_text)
    for src in spec.get("value_sources", []):
        if not checks.is_grounded(src["quote"], requirement_text):
            problems.append(f"source quote for {src['param']} is not in the requirement: "
                            f"\"{src['quote']}\"")
    return problems


def _tracking_problems(spec: dict, text: str) -> list[str]:
    out = []
    lo = (spec.get("track_low_factor"), spec.get("track_low_offset"))
    hi = (spec.get("track_high_factor"), spec.get("track_high_offset"))
    if lo[0] is None and hi[0] is None:
        out.append("tracking needs a lower or an upper bound")
    nums = _numbers(text)
    for name, (f, o) in (("lower", lo), ("upper", hi)):
        if f is None:
            if o not in (None, 0):
                out.append(f"{name} bound has an offset but no factor")
            continue
        pct = round((f - 1) * 100, 6)
        if not (f == 1 or f in nums or abs(pct) in nums):
            out.append(f"{name} factor {f:g} does not appear in the requirement text "
                       f"(as {f:g} or {abs(pct):g} percent)")
        if o not in (None, 0) and abs(o) not in nums:
            out.append(f"{name} offset {o:g} does not appear in the requirement text")
    if lo[0] is not None and hi[0] is not None:
        for x in (0, 100):
            if lo[0] * x + (lo[1] or 0) > hi[0] * x + (hi[1] or 0):
                out.append("lower bound is above the upper bound")
                break
    return out
