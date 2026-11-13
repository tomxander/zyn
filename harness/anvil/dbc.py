"""Read a DBC file into a small, plain description the rest of Anvil uses."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Signal:
    name: str
    message: str
    unit: str
    minimum: float
    maximum: float
    resolution: float
    choices: dict[int, str]
    cluster_receives: bool  # True: an input the test drives; False: sent by the cluster
    range_from_bits: bool = False  # the DBC gave no min/max; the range its bits allow is used

    @property
    def boolean(self) -> bool:
        return self.minimum == 0 and self.maximum == 1 and self.resolution == 1


@dataclass
class Message:
    name: str
    frame_id: int
    cycle_ms: int | None
    cluster_sends: bool
    signals: list[str] = field(default_factory=list)


@dataclass
class CanDb:
    filename: str
    sha256: str
    node: str
    messages: dict[str, Message]
    signals: dict[str, Signal]

    def prompt_block(self) -> str:
        lines = []
        for m in self.messages.values():
            role = "sent by the cluster (outputs)" if m.cluster_sends else "received (inputs)"
            lines.append(f"Message {m.name}, every {m.cycle_ms} ms, {role}:")
            for s in (self.signals[n] for n in m.signals):
                ch = (" values " + ", ".join(f"{k}={v}" for k, v in s.choices.items())
                      if s.choices else "")
                lines.append(f"  {s.name}: {s.unit or '-'}, {s.minimum}..{s.maximum}, "
                             f"step {s.resolution}{ch}")
        return "\n".join(lines)


def raw_range(s) -> tuple[float, float]:
    """The physical range a cantools signal's bits can carry, from its length, sign, scale
    and offset."""
    lo, hi = ((-(2 ** (s.length - 1)), 2 ** (s.length - 1) - 1) if s.is_signed
              else (0, 2 ** s.length - 1))
    a, b = lo * s.scale + s.offset, hi * s.scale + s.offset
    return float(min(a, b)), float(max(a, b))


def load_raw(path: Path | str):
    """The cantools database, read leniently so a faulty file can still be checked
    (harness.anvil.dbc_check) instead of stopping the run. DBC, KCD, SYM and ARXML."""
    import cantools

    return cantools.database.load_file(str(path), strict=False)


def load_dbc(path: Path | str, node: str = "ICX100") -> CanDb:
    path = Path(path)
    db = load_raw(path)
    messages, signals = {}, {}
    for m in db.messages:
        sends = node in (m.senders or [])
        messages[m.name] = Message(m.name, m.frame_id, m.cycle_time, sends,
                                   [s.name for s in m.signals])
        for s in m.signals:
            # A DBC range of [0|0] (cantools: None) means "not given", not "only zero".
            missing = (s.minimum is None and s.maximum is None) or (
                s.minimum == 0 and s.maximum == 0)
            lo, hi = raw_range(s) if missing else (
                float(s.minimum if s.minimum is not None else raw_range(s)[0]),
                float(s.maximum if s.maximum is not None else raw_range(s)[1]))
            signals[s.name] = Signal(
                s.name, m.name, s.unit or "", lo, hi, float(s.scale),
                {int(k): str(v) for k, v in (s.choices or {}).items()},
                cluster_receives=not sends, range_from_bits=missing)
    return CanDb(path.name, hashlib.sha256(path.read_bytes()).hexdigest(), node, messages,
                 signals)
