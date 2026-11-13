"""Deterministic test-case generation from an approved test spec. No model involved.

Each case is a list of steps on the bus:
  {"at_ms", "do": "set", "signal", "value"}        drive an input signal
  {"at_ms", "do": "stop", "message"}                stop sending an input message
  {"at_ms", "do": "expect", "signal", "value", "within_ms" | "for_ms" | neither}
      within_ms: the value must appear at some point in [at, at + within]
      for_ms:    the value must hold for the whole of [at, at + for]
      neither:   the value at exactly that time
  {"at_ms", "do": "expect_absent", "signal", "value", "for_ms"}
      the value must not appear anywhere in [at, at + for]
  {"at_ms", "do": "expect_range", "signal", "low", "high", "after_ms"}
      after_ms later the value must lie in [low, high]; a null bound is open
  {"at_ms", "do": "expect_period", "message", "period_ms", "tolerance_ms", "count"}
Every case names the requirement clause its expected result comes from (the oracle) and why
its stimulus values were chosen. Values the requirement does not give are listed in
open_values with the value the case assumed, so a person can replace them."""

from __future__ import annotations

from harness.anvil.dbc import CanDb

SETTLE_MS = 500


def _assumed_window(db: CanDb, spec: dict) -> int:
    """Time allowed for a reaction when the requirement gives none: two cycles of the
    cluster's status message plus one cycle of the input message. An assumption, flagged."""
    out = db.signals[spec["output_signal"]].message
    oc = db.messages[out].cycle_ms or 100
    inp = spec.get("input_signal")
    ic = db.messages[db.signals[inp].message].cycle_ms or 100 if inp in db.signals else 100
    return int(2 * oc + ic)


def _inactive(db: CanDb, spec: dict) -> float | None:
    sig = db.signals[spec["output_signal"]]
    if sig.boolean and spec["expected_value"] in (0, 1):
        return 1 - spec["expected_value"]
    return None


def _case(spec, req, n, title, kind, steps, expected, why, open_values):
    return {"case_id": f"TC-{req['id']}-{n:02d}", "requirement_id": req["id"],
            "template": spec["template"], "title": title, "kind": kind, "steps": steps,
            "expected": expected, "boundary_rationale": why,
            "oracle": {"requirement_id": req["id"], "quote": req["quote"]},
            "open_values": open_values}


