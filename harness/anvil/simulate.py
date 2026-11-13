"""Fault injection: can the generated cases tell a correct cluster from a faulty one?

From an approved spec, code builds a tiny simulated cluster that behaves as the spec says,
plus a few faulty variants (threshold off by one step, a late or missing reaction, a timeout
too short or too long, a wrong period). Every case must pass on the correct simulation; a
faulty variant counts as detected when at least one case fails on it.

This checks the tests, not the product. It shows each case can catch the faults its
template is meant to catch; it says nothing about the real cluster."""

from __future__ import annotations

import itertools

from harness.anvil.dbc import CanDb
from harness.anvil.generate import SETTLE_MS, track_bounds

TICK = 10


def _end(cases: list[dict]) -> int:
    end = 0
    for c in cases:
        for s in c["steps"]:
            span = s.get("within_ms") or s.get("for_ms") or s.get("after_ms") or 0
            if s["do"] == "expect_period":
                span = s["period_ms"] * (s["count"] + 2)
            end = max(end, s["at_ms"] + span)
    return end + 500


def _other(value, sig) -> float:
    """A value the output should not take: the opposite for on/off, else one step away."""
    if sig.boolean and value in (0, 1):
        return 1 - value
    step = sig.resolution or 1
    return value + step if value + step <= sig.maximum else value - step


class Sim:
    """Discrete-time cluster: inputs set by the case, one output signal driven by the
    spec's behaviour, or a message's transmission times."""

    def __init__(self, spec: dict, db: CanDb, fault: str | None):
        self.spec, self.db, self.fault = spec, db, fault

    def run(self, steps: list[dict], end: int) -> dict:
        sp, db, fault = self.spec, self.db, self.fault
        t = sp["template"]
        inp = sp.get("input_signal")
        sig = db.signals.get(inp) if inp else None
        r = sig.resolution if sig else 0
        out = sp.get("output_signal")
        exp = sp.get("expected_value")
        inactive = (1 - exp) if out and db.signals[out].boolean and exp in (0, 1) else None
        lat = 50
        if fault == "late":
            lat = int(sp.get("max_latency_ms") or 300) + 200
        # Only the spec's own input and message drive the output. A step on another signal
        # (a precondition such as IGN = 1) must not count as the input changing.
        sets = sorted((s["at_ms"], s["value"]) for s in steps if s["do"] == "set"
                      and s.get("signal") in (None, inp))
        stop = min([s["at_ms"] for s in steps if s["do"] == "stop"
                    and s.get("message") in (None, sp.get("message"))], default=None)
        value_at = {}
        x, events = None, []
        for tm in range(0, end + TICK, TICK):
            while sets and sets[0][0] <= tm:
                new = sets.pop(0)[1]
                if x is not None and new != x:
                    events.append(tm)
                x = new
            value_at[tm] = x
        timeline = {}
        for tm in range(0, end + TICK, TICK):
            v = inactive
            if t == "threshold":
                xin = value_at.get(max(0, tm - lat))
                th = float(sp["threshold"])
                if fault == "shift_up":
                    th += r
                if fault == "shift_down":
                    th -= r
                below = sp["direction"] == "below"
                if xin is not None:
                    if fault == "inclusive":
                        hit = xin <= th if below else xin >= th
                    else:
                        hit = xin < th if below else xin > th
                    if fault == "inverted":
                        hit = not hit
                    v = exp if hit else inactive
                if fault == "stuck_active":
                    v = exp
                if fault == "stuck_inactive":
                    v = inactive
            elif t == "event_response":
                hold = sp.get("hold_ms")
                if fault == "hold_short" and hold:
                    hold = hold - 300
                for e in events:
                    if (value_at.get(e) == sp["input_value"] and tm >= e + lat
                            and fault != "no_response" and (not hold or tm < e + lat + hold)):
                        v = exp
                if fault == "always":
                    v = exp
                if fault == "wrong_value" and v == exp:
                    v = _other(exp, db.signals[out])
            elif t == "tracking":
                osig = db.signals[out]
                lag = int(sp.get("max_latency_ms") or 300) + 200 if fault == "late" else lat
                xin = value_at.get(0) if fault == "frozen" else value_at.get(max(0, tm - lag))
                if xin is not None:
                    lo, hi = track_bounds(sp, xin, osig)
                    if fault == "stuck_min":
                        v = osig.minimum
                    elif fault == "under_read" and lo is not None:
                        v = lo - osig.resolution
                    elif fault == "over_read" and hi is not None:
                        v = hi + osig.resolution
                    else:
                        v = hi if hi is not None else lo
            elif t == "timeout":
                tmo = sp["timeout_ms"]
                c = db.messages[sp["message"]].cycle_ms or 100
                impl = {"early": tmo - 2 * c, "late": tmo + 600, "never": 10**9}.get(fault,
                                                                                   tmo + 20)
                if stop is not None and tm - stop > impl:
                    v = exp
                if fault == "always":
                    v = exp
            timeline[tm] = v
        tx = []
        if t == "periodic_tx":
            p = sp["period_ms"] * {"slow": 1.2, "fast": 0.8}.get(fault, 1.0)
            k = 0
            while k * p <= end:
                if fault == "stops" and k >= 3:
                    break
                tx.append(k * p)
                k += 1
        return {"out": timeline, "tx": tx}


