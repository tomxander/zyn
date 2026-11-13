"""Requirement formalisation: each Anvil spec as a formal statement, checked as a set.

An approved spec already pins a requirement to signals, values and times. Written out in an
EARS-like form ("When FuelLevel < 10, TT_LowFuel shall be 1 within 300 ms") it can be read
by a person and compared with the others by code:

- conflict:   two specs drive the same output signal to different values for overlapping
              input conditions (thresholds on the same input that overlap, or the same
              trigger with different responses)
- timeout:    two specs give different timeouts for the loss of the same message
- band:       a tracking spec whose lower bound can exceed its upper bound
- uncovered:  output signals the cluster sends that no spec checks (listed, not a defect)

Code only. It finds contradictions between the specs as written; it cannot tell which of two
conflicting requirements is right.
"""

from __future__ import annotations

from itertools import combinations

from harness.anvil.dbc import CanDb


def _n(v) -> str:
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def statement(p: dict) -> str | None:
    t = p.get("template")
    lat = f" within {_n(p['max_latency_ms'])} ms" if p.get("max_latency_ms") else ""
    if t == "threshold":
        op = "<" if p["direction"] == "below" else ">"
        return (f"When {p['input_signal']} {op} {_n(p['threshold'])}, {p['output_signal']} "
                f"shall be {_n(p['expected_value'])}{lat}.")
    if t == "event_response":
        hold = f" for {_n(p['hold_ms'])} ms" if p.get("hold_ms") else ""
        return (f"When {p['input_signal']} changes from {_n(p.get('initial_value'))} to "
                f"{_n(p['input_value'])}, {p['output_signal']} shall be "
                f"{_n(p['expected_value'])}{lat}{hold}.")
    if t == "timeout":
        return (f"If {p['message']} is not received for more than {_n(p['timeout_ms'])} ms, "
                f"{p['output_signal']} shall be {_n(p['expected_value'])}.")
    if t == "periodic_tx":
        return f"The cluster shall send {p['message']} every {_n(p['period_ms'])} ms."
    if t == "tracking":
        lo = (f"{_n(p['track_low_factor'])} x {p['input_signal']} + "
              f"{_n(p.get('track_low_offset') or 0)}"
              if p.get("track_low_factor") is not None else None)
        hi = (f"{_n(p['track_high_factor'])} x {p['input_signal']} + "
              f"{_n(p.get('track_high_offset') or 0)}"
              if p.get("track_high_factor") is not None else None)
        band = (f"between {lo} and {hi}" if lo and hi else f"at least {lo}" if lo
                else f"at most {hi}")
        return f"{p['output_signal']} shall be {band}{lat}."
    return None


def _interval(p: dict) -> tuple[float, float, bool, bool]:
    """Input range where a threshold spec is active: (low, high, low_open, high_open)."""
    th = float(p["threshold"])
    return ((float("-inf"), th, True, True) if p["direction"] == "below"
            else (th, float("inf"), True, True))


def _sequential(a: dict, b: dict) -> bool:
    """One response is held for H ms and the other is only expected after at least H ms:
    a sequence (goodbye screen, then sleep), not a conflict."""
    for x, y in ((a, b), (b, a)):
        if x.get("hold_ms") and y.get("max_latency_ms") and float(
                y["max_latency_ms"]) >= float(x["hold_ms"]) + float(x.get("max_latency_ms") or 0):
            return True
    return False


def _overlap(a: tuple, b: tuple) -> bool:
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return lo < hi


def check_set(specs: list[dict], db: CanDb | None = None) -> dict:
    """specs: approved spec payloads (with req_id). Returns statements and issues."""
    stmts = {p["req_id"]: statement(p) for p in specs if statement(p)}
    issues = []
    auto = [p for p in specs if p.get("template") not in (None, "not_automatable")]
    for a, b in combinations(auto, 2):
        ids = sorted([a["req_id"], b["req_id"]])
        if (a["template"] == b["template"] == "threshold"
                and a["input_signal"] == b["input_signal"]
                and a["output_signal"] == b["output_signal"]
                and a["expected_value"] != b["expected_value"]
                and _overlap(_interval(a), _interval(b))):
            issues.append({"kind": "conflict", "requirements": ids,
                           "explanation": f"Both set {a['output_signal']} from "
                           f"{a['input_signal']} with overlapping conditions but to different "
                           f"values ({_n(a['expected_value'])} vs {_n(b['expected_value'])})."})
        if (a["template"] == b["template"] == "event_response"
                and a["input_signal"] == b["input_signal"]
                and a.get("input_value") == b.get("input_value")
                and a["output_signal"] == b["output_signal"]
                and a["expected_value"] != b["expected_value"]
                and not _sequential(a, b)):
            held = next((x for x in (a, b) if x.get("hold_ms")), None)
            other = b if held is a else a
            why = (f"The same trigger ({a['input_signal']} = {_n(a['input_value'])}) sets "
                   f"{a['output_signal']} to {_n(a['expected_value'])} in one and "
                   f"{_n(b['expected_value'])} in the other.")
            if held is not None:
                why += (f" {held['req_id']} holds {_n(held['expected_value'])} for "
                        f"{_n(held['hold_ms'])} ms; {other['req_id']} gives no delay of at "
                        "least that long, so either its spec lost an 'after' or the "
                        "requirements conflict.")
            issues.append({"kind": "conflict", "requirements": ids, "explanation": why})
        if (a["template"] == b["template"] == "timeout" and a["message"] == b["message"]
                and float(a["timeout_ms"]) != float(b["timeout_ms"])):
            issues.append({"kind": "timeout", "requirements": ids,
                           "explanation": f"Loss of {a['message']} is detected after "
                           f"{_n(a['timeout_ms'])} ms in one and {_n(b['timeout_ms'])} ms in "
                           "the other."})
    for p in auto:
        if (p["template"] == "tracking" and p.get("track_low_factor") is not None
                and p.get("track_high_factor") is not None):
            lo_f, hi_f = p["track_low_factor"], p["track_high_factor"]
            lo_o, hi_o = p.get("track_low_offset") or 0, p.get("track_high_offset") or 0
            if lo_f > hi_f or (lo_f == hi_f and lo_o > hi_o):
                issues.append({"kind": "band", "requirements": [p["req_id"]],
                               "explanation": "The lower bound can exceed the upper bound."})
    uncovered = []
    if db is not None:
        checked = {p.get("output_signal") for p in auto} | {
            s for p in auto if p["template"] == "periodic_tx"
            for s in db.messages.get(p["message"], type("M", (), {"signals": []})).signals}
        uncovered = sorted(n for n, s in db.signals.items()
                           if not s.cluster_receives and n not in checked)
    return {"statements": stmts, "issues": issues, "uncovered_outputs": uncovered}


def run_check(audit, run_id: str) -> dict:
    from harness.anvil.pipeline import _dbc

    specs = [s["payload"] for s in audit.approved_items(run_id, "test_spec")]
    return check_set(specs, _dbc(audit, run_id))