def generate_cases(spec: dict, req: dict, db: CanDb) -> list[dict]:
    """req: {"id", "text", "quote"} for the approved requirement behind the spec."""
    t = spec["template"]
    if t == "not_automatable":
        return [_case(spec, req, 1, "Manual check", "manual", [], spec["manual_test_idea"],
                      "No bus observable; checked by a person.", [])]
    cases: list[dict] = []
    open_values = []
    if t in ("threshold", "event_response"):
        if spec.get("max_latency_ms"):
            window = int(spec["max_latency_ms"])
        else:
            window = _assumed_window(db, spec)
            open_values.append(f"reaction time not stated; cases allow {window} ms "
                               "(two status cycles plus one input cycle)")
    out, exp = spec.get("output_signal"), spec.get("expected_value")
    inactive = _inactive(db, spec) if out else None

    if t == "threshold":
        sig = db.signals[spec["input_signal"]]
        r, th, below = sig.resolution, float(spec["threshold"]), spec["direction"] == "below"
        inside, outside = (th - r, th + r) if below else (th + r, th - r)
        far = min(sig.maximum, th + 10 * r) if below else max(sig.minimum, th - 10 * r)
        extreme = sig.minimum if below else sig.maximum
        side = "below" if below else "above"

        def run(value):
            return [{"at_ms": 0, "do": "set", "signal": sig.name, "value": far},
                    {"at_ms": SETTLE_MS, "do": "set", "signal": sig.name, "value": value}]

        cases.append(_case(spec, req, 1, f"{sig.name} one step {side} {th:g}", "boundary",
                           run(inside) + [{"at_ms": SETTLE_MS, "do": "expect", "signal": out,
                                           "value": exp, "within_ms": window}],
                           f"{out} = {exp:g} within {window} ms",
                           f"Smallest step ({r:g} {sig.unit}) past the threshold.", open_values))
        if inactive is not None:
            cases.append(_case(spec, req, 2, f"{sig.name} exactly {th:g}", "boundary",
                               run(th) + [{"at_ms": SETTLE_MS, "do": "expect", "signal": out,
                                           "value": inactive, "for_ms": window}],
                               f"{out} stays {inactive:g} for {window} ms",
                               f"'{side}' excludes the threshold itself.", open_values))
            cases.append(_case(spec, req, 3, f"{sig.name} one step on the other side",
                               "boundary",
                               run(outside) + [{"at_ms": SETTLE_MS, "do": "expect",
                                                "signal": out, "value": inactive,
                                                "for_ms": window}],
                               f"{out} stays {inactive:g} for {window} ms",
                               f"Smallest step ({r:g} {sig.unit}) before the threshold.",
                               open_values))
        cases.append(_case(spec, req, len(cases) + 1, f"{sig.name} at range limit {extreme:g}",
                           "range", run(extreme) + [{"at_ms": SETTLE_MS, "do": "expect",
                                                     "signal": out, "value": exp,
                                                     "within_ms": window}],
                           f"{out} = {exp:g} within {window} ms",
                           "Signal range limit from the DBC.", open_values))

    elif t == "event_response":
        sig = db.signals[spec["input_signal"]]
        init = spec.get("initial_value")
        init = init if init is not None else (1 - spec["input_value"] if sig.boolean else
                                              sig.minimum)
        start = [{"at_ms": 0, "do": "set", "signal": sig.name, "value": init}]
        steps = start + [{"at_ms": SETTLE_MS, "do": "set", "signal": sig.name,
                          "value": spec["input_value"]},
                         {"at_ms": SETTLE_MS, "do": "expect", "signal": out, "value": exp,
                          "within_ms": window}]
        cases.append(_case(spec, req, 1, f"{sig.name} {init:g} -> {spec['input_value']:g}",
                           "positive", steps, f"{out} = {exp:g} within {window} ms",
                           "The triggering change from the requirement.", open_values))
        hold = spec.get("hold_ms")
        if hold:
            oc = db.messages[db.signals[out].message].cycle_ms or 100
            steps = start + [{"at_ms": SETTLE_MS, "do": "set", "signal": sig.name,
                              "value": spec["input_value"]},
                             {"at_ms": SETTLE_MS + window, "do": "expect", "signal": out,
                              "value": exp, "for_ms": int(hold - window - oc)}]
            if inactive is not None:
                steps.append({"at_ms": SETTLE_MS + int(hold) + window, "do": "expect",
                              "signal": out, "value": inactive, "within_ms": 2 * oc})
            cases.append(_case(spec, req, 2, f"{out} holds for {hold:g} ms", "timing", steps,
                               f"{out} = {exp:g} for {hold:g} ms, then ends",
                               f"Duration from the requirement; checked to one {oc} ms "
                               "status cycle.", open_values))
        if inactive is not None:
            cases.append(_case(spec, req, len(cases) + 1, f"No {sig.name} change", "negative",
                               start + [{"at_ms": SETTLE_MS, "do": "expect", "signal": out,
                                         "value": inactive, "for_ms": window}],
                               f"{out} stays {inactive:g}",
                               "Without the trigger the output must not react.", open_values))
        else:
            # Output is not on/off, so there is no single "not reacted" value: check that the
            # expected value never appears without the trigger.
            cases.append(_case(spec, req, len(cases) + 1, f"No {sig.name} change", "negative",
                               start + [{"at_ms": SETTLE_MS, "do": "expect_absent",
                                         "signal": out, "value": exp, "for_ms": window}],
                               f"{out} never shows {exp:g} for {window} ms",
                               "Without the trigger the output must not react.", open_values))

    elif t == "timeout":
        m = db.messages[spec["message"]]
        c = m.cycle_ms or 100
        oc = db.messages[db.signals[out].message].cycle_ms or 100
        tmo = int(spec["timeout_ms"])
        stop = [{"at_ms": SETTLE_MS, "do": "stop", "message": m.name}]
        if inactive is not None:
            cases.append(_case(spec, req, 1, f"{m.name} silent just under {tmo} ms", "boundary",
                               stop + [{"at_ms": SETTLE_MS, "do": "expect", "signal": out,
                                        "value": inactive, "for_ms": tmo - c}],
                               f"{out} stays {inactive:g} for {tmo - c} ms",
                               f"One {c} ms message cycle short of the timeout.", open_values))
        window = 2 * oc
        ov = open_values + [(f"reaction after the timeout not stated; cases allow {window} ms "
                            "(two status cycles)")]
        cases.append(_case(spec, req, len(cases) + 1, f"{m.name} silent past {tmo} ms",
                           "boundary", stop + [{"at_ms": SETTLE_MS + tmo, "do": "expect",
                                                "signal": out, "value": exp,
                                                "within_ms": window}],
                           f"{out} = {exp:g} within {window} ms after the timeout",
                           "Reaction must follow the stated timeout.", ov))

    elif t == "tracking":
        sig, osig = db.signals[spec["input_signal"]], db.signals[out]
        window = int(spec.get("max_latency_ms") or _assumed_window(db, spec))
        ov = open_values if spec.get("max_latency_ms") else [*open_values, (
            f"update time not stated; cases read the output {window} ms after the change "
            "(two status cycles plus one input cycle)")]
        points = sorted({_on_grid(sig.minimum + f * (sig.maximum - sig.minimum), sig)
                         for f in (0, 0.02, 0.25, 0.5, 0.75, 1.0)})
        mid = _on_grid(sig.minimum + 0.5 * (sig.maximum - sig.minimum), sig)
        for n, x in enumerate(points, start=1):
            lo, hi = track_bounds(spec, x, osig)
            band = (("-" if lo is None else f"{lo:g}") + " .. "
                    + ("-" if hi is None else f"{hi:g}") + f" {osig.unit}")
            first = mid if x != mid else _on_grid(sig.minimum, sig)
            steps = [{"at_ms": 0, "do": "set", "signal": sig.name, "value": first},
                     {"at_ms": SETTLE_MS, "do": "set", "signal": sig.name, "value": x},
                     {"at_ms": SETTLE_MS, "do": "expect_range", "signal": out, "low": lo,
                      "high": hi, "after_ms": window}]
            kind = "range" if x in (sig.minimum, sig.maximum) else "boundary"
            cases.append(_case(spec, req, n, f"{sig.name} = {x:g} {sig.unit}", kind, steps,
                               f"{out} within {band} after {window} ms",
                               "Spread over the DBC range, including the limits and a low "
                               "value where a fixed offset matters most.", ov))

    elif t == "periodic_tx":
        p = int(spec["period_ms"])
        tol = max(1, round(p * 0.1))
        cases.append(_case(spec, req, 1, f"{spec['message']} every {p} ms", "timing",
                           [{"at_ms": SETTLE_MS, "do": "expect_period",
                             "message": spec["message"], "period_ms": p, "tolerance_ms": tol,
                             "count": 50}],
                           f"50 intervals of {p} ms ± {tol} ms",
                           "Period from the requirement.",
                           open_values + [(f"tolerance not stated; cases allow ±{tol} ms "
                                          "(10 percent)")]))
    return cases


def _on_grid(x: float, sig) -> float:
    """Round to the signal's resolution, kept inside its range."""
    v = round(round(x / sig.resolution) * sig.resolution, 6)
    return min(max(v, sig.minimum), sig.maximum)


def track_bounds(spec: dict, x: float, osig) -> tuple[float | None, float | None]:
    """Allowed output band for input x; the upper bound is clipped to the output's range."""
    lo = hi = None
    if spec.get("track_low_factor") is not None:
        lo = round(x * spec["track_low_factor"] + (spec.get("track_low_offset") or 0), 6)
    if spec.get("track_high_factor") is not None:
        hi = round(x * spec["track_high_factor"] + (spec.get("track_high_offset") or 0), 6)
        hi = min(hi, osig.maximum)
    return lo, hi