def check_case(case: dict, result: dict) -> bool:
    out, tx = result["out"], result["tx"]

    def at(tm):
        return out.get(int(tm // TICK * TICK))

    for s in case["steps"]:
        if s["do"] == "expect":
            span = s.get("within_ms") or s.get("for_ms") or s.get("after_ms") or 0
            vals = [at(tm) for tm in range(s["at_ms"], s["at_ms"] + int(span) + TICK, TICK)]
            if s.get("within_ms") is not None:
                if s["value"] not in vals:
                    return False
            elif s.get("for_ms") is not None:
                if any(v != s["value"] for v in vals):
                    return False
            elif at(s["at_ms"]) != s["value"]:
                return False
        elif s["do"] == "expect_range":
            v = at(s["at_ms"] + s["after_ms"])
            if v is None or (s["low"] is not None and v < s["low"] - 1e-9) or (
                    s["high"] is not None and v > s["high"] + 1e-9):
                return False
        elif s["do"] == "expect_absent":
            vals = [at(tm) for tm in range(s["at_ms"], s["at_ms"] + int(s["for_ms"]) + TICK,
                                           TICK)]
            if s["value"] in vals:
                return False
        elif s["do"] == "expect_period":
            times = [x for x in tx if x >= s["at_ms"]][: s["count"] + 1]
            gaps = [b - a for a, b in itertools.pairwise(times)]
            if len(gaps) < s["count"] or any(abs(g - s["period_ms"]) > s["tolerance_ms"]
                                              for g in gaps):
                return False
    return True


FAULTS = {
    "threshold": {"shift_up": "threshold one step higher",
                  "shift_down": "threshold one step lower",
                  "inclusive": "threshold value itself included",
                  "late": "reaction later than allowed",
                  "inverted": "reacts on the wrong side of the threshold",
                  "stuck_active": "output stuck in the active state",
                  "stuck_inactive": "output never becomes active"},
    "event_response": {"no_response": "no reaction", "late": "reaction later than allowed",
                       "hold_short": "output ends too early", "always": "reacts without the trigger",
                       "wrong_value": "reacts with the wrong output value"},
    "timeout": {"early": "reacts before the timeout", "late": "reacts too late",
                "never": "never reacts", "always": "reacts while messages still arrive"},
    "periodic_tx": {"slow": "period 20 percent too long", "fast": "period 20 percent too short",
                    "stops": "transmission stops after three frames"},
    "tracking": {"under_read": "output one step below the lower bound",
                 "over_read": "output one step above the upper bound",
                 "frozen": "output does not follow the input",
                 "late": "output updates later than allowed",
                 "stuck_min": "output stuck at its minimum"},
}


def fault_check(spec: dict, cases: list[dict], db: CanDb) -> dict:
    """Returns which faults the cases detect, and whether all cases pass on the correct
    simulation (if not, the generator or the spec is wrong)."""
    auto = [c for c in cases if c["kind"] != "manual"]
    faults = dict(FAULTS.get(spec["template"], {}))
    if spec["template"] == "event_response" and not spec.get("hold_ms"):
        faults.pop("hold_short", None)
    if spec["template"] == "tracking":
        if spec.get("track_low_factor") is None:
            faults.pop("under_read", None)
        if spec.get("track_high_factor") is None:
            faults.pop("over_read", None)
    if not auto or not faults:
        return {"reference_passes": None, "faults": {}, "detected": 0, "total": 0}
    end = _end(auto) + SETTLE_MS
    ref = all(check_case(c, Sim(spec, db, None).run(c["steps"], end)) for c in auto)
    detected = {}
    for f, label in faults.items():
        killers = [c["case_id"] for c in auto
                   if not check_case(c, Sim(spec, db, f).run(c["steps"], end))]
        detected[f] = {"fault": label, "detected_by": killers}
    return {"reference_passes": ref, "faults": detected,
            "detected": sum(1 for d in detected.values() if d["detected_by"]),
            "total": len(detected)}
