"""The simulated cluster reacts only to its spec's own input and message."""

from __future__ import annotations

from pathlib import Path

from harness.anvil.dbc import load_dbc
from harness.anvil.simbench import SimBench

DBC = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "icx100.dbc"

SPEC = {"template": "event_response", "input_signal": "BrakeWarn", "input_value": 1.0,
        "output_signal": "TT_Brake", "expected_value": 1.0, "max_latency_ms": 300}


def test_a_precondition_on_another_signal_is_not_the_input():
    """bench.set('IGN', 1) before the test must not count as BrakeWarn changing."""
    b = SimBench(SPEC, load_dbc(DBC))
    b.set("IGN", 1)
    b.set("BrakeWarn", 0)
    b.wait_ms(500)
    assert b.expect_for("TT_Brake", 0, 300)
    b.set("BrakeWarn", 1)
    assert b.expect_within("TT_Brake", 1, 300)


def test_stopping_another_message_does_not_trigger_a_timeout():
    spec = {"template": "timeout", "message": "Warnings", "timeout_ms": 500,
            "output_signal": "TT_Brake", "expected_value": 1.0}
    b = SimBench(spec, load_dbc(DBC))
    b.stop("Fuel")
    assert b.expect_for("TT_Brake", 0, 1000)
    b.stop("Warnings")
    assert b.expect_within("TT_Brake", 1, 800)
