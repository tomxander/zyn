"""Anvil schemas: the model proposes a test template and its parameters for a requirement.
Code validates the proposal and generates the test cases; the model never writes cases."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Template(str, Enum):
    threshold = "threshold"            # input signal crosses a value -> output signal value
    event_response = "event_response"  # input signal set to a value -> output value (within, for)
    timeout = "timeout"                # input message stops -> output value after a time
    periodic_tx = "periodic_tx"        # the cluster sends a message at a fixed period
    tracking = "tracking"              # output follows input within a tolerance band
    not_automatable = "not_automatable"  # no bus observable; a manual test idea instead


class Direction(str, Enum):
    below = "below"
    above = "above"


class BoundSide(str, Enum):
    lower = "lower"
    upper = "upper"


class TrackBound(BaseModel):
    """One side of a tracking band: bound = input x factor + offset. Kept as a list item with
    required fields because the API limits how many optional fields a schema may have."""
    side: BoundSide
    factor: float = Field(description="1 for 'not lower/higher than the input'; 1.1 for "
                                      "'10 percent above'")
    offset: float = Field(description="Fixed offset in the output's unit, 0 if none")


class ValueSource(BaseModel):
    param: str = Field(description="Parameter name, e.g. threshold, max_latency_ms")
    quote: str = Field(description="The exact words from the requirement text that give this "
                                   "value, copied character for character")


class TestSpec(BaseModel):
    __test__ = False  # not a pytest test class
    req_id: str = Field(description="Requirement ID exactly as given")
    template: Template
    input_signal: str | None = Field(description="DBC signal the test drives, else null")
    initial_value: float | None = Field(description="Input value before the event, else null")
    input_value: float | None = Field(description="Input value that triggers the behaviour "
                                                  "(event_response), else null")
    threshold: float | None = Field(description="Threshold in the signal's unit (threshold "
                                                "template), else null")
    direction: Direction | None = Field(description="below or above the threshold, else null")
    output_signal: str | None = Field(description="ClusterStatus signal that shows the result")
    expected_value: float | None = Field(description="Value the output signal must take")
    max_latency_ms: float | None = Field(description="Time limit for the reaction, only if the "
                                                     "requirement states one, else null")
    hold_ms: float | None = Field(description="How long the expected value must hold, only if "
                                              "stated, else null")
    message: str | None = Field(description="DBC message for timeout or periodic_tx, else null")
    timeout_ms: float | None = Field(description="Silence time before the reaction (timeout)")
    period_ms: float | None = Field(description="Transmission period (periodic_tx)")
    track_bounds: list[TrackBound] = Field(
        description="tracking only: the lower and/or upper bound of the band; empty otherwise")
    value_sources: list[ValueSource] = Field(
        description="For every number taken from the requirement, the words that give it")
    assumptions: list[str] = Field(
        description="Choices not stated in the requirement, e.g. which DBC signal stands for "
                    "a named telltale")
    missing: list[str] = Field(
        description="Values a test needs that the requirement does not give (e.g. a time "
                    "limit or tolerance). Never invent them.")
    manual_test_idea: str | None = Field(description="For not_automatable only: a short "
                                                     "manual test idea, else null")
    rationale: str = Field(description="One sentence: why this template")


class SpecBatch(BaseModel):
    specs: list[TestSpec]


def flatten(spec: dict) -> dict:
    """Spreads track_bounds into the flat fields the rest of Anvil reads."""
    out = {**spec, "track_low_factor": None, "track_low_offset": None,
           "track_high_factor": None, "track_high_offset": None}
    for b in spec.get("track_bounds") or []:
        side = "low" if b["side"] == "lower" else "high"
        out[f"track_{side}_factor"], out[f"track_{side}_offset"] = b["factor"], b["offset"]
    return out
