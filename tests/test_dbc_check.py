"""Code checks on the CAN database before Anvil Review trusts it."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.anvil.dbc_check import bit_positions, check_file
from harness.outside import start_tests

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"

FAULTY = '''VERSION ""
BU_: A B
BO_ 100 Engine: 8 A
 SG_ Rpm : 0|16@1+ (1,0) [0|8000] "rpm" B
 SG_ Load : 8|8@1+ (1,0) [0|100] "%" B
BO_ 100 Brake: 2 A
 SG_ Pressure : 8|16@1+ (0.1,0) [0|250] "bar" B
BO_ 200 Body: 2 A
 SG_ Temp : 0|8@1+ (0.5,-40) [-40|200] "degC" B
 SG_ Level : 8|4@1+ (1,0) [10|5] "" B
'''


def _cats(text: str, tmp_path: Path) -> dict[str, str]:
    p = tmp_path / "faulty.dbc"
    p.write_text(text, encoding="utf-8")
    return {f["category"]: f["subject"] for f in check_file(p)}


def test_synthetic_dbc_is_clean():
    assert check_file(DATA / "icx100.dbc") == []


def test_each_fault_is_reported_with_its_subject(tmp_path):
    got = _cats(FAULTY, tmp_path)
    assert got["duplicate_frame_id"] == "Brake"
    assert got["signal_overlap"] == "Engine"       # Load sits inside Rpm's 16 bits
    assert got["outside_frame"] == "Pressure"      # bits 8..23 in a 2-byte frame
    assert got["range_unreachable"] == "Temp"      # 8 bits at 0.5, -40 reach 87.5
    assert got["range_inverted"] == "Level"


def test_motorola_bits_run_down_then_to_the_next_byte():
    class S:
        byte_order, start, length = "big_endian", 7, 12
    assert bit_positions(S) == [7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12]


def test_multiplexed_signals_may_share_bits(tmp_path):
    text = '''VERSION ""
BU_: A B
BO_ 300 Mux: 8 A
 SG_ Sel M : 0|8@1+ (1,0) [0|1] "" B
 SG_ X m0 : 8|8@1+ (1,0) [0|255] "" B
 SG_ Y m1 : 8|8@1+ (1,0) [0|255] "" B
'''
    assert "signal_overlap" not in _cats(text, tmp_path)


def test_dbc_findings_become_a_row_in_the_review(audit, tmp_path):
    dbc = tmp_path / "faulty.dbc"
    dbc.write_text(FAULTY, encoding="utf-8")
    tests = tmp_path / "test_x.py"
    tests.write_text("def test_a(bench):\n    bench.set('Rpm', 900)\n", encoding="utf-8")
    run = start_tests(audit, [tests], dbc)
    rows = {i["payload"]["ext_id"]: i for i in audit.list_items(run, "imported_requirement")}
    assert rows["faulty.dbc"]["payload"]["heading"] == "CAN database"
    on_dbc = [f for f in audit.list_items(run, "finding")
              if f["payload"]["req_id"] == "faulty.dbc"]
    assert len(on_dbc) == 5


def test_kcd_and_dbc_read_the_same(tmp_path):
    """cantools reads KCD, SYM and ARXML as well as DBC; Anvil Review accepts them."""
    import cantools

    from harness.anvil.dbc import load_dbc

    kcd = tmp_path / "icx100.kcd"
    kcd.write_text(cantools.database.load_file(str(DATA / "icx100.dbc")).as_kcd_string(),
                   encoding="utf-8")
    a, b = load_dbc(DATA / "icx100.dbc"), load_dbc(kcd)
    assert set(a.signals) == set(b.signals)
    assert {n: (s.minimum, s.maximum) for n, s in a.signals.items()} == {
        n: (s.minimum, s.maximum) for n, s in b.signals.items()}
    assert check_file(kcd) == []


def test_senders_and_receivers_must_be_listed_nodes(tmp_path):
    text = '''VERSION ""
BU_: A B
BO_ 100 M: 8 A
 SG_ S : 0|8@1+ (1,0) [0|255] "" C
BO_ 101 N: 8 Z
 SG_ T : 0|8@1+ (1,0) [0|255] "" Vector__XXX
'''
    p = tmp_path / "nodes.dbc"
    p.write_text(text, encoding="utf-8")
    got = sorted((f["subject"], f["evidence"]) for f in check_file(p)
                 if f["category"] == "unknown_node")
    assert got == [("C", "C"), ("Z", "Z")]


def test_faults_the_parser_hides(tmp_path):
    text = '''VERSION ""
BU_: A B
BO_ 100 Long: 99 A
 SG_ S : 0|8@1+ (1,0) [0|255] "" B
BO_ 101 Odd: 8 A
 SG_ T : 0|8@2+ (1,0) [0|255] "" B
BO_ 102 Mux: 8 A
 SG_ X m0 : 8|8@1+ (1,0) [0|255] "" B
'''
    got = _cats(text, tmp_path)
    assert got["invalid_length"] == "Long"
    assert got["bad_encoding"] == "T"
    assert got["mux_undefined"] == "X"


OPENDBC = Path(__file__).resolve().parents[1] / "data" / "public" / "opendbc"


@pytest.mark.skipif(not any(OPENDBC.glob("*.dbc")) if OPENDBC.exists() else True,
                    reason="run: python -m evals.opendbc fetch")
def test_real_dbcs_are_read_or_refused_with_a_reason():
    """Every public file either loads and is checked, or stops with the parser's reason."""
    import evals.opendbc as e

    report = e.run()
    assert report["read"] + len(report["unreadable"]) == report["files"]
    assert all("could not be read" in why for why in report["unreadable"].values())
    assert report["read"] >= 50
