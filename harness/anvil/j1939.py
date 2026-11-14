"""SAE J1939 protocol checks for commercial vehicle CAN databases (Batch G).

Deterministic checks on 29-bit CAN identifiers and payload limits:
- j1939_edp_reserved: Extended Data Page (bit 25) is set to 1 with DP=0,
  which is reserved by SAE J1939-21:2006.
- j1939_dlc_exceeded: Payload exceeds the J1939 Transport Protocol limit of 1785 bytes
  (255 packets x 7 bytes) on classic CAN.
- j1939_global_source: Transmitting node uses global broadcast address (255 / 0xFF) as
  a source address. Standard DBC templates with source address 254 (0xFE) and PGN 60928
  (Address Claimed) are not flagged.
"""

from __future__ import annotations

from typing import Any

J1939_CATEGORIES = (
    "j1939_edp_reserved",
    "j1939_global_source",
    "j1939_dlc_exceeded",
)

NULL_ADDRESS = 254  # 0xFE (Any sender / unassigned in template DBCs)
GLOBAL_ADDRESS = 255  # 0xFF (Broadcast address; cannot be a transmitting source address)
ADDRESS_CLAIMED_PGN = 60928  # 0xEE00


def parse_j1939_id(can_id: int) -> dict[str, Any]:
    """Decodes a 29-bit J1939 CAN identifier into its protocol fields."""
    priority = (can_id >> 26) & 0x07
    edp = (can_id >> 25) & 0x01
    data_page = (can_id >> 24) & 0x01
    pdu_format = (can_id >> 16) & 0xFF
    pdu_specific = (can_id >> 8) & 0xFF
    source_address = can_id & 0xFF

    is_pdu1 = pdu_format < 240
    destination_address = pdu_specific if is_pdu1 else None
    pgn = (data_page << 16) | (pdu_format << 8) | (0 if is_pdu1 else pdu_specific)

    return {
        "can_id": can_id,
        "priority": priority,
        "edp": edp,
        "reserved": edp,  # alias for backwards compatibility
        "data_page": data_page,
        "pdu_format": pdu_format,
        "pdu_specific": pdu_specific,
        "source_address": source_address,
        "is_pdu1": is_pdu1,
        "destination_address": destination_address,
        "pgn": pgn,
    }


def is_j1939_database(db: Any) -> bool:
    """Decides whether a CAN database is J1939 from DBC ProtocolType attribute.

    No guessing from 29-bit identifier width: other automotive networks (such as GMLAN
    or proprietary battery packs) use 29-bit frames without being J1939.
    """
    protocol = getattr(db, "protocol", None)
    if protocol and "j1939" in str(protocol).lower():
        return True
    dbc_obj = getattr(db, "dbc", None)
    if dbc_obj and getattr(dbc_obj, "attributes", None):
        pt = dbc_obj.attributes.get("ProtocolType")
        if pt is not None:
            val = getattr(pt, "value", pt)
            if "j1939" in str(val).lower():
                return True
    return False


def is_j1939_message(m: Any, db_is_j1939: bool = False) -> bool:
    """Decides whether an individual message is J1939."""
    proto = getattr(m, "protocol", None)
    if proto and "j1939" in str(proto).lower():
        return True
    m_dbc = getattr(m, "dbc", None)
    if m_dbc and getattr(m_dbc, "attributes", None):
        vf = m_dbc.attributes.get("VFrameFormat")
        if vf is not None:
            val = getattr(vf, "value", vf)
            # In Vector DBC enums: 3 is J1939PG, or string "J1939PG"
            if str(val) == "3" or "j1939" in str(val).lower():
                return True
    if db_is_j1939:
        # On a declared J1939 database, 29-bit frames are J1939 PGNs
        return getattr(m, "is_extended_frame", False) or getattr(m, "frame_id", 0) > 2047
    return False


def check_j1939(db: Any, filename: str) -> list[dict[str, Any]]:
    """Runs SAE J1939 deterministic integrity checks across messages in a CAN database."""
    findings: list[dict[str, Any]] = []

    def add(msg_name: str, cat: str, subject: str, problem: str, question: str):
        findings.append({
            "target": f"{filename}:{msg_name}",
            "payload": {
                "category": cat,
                "subject": subject,
                "problem": problem,
                "question": question,
            },
        })

    is_db_j1939 = is_j1939_database(db)

    for m in getattr(db, "messages", []):
        if not is_j1939_message(m, is_db_j1939):
            continue

        frame_id = getattr(m, "frame_id", 0)
        is_extended = getattr(m, "is_extended_frame", False) or frame_id > 2047

        # SAE J1939 networks may carry proprietary 11-bit standard frames; do not flag them
        if not is_extended:
            continue

        decoded = parse_j1939_id(frame_id)

        # 1. Extended Data Page (EDP) check:
        # Per SAE J1939-21 (2006 on): EDP=0/DP=0 is page 0, EDP=0/DP=1 is page 1,
        # EDP=1/DP=0 is "SAE J1939 reserved", and EDP=1/DP=1 is "ISO 15765-3 defined".
        # Flag EDP=1/DP=0 only (ISO 15765-2 fixed addressing uses EDP=0).
        if decoded["edp"] == 1 and decoded["data_page"] == 0:
            add(
                m.name,
                "j1939_edp_reserved",
                f"EDP={decoded['edp']}, DP={decoded['data_page']}",
                f"Message '{m.name}' (ID 0x{frame_id:08X}) has Extended Data Page (bit 25) set to 1 "
                "with Data Page (bit 24) set to 0. This combination is reserved by SAE J1939-21.",
                "Why is EDP set to 1 with Data Page set to 0?",
            )

        # 2. Source address check:
        # Public J1939 DBCs use source address 254 (0xFE) to represent 'any sender' or template,
        # and PGN 60928 (Address Claimed / Cannot Claim) is sent from 0xFE by rule.
        # Neither is flagged.
        # Address 255 (0xFF) is the global broadcast address and cannot be a transmitting source.
        if decoded["source_address"] == GLOBAL_ADDRESS:
            add(
                m.name,
                "j1939_global_source",
                "SA 255 (0xFF)",
                f"Message '{m.name}' (PGN {decoded['pgn']}) has source address 255 (0xFF / Global Address). "
                "A global broadcast address cannot be used as a transmitting source address.",
                "Which controller source address should transmit this PGN?",
            )

        # 3. Message length check:
        # In J1939, message length over 8 declared in the DBC indicates a multi-packet message
        # carried by Transport Protocol (BAM / RTS-CTS, up to 1785 bytes: 255 packets x 7 bytes).
        # Standard DBC files omit single-frame markers, so lengths between 9 and 1785 bytes are
        # accepted as declared multi-packet messages. Lengths over 1785 exceed classic CAN TP capacity and are flagged.
        length = getattr(m, "length", 0)
        is_fd = getattr(m, "is_fd", False)
        if length > 1785 and not is_fd:
            add(
                m.name,
                "j1939_dlc_exceeded",
                f"{length} bytes",
                f"Message '{m.name}' length is {length} bytes on classic CAN, exceeding the "
                "J1939 Transport Protocol maximum of 1785 bytes (255 packets x 7 bytes).",
                "Is this message intended to use CAN FD or a smaller payload?",
            )

    return findings
