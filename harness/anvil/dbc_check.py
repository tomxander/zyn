"""Code checks on the CAN database itself, before Anvil Review trusts it as the reference.

Every Anvil Review finding about a range or a signal name rests on the DBC, so a faulty DBC
makes those findings wrong. These checks read the file leniently (a strict reader stops at
the first fault) and report:

- duplicate_frame_id: two messages share a frame ID
- signal_overlap:     signals in one message use the same bits (multiplexed signals that
                      never appear together are allowed); one finding per message
- outside_frame:      a signal's bits reach past the message length (DLC)
- range_unreachable:  the DBC min or max cannot be carried by the signal's bits at its
                      scale and offset
- range_inverted:     min is greater than max
- range_missing:      no min/max given ([0|0]); Zyn uses the range the bits allow; one
                      finding per file
- unknown_node:       a sender or receiver that is not in the database's node list
                      (only when the file lists nodes); one finding per node
- invalid_length:     a message length that is not a CAN (0 to 8) or CAN FD length
- bad_encoding:       a byte order other than @0 / @1 or a sign other than + / - (DBC text
                      only; the parser silently reads these as little-endian)
- mux_undefined:      a multiplexed signal (m0, m1...) in a message with no multiplexer (M);
                      the parser silently drops the multiplexing (DBC text only)

Each finding names the message or signal and the numbers that show the problem. A clean
result means these checks ran and found nothing, not that the DBC is correct.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness.anvil.dbc import load_raw, raw_range

CATEGORIES = ("duplicate_frame_id", "signal_overlap", "outside_frame", "range_unreachable",
              "range_inverted", "range_missing", "unknown_node", "invalid_length",
              "bad_encoding", "mux_undefined")
_LENGTHS = set(range(9)) | {12, 16, 20, 24, 32, 48, 64}
_BO = re.compile(r"^BO_\s+\d+\s+(\w+)\s*:", re.MULTILINE)
_SG = re.compile(r"^\s*SG_\s+(\w+)\s*(M|m\d+M?)?\s*:\s*\d+\|\d+@(\S)(\S)",
                 re.MULTILINE)
_NO_NODE = {"Vector__XXX", ""}


def bit_positions(s) -> list[int]:
    """Bit numbers (byte * 8 + bit, LSB = 0) a cantools signal occupies."""
    if s.byte_order == "little_endian":
        return list(range(s.start, s.start + s.length))
    out, bit = [], s.start  # Motorola: start is the MSB, bits run down then to the next byte
    for _ in range(s.length):
        out.append(bit)
        bit = bit + 15 if bit % 8 == 0 else bit - 1
    return out


def _fmt(x: float) -> str:
    return f"{x:g}"


def check_db(db, filename: str) -> list[dict]:
    out = []

    def add(subject, cat, evidence, why, question):
        out.append({"req_id": filename, "category": cat, "evidence": evidence,
                    "explanation": why, "question_for_author": question,
                    "related_ids": [], "subject": subject})

    seen: dict[tuple[int, bool], str] = {}
    nodes = {n.name for n in db.nodes}
    undeclared: dict[str, list[str]] = {}
    no_range: list[str] = []
    total = 0
    for m in db.messages:
        if nodes:
            used = [(m.name, n, "sender") for n in m.senders or []] + [
                (s.name, n, "receiver") for s in m.signals for n in s.receivers or []]
            for subject, n, role in used:
                if n not in nodes and n not in _NO_NODE:
                    undeclared.setdefault(n, []).append(f"{role} of {subject}")
        if m.length not in _LENGTHS:
            add(m.name, "invalid_length", str(m.length),
                f"{m.name} is {m.length} bytes long; CAN allows 0 to 8 and CAN FD 12, 16, 20, "
                "24, 32, 48 or 64.", f"How long is {m.name}?")
        key = (m.frame_id, bool(m.is_extended_frame))
        if key in seen:
            add(m.name, "duplicate_frame_id", f"0x{m.frame_id:X}",
                f"Messages {seen[key]} and {m.name} both use frame ID 0x{m.frame_id:X}.",
                "Which message owns this frame ID?")
        else:
            seen[key] = m.name
        bits = {s.name: bit_positions(s) for s in m.signals}
        frame_bits = m.length * 8
        for s in m.signals:
            total += 1
            if any(b < 0 or b >= frame_bits for b in bits[s.name]):
                add(s.name, "outside_frame", s.name,
                    f"{s.name} ({s.length} bits from bit {s.start}) does not fit in "
                    f"{m.name}, which is {m.length} bytes long.",
                    f"Is {m.name} longer, or is {s.name} placed wrongly?")
            if s.minimum is not None and s.maximum is not None and s.minimum > s.maximum:
                add(s.name, "range_inverted", f"[{_fmt(s.minimum)}|{_fmt(s.maximum)}]",
                    f"{s.name}'s minimum {_fmt(s.minimum)} is above its maximum "
                    f"{_fmt(s.maximum)}.", "Which are the intended limits?")
                continue
            lo, hi = raw_range(s)
            if (s.minimum is None and s.maximum is None) or (s.minimum == s.maximum == 0):
                no_range.append(s.name)
                continue
            tol = abs(s.scale) / 2
            bad = [f"{w} {_fmt(v)}" for w, v in (("minimum", s.minimum), ("maximum", s.maximum))
                   if v is not None and (v < lo - tol or v > hi + tol)]
            if bad:
                add(s.name, "range_unreachable", f"[{_fmt(s.minimum)}|{_fmt(s.maximum)}]",
                    f"{s.name}'s {' and '.join(bad)} cannot be sent: {s.length} "
                    f"{'signed' if s.is_signed else 'unsigned'} bits at scale {_fmt(s.scale)}, "
                    f"offset {_fmt(s.offset)} carry {_fmt(lo)}..{_fmt(hi)}.",
                    f"Is the range, the length or the scale of {s.name} wrong?")
        names = [s.name for s in m.signals]
        mux = {s.name: set(s.multiplexer_ids or []) for s in m.signals}
        pairs = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if mux[a] and mux[b] and not (mux[a] & mux[b]):
                    continue  # never in the same frame
                common = set(bits[a]) & set(bits[b])
                if common:
                    pairs.append(f"{a} / {b} ({len(common)} bits from bit {min(common)})")
        if pairs:
            add(m.name, "signal_overlap", pairs[0].split(" (")[0],
                f"In {m.name}, {len(pairs)} pair(s) of signals share bits: {_some(pairs)}.",
                f"Where should these signals sit in {m.name}?")
    # One finding per undeclared node and one for all missing ranges: a person decides
    # each kind of problem once, not once per signal.
    for n, uses in sorted(undeclared.items()):
        add(n, "unknown_node", n,
            f"{n} is not among the nodes {', '.join(sorted(nodes))}, but is the "
            f"{_some(uses)}.", f"Is {n} a missing node or a typo?")
    if no_range:
        add(no_range[0] if len(no_range) == 1 else f"{len(no_range)} signals",
            "range_missing", f"{len(no_range)} of {total} signals [0|0]",
            f"{len(no_range)} of {total} signals have no minimum or maximum ({_some(no_range)})."
            " Zyn checks their values against the range their bits allow.",
            "What are the valid ranges of these signals?")
    return out


def _some(items: list[str], n: int = 4) -> str:
    head = ", ".join(items[:n])
    return head + (f" and {len(items) - n} more" if len(items) > n else "")


def check_dbc_text(text: str, filename: str) -> list[dict]:
    """Faults the parser hides: it reads them without error and changes their meaning."""
    out = []

    def add(subject, cat, evidence, why, question):
        out.append({"req_id": filename, "category": cat, "evidence": evidence,
                    "explanation": why, "question_for_author": question,
                    "related_ids": [], "subject": subject})

    blocks = list(_BO.finditer(text))
    for i, b in enumerate(blocks):
        body = text[b.end(): blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]
        sigs = list(_SG.finditer(body))
        has_mux = any(s.group(2) and s.group(2).startswith("M") or
                      (s.group(2) or "").endswith("M") for s in sigs)
        for s in sigs:
            name, mux, order, sign = s.groups()
            if order not in "01" or sign not in "+-":
                add(name, "bad_encoding", f"@{order}{sign}",
                    f"{name} is encoded as @{order}{sign}; a DBC allows @0 (Motorola) or @1 "
                    "(Intel) followed by + or -. The parser reads it as Intel unsigned.",
                    f"What byte order and sign does {name} use?")
            if mux and mux.startswith("m") and not has_mux:
                add(name, "mux_undefined", mux,
                    f"{name} is multiplexed ({mux}) but {b.group(1)} has no multiplexer "
                    "signal (M). The parser drops the multiplexing.",
                    f"Which signal selects {name} in {b.group(1)}?")
    return out


def check_file(path: Path | str) -> list[dict]:
    """Findings on a DBC (or KCD, SYM, ARXML) file. Raises ValueError for a file that
    cannot be read at all or holds no signals, so an unreadable database never looks clean."""
    path = Path(path)
    try:
        db = load_raw(path)
    except Exception as e:  # any parser error
        raise ValueError(f"{path.name} could not be read as a CAN database: {e}") from e
    if not any(m.signals for m in db.messages):
        raise ValueError(f"{path.name} has no signals, so nothing can be checked against it.")
    found = check_db(db, path.name)
    if path.suffix.lower() == ".dbc":
        found += check_dbc_text(path.read_text(encoding="utf-8", errors="replace"), path.name)
    return found
