"""Tests for Project 3: SAE J1939 protocol checks and Vector vTESTstudio test review."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.anvil import j1939
from harness.outside import split_tests


def test_parse_j1939_id():
    # Electronic Engine Controller 1 (EEC1): PGN 61444 (0xF004), Priority 3, SA 0
    # CAN ID: (3 << 26) | (0 << 25) | (0 << 24) | (0xF0 << 16) | (0x04 << 8) | 0x00
    # = 0x0CF00400 = 217056256
    can_id = 0x0CF00400
    res = j1939.parse_j1939_id(can_id)
    assert res["priority"] == 3
    assert res["reserved"] == 0
    assert res["data_page"] == 0
    assert res["pdu_format"] == 0xF0  # 240, PDU2 broadcast
    assert res["pdu_specific"] == 0x04
    assert res["source_address"] == 0x00
    assert not res["is_pdu1"]
    assert res["destination_address"] is None
    assert res["pgn"] == 61444

    # PDU1 message (peer-to-peer): e.g. Torque/Speed Control 1 (TSC1), PGN 0, DA 0x00, SA 0x0B
    # CAN ID: (3 << 26) | (0 << 25) | (0 << 24) | (0x00 << 16) | (0x00 << 8) | 0x0B
    # = 0x0C00000B
    tsc1_id = 0x0C00000B
    res_tsc1 = j1939.parse_j1939_id(tsc1_id)
    assert res_tsc1["is_pdu1"]
    assert res_tsc1["pdu_format"] == 0
    assert res_tsc1["destination_address"] == 0
    assert res_tsc1["source_address"] == 0x0B
    assert res_tsc1["pgn"] == 0


def test_j1939_database_checks():
    # Clean message (EEC1): 29-bit, bit 25=0, SA=0, DLC=8
    m_clean = SimpleNamespace(
        name="EEC1",
        frame_id=0x0CF00400,
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # Fault 1: bit 25=1 and bit 24=0 (EDP=1, DP=0 is SAE J1939 reserved)
    m_bad_reserved = SimpleNamespace(
        name="BadReserved",
        frame_id=0x0CF00400 | (1 << 25),
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # Permitted: bit 25=1 and bit 24=1 is defined for ISO 15765-3
    m_iso15765_3 = SimpleNamespace(
        name="IsoDiagMsg",
        frame_id=0x0CF00400 | (1 << 25) | (1 << 24),
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # Fault 2: source address is 255 (0xFF / Global broadcast address cannot transmit)
    m_null_source = SimpleNamespace(
        name="NullSender",
        frame_id=(0x0CF00400 & ~0xFF) | 255,
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # 11-bit standard frames are allowed on J1939 (proprietary frames)
    m_standard = SimpleNamespace(
        name="StdMsg",
        frame_id=0x123,
        is_extended_frame=False,
        length=8,
        is_fd=False,
    )
    # Fault 3: DLC > 1785 bytes without FD
    m_oversized = SimpleNamespace(
        name="BigMsg",
        frame_id=0x0CF00500,
        is_extended_frame=True,
        length=2000,
        is_fd=False,
    )

    db = SimpleNamespace(
        protocol="J1939",
        messages=[m_clean, m_bad_reserved, m_iso15765_3, m_null_source, m_standard, m_oversized],
    )

    findings = j1939.check_j1939(db, "truck.dbc")
    cats = {f["payload"]["category"] for f in findings}
    targets = [f["target"] for f in findings]

    assert "j1939_edp_reserved" in cats
    assert "truck.dbc:BadReserved" in targets
    assert "truck.dbc:IsoDiagMsg" not in targets
    assert "j1939_global_source" in cats
    assert "j1939_dlc_exceeded" in cats
    assert "j1939_standard_id" not in cats


def test_j1939_g1_no_flag_on_0xfe_and_address_claimed():
    """G1: 0xFE is 'any sender' in public DBCs and PGN 60928 sends from 0xFE by rule; neither is flagged."""
    # EEC1 with source 0xFE (standard template DBC)
    m_eec1_0xfe = SimpleNamespace(
        name="EEC1",
        frame_id=0x0CF004FE,
        is_extended_frame=True,
        length=8,
        is_fd=False,
        protocol="j1939",
    )
    # PGN 60928 (Address Claimed) from 0xFE (Cannot Claim)
    # PGN 60928 = 0xEE00, PDU1, DA=0xFF (global), SA=0xFE -> 0x18EEFFFE
    m_addr_claimed = SimpleNamespace(
        name="AddressClaimed",
        frame_id=0x18EEFFFE,
        is_extended_frame=True,
        length=8,
        is_fd=False,
        protocol="j1939",
    )
    # Real invalid source: 0xFF (global broadcast address cannot transmit)
    m_bad_global_sa = SimpleNamespace(
        name="BadGlobalSender",
        frame_id=0x0CF004FF,
        is_extended_frame=True,
        length=8,
        is_fd=False,
        protocol="j1939",
    )

    db = SimpleNamespace(
        protocol="J1939",
        messages=[m_eec1_0xfe, m_addr_claimed, m_bad_global_sa],
    )

    findings = j1939.check_j1939(db, "truck.dbc")
    targets = [f["target"] for f in findings]
    assert "truck.dbc:EEC1" not in targets
    assert "truck.dbc:AddressClaimed" not in targets
    assert "truck.dbc:BadGlobalSender" in targets


def test_j1939_g2_valid_multipacket_dlc():
    """G2: lengths > 8 up to 1785 bytes are valid multi-packet (TP); > 1785 reports one fault, not two."""
    from harness.anvil import dbc_check

    # DM1 active diagnostic trouble codes (e.g. 200 bytes, transported via BAM)
    m_dm1 = SimpleNamespace(
        name="DM1",
        frame_id=0x18FECA00,
        is_extended_frame=True,
        length=200,
        is_fd=False,
        protocol="j1939",
        signals=[],
        senders=[],
    )
    # Excessively long message (> 1785 bytes)
    m_oversized = SimpleNamespace(
        name="OverLimit",
        frame_id=0x18FEE000,
        is_extended_frame=True,
        length=2000,
        is_fd=False,
        protocol="j1939",
        signals=[],
        senders=[],
    )

    db = SimpleNamespace(
        protocol="J1939",
        messages=[m_dm1, m_oversized],
        nodes=[],
    )

    findings = dbc_check.check_db(db, "truck.dbc")
    dm1_finds = [f for f in findings if f["subject"] == "DM1"]
    over_finds = [f for f in findings if f["subject"] == "OverLimit"]

    # DM1 at 200 bytes is valid in J1939 TP
    assert len(dm1_finds) == 0
    # OverLimit (> 1785 bytes) gets exactly 1 fault, not two (no duplicate invalid_length + j1939_dlc_exceeded)
    assert len(over_finds) == 1
    assert over_finds[0]["category"] == "j1939_dlc_exceeded"


def test_j1939_g3_no_guessing_from_29bit_ids():
    """G3: a 29-bit DBC that is not J1939 (e.g. GMLAN or battery) gets zero J1939 findings."""
    # 29-bit non-J1939 frame with bit 25=1 or SA=0xFE shape
    m_gmlan = SimpleNamespace(
        name="GMLAN_Status",
        frame_id=0x10203040,
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    db = SimpleNamespace(
        messages=[m_gmlan],
    )
    findings = j1939.check_j1939(db, "gmlan.dbc")
    assert len(findings) == 0


def test_j1939_g4_attributes_and_spn(tmp_path):
    """G4: ProtocolType and SPN attributes are properly read from DBC."""
    from harness.anvil.dbc import load_dbc

    ext_id = 0x0CF00400 | 0x80000000
    dbc_text = f"""VERSION ""
NS_ :
    BA_DEF_
    BA_
    BA_DEF_DEF_
BS_:
BU_: Engine
BO_ {ext_id} EEC1: 8 Engine
 SG_ EngSpeed : 0|16@1+ (0.125,0) [0|8000] "rpm" Vector__XXX
BA_DEF_ "ProtocolType" STRING ;
BA_DEF_ SG_ "SPN" INT 0 524287;
BA_ "ProtocolType" "J1939";
BA_ "SPN" SG_ {ext_id} EngSpeed 190;
"""
    p = tmp_path / "j1939_sample.dbc"
    p.write_text(dbc_text, encoding="utf-8")
    db = load_dbc(p)
    assert db.signals["EngSpeed"].spn == 190


def test_j1939_g5_11bit_standard_frames_allowed():
    """G5: 11-bit standard frames on a J1939 network are allowed (proprietary frames)."""
    m_std = SimpleNamespace(
        name="Proprietary11",
        frame_id=0x123,
        is_extended_frame=False,
        length=8,
        is_fd=False,
    )
    db = SimpleNamespace(protocol="J1939", messages=[m_std])
    findings = j1939.check_j1939(db, "truck.dbc")
    assert not any(f["payload"]["category"] == "j1939_standard_id" for f in findings)


def test_j1939_g6_extended_data_page():
    """G6 & Batch I: bit 25 is Extended Data Page; reserved combination is EDP=1 and DP=0."""
    # EDP=1, DP=1: ISO 15765-3 defined (allowed, not reserved)
    id_edp_iso = 0x0CF00400 | (1 << 25) | (1 << 24)
    m_iso = SimpleNamespace(name="IsoDiag", frame_id=id_edp_iso, is_extended_frame=True, length=8, is_fd=False, protocol="j1939")

    # EDP=1, DP=0: Reserved combination per SAE J1939-21:2006
    id_edp_reserved = 0x0CF00400 | (1 << 25)
    m_res = SimpleNamespace(name="BadEDP", frame_id=id_edp_reserved, is_extended_frame=True, length=8, is_fd=False, protocol="j1939")

    db = SimpleNamespace(protocol="J1939", messages=[m_iso, m_res])
    findings = j1939.check_j1939(db, "truck.dbc")
    cats = {f["payload"]["category"] for f in findings}
    targets = {f["target"] for f in findings}

    assert "truck.dbc:IsoDiag" not in targets
    assert "truck.dbc:BadEDP" in targets
    assert "j1939_edp_reserved" in cats


def test_vteststudio_g7_and_g8_parser_features(tmp_path):
    """G7 & G8: uppercase extension, child elements, attribute order, XML comments stripped, title child, refusal when empty."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests

    # 1. Uppercase .VTT is recognized
    vtt = tmp_path / "TESTS.VTT"
    vtt.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testunit>
  <!-- Comment containing check that must be ignored -->
  <!-- <teststep action="check" signal="EngineSpeed" value="99999" /> -->
  <testcase classname="pkg.IgnoredClass" name="TC_OrderTest">
    <!-- wait before value: must pick value 9500, not 100 -->
    <teststep action="check" signal="EngineSpeed" wait="100" value="9500" />
  </testcase>
  <testcase>
    <!-- Title as child element -->
    <title>TC_ChildLayout</title>
    <teststep>
      <action>check</action>
      <signal>EngineSpeed</signal>
      <value>9200</value>
    </teststep>
  </testcase>
</testunit>
""",
        encoding="utf-8",
    )

    units = split_tests(vtt)
    assert len(units) == 2
    # G8: does not use classname
    assert units[0].name == "TC_OrderTest"
    assert units[1].name == "TC_ChildLayout"

    # Run check_tests against CAN database with max 8000
    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 20, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    findings, _ = check_tests(units, db, {})
    oor_values = [f["evidence"] for f in findings if f["category"] == "out_of_range"]
    assert "9500" in oor_values
    assert "9200" in oor_values
    assert "100" not in oor_values  # wait was not picked
    assert "99999" not in oor_values  # comment was ignored

    # File with no testcases is refused
    empty_vtt = tmp_path / "empty.vtt"
    empty_vtt.write_text("<testunit><otherTag>nothing</otherTag></testunit>", encoding="utf-8")
    with pytest.raises(ValueError, match="no recognized test cases"):
        split_tests(empty_vtt)


def test_weak_words_g9_narrowed_exceptions():
    """G9: contextual exceptions allow only standards and specific technical terms, flagging vague words."""
    from harness.sift.rules import RuleProfile

    profile = RuleProfile(name="test")

    # Real vague words must be FLAGGED
    vague_samples = [
        "as required by the driver",
        "as required in the current situation",
        "within the normal range",
        "operate at normal voltage",
        "return to normal mode",
    ]
    for sample in vague_samples:
        found = profile.weak_words(sample)
        assert len(found) > 0, f"Expected weak word flagged in '{sample}'"

    # Specific standard terms must NOT be flagged
    technical_samples = [
        "as required by ISO 26262-6",
        "as required by UN ECE 155",
        "as required by SAE J1939",
        "system uses Fast Ethernet for flashing",
        "supports fast charging at 350kW",
        "CAN flexible data-rate protocol",
    ]
    for sample in technical_samples:
        found = profile.weak_words(sample)
        assert len(found) == 0, f"Expected no weak word flagged in '{sample}', got {found}"


def test_batch_i_edp_inverted_rule():
    """Batch I finding 8: EDP=1/DP=0 is SAE J1939 reserved; EDP=1/DP=1 is ISO 15765-3 defined (permitted)."""
    from harness.anvil import j1939

    # EDP=1, DP=0: reserved
    m_reserved = SimpleNamespace(
        name="ReservedPage",
        frame_id=0x0CF00400 | (1 << 25),  # EDP=1, DP=0
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # EDP=1, DP=1: ISO 15765-3 defined (allowed)
    m_iso = SimpleNamespace(
        name="IsoDiag",
        frame_id=0x0CF00400 | (1 << 25) | (1 << 24),  # EDP=1, DP=1
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )
    # Global broadcast source 255
    m_global_sa = SimpleNamespace(
        name="GlobalSender",
        frame_id=0x0CF004FF,
        is_extended_frame=True,
        length=8,
        is_fd=False,
    )

    db = SimpleNamespace(
        protocol="J1939",
        messages=[m_reserved, m_iso, m_global_sa],
    )
    findings = j1939.check_j1939(db, "truck.dbc")
    targets = [f["target"] for f in findings]
    cats = {f["payload"]["category"] for f in findings}

    assert "truck.dbc:ReservedPage" in targets
    assert "truck.dbc:IsoDiag" not in targets
    assert "j1939_edp_reserved" in cats
    assert "j1939_global_source" in cats


def test_batch_i_minified_xml_no_false_findings(tmp_path):
    """Batch I finding 9: Single-line XML does not get false no_setup or unknown_signal."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    xml_file = tmp_path / "minified.vtt"
    # Single-line minified XML with a set step and an expect step
    xml_file.write_text(
        '<testunit><testcase name="SpeedVerification" id="tc1"><teststep action="set" signal="EngineSpeed" value="1000"/><teststep action="check" signal="EngineSpeed" value="1000"/></testcase></testunit>',
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(xml_file)
    assert len(units) == 1
    assert units[0].name == "SpeedVerification"

    findings, _ = check_tests(units, db, {})
    cats = {f["category"] for f in findings}

    # Should NOT have false no_setup (it has a set step)
    assert "no_setup" not in cats
    # Should NOT have false unknown_signal from test name "SpeedVerification"
    assert "unknown_signal" not in cats


def test_batch_i_element_text_values(tmp_path):
    """Batch I finding 10: Values written as element text are read correctly."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    vtt = tmp_path / "text_val.vtt"
    vtt.write_text(
        """<testunit>
  <testcase name="TextValueTest">
    <teststep action="set" signal="EngineSpeed">1000</teststep>
    <teststep action="check" signal="EngineSpeed">9500</teststep>
  </testcase>
</testunit>""",
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(vtt)
    findings, _ = check_tests(units, db, {})

    oor = [f for f in findings if f["category"] == "out_of_range"]
    assert len(oor) == 1
    assert oor[0]["evidence"] == "9500"


def test_batch_i_namespaced_xml(tmp_path):
    """Batch I finding 11: Namespaced XML matches local tags and attributes."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    vtt = tmp_path / "namespaced.vtt"
    vtt.write_text(
        """<ns:testunit xmlns:ns="http://vector.com/vteststudio">
  <ns:testcase ns:name="NamespacedTC">
    <ns:teststep ns:action="set" ns:signal="EngineSpeed" ns:value="1000"/>
    <ns:teststep ns:action="check" ns:signal="EngineSpeed" ns:value="9600"/>
  </ns:testcase>
</ns:testunit>""",
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(vtt)
    assert len(units) == 1
    assert units[0].name == "NamespacedTC"

    findings, _ = check_tests(units, db, {})
    oor = [f for f in findings if f["category"] == "out_of_range"]
    assert len(oor) == 1
    assert oor[0]["evidence"] == "9600"


def test_batch_i_nested_testcases(tmp_path):
    """Batch I finding 12: Nested test cases are not checked twice (steps checked under innermost test case)."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    vtt = tmp_path / "nested.vtt"
    vtt.write_text(
        """<testunit>
  <testcase name="Outer">
    <teststep action="set" signal="EngineSpeed" value="1000"/>
    <testcase name="Inner">
      <teststep action="check" signal="EngineSpeed" value="9700"/>
    </testcase>
  </testcase>
</testunit>""",
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(vtt)
    assert len(units) == 2
    assert units[0].name == "Outer"
    assert units[1].name == "Inner"

    findings, _ = check_tests(units, db, {})
    # 9700 out of range must be reported only under Inner, not twice
    oor = [f for f in findings if f["category"] == "out_of_range"]
    assert len(oor) == 1
    assert oor[0]["req_id"] == "Inner"
    assert oor[0]["evidence"] == "9700"


def test_batch_i_xml_doctype_comments_and_utf16(tmp_path):
    """Batch I finding 13: DOCTYPE inside comment and UTF-16 files accepted; real DOCTYPE refused."""
    from harness.outside import split_tests

    # DOCTYPE inside comment
    safe_comment = tmp_path / "safe_comment.vtt"
    safe_comment.write_text(
        '<!-- <!DOCTYPE ignore-me> --><testunit><testcase name="CommentTest"><teststep/></testcase></testunit>',
        encoding="utf-8",
    )
    units = split_tests(safe_comment)
    assert len(units) == 1
    assert units[0].name == "CommentTest"

    # UTF-16 encoded file
    utf16_file = tmp_path / "utf16_test.vtt"
    utf16_content = '<?xml version="1.0" encoding="utf-16"?><testunit><testcase name="Utf16Test"><teststep/></testcase></testunit>'
    utf16_file.write_bytes(utf16_content.encode("utf-16"))
    units16 = split_tests(utf16_file)
    assert len(units16) == 1
    assert units16[0].name == "Utf16Test"

    # Real DOCTYPE is refused
    bad_doctype = tmp_path / "bad.vtt"
    bad_doctype.write_text(
        '<!DOCTYPE testunit SYSTEM "evil.dtd"><testunit><testcase name="Evil"/></testunit>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="forbidden DOCTYPE"):
        split_tests(bad_doctype)


def test_batch_i_weak_words_allow_pattern_narrowed():
    """Batch I finding 14: Standards body requires document number; generic 'standards' or 'en route' are flagged."""
    from harness.sift.rules import RuleProfile

    profile = RuleProfile(name="test")

    # Generic or loanword uses are FLAGGED
    assert len(profile.weak_words("The system behaves as required by SAE standards.")) > 0
    assert len(profile.weak_words("Power is adjusted as required by en route timing.")) > 0

    # Concrete standard with document number is ALLOWED
    assert len(profile.weak_words("The gateway behaves as required by ISO 26262.")) == 0
    assert len(profile.weak_words("The bus behaves as required by SAE J1939-21.")) == 0
    assert len(profile.weak_words("Security behaves as required by UN ECE R155.")) == 0


def test_batch_k_prefixed_xml_namespaces_signal_checked(tmp_path):
    """Batch K finding 5: prefixed XML namespaces (xmlns:v / v:testcase) do not break parsing; misspelt signals caught."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    vtt = tmp_path / "prefixed.vtt"
    vtt.write_text(
        """<testunit xmlns:v="http://www.vector-informatik.de/vTESTstudio/TestDesign">
  <v:testcase name="NamespaceCase">
    <v:teststep signal="EngineSpd">100</v:teststep>
  </v:testcase>
</testunit>""",
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(vtt)
    assert len(units) == 1
    assert units[0].name == "NamespaceCase"

    findings, _ = check_tests(units, db, {})
    # Misspelt signal EngineSpd (instead of EngineSpeed) must be caught
    unknown = [f for f in findings if f["category"] == "unknown_signal"]
    assert len(unknown) == 1
    assert unknown[0]["evidence"] == "EngineSpd"


def test_batch_k_xml_silent_pass_fallback_to_line_matching(tmp_path):
    """Batch K finding 6: unrecognized XML step vocabulary falls back to line matching and catches out-of-range value."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    vtt = tmp_path / "custom_steps.vtt"
    vtt.write_text(
        """<testunit>
  <testcase name="CustomStepVocab">
    <set sig="EngineSpeed">9500</set>
  </testcase>
</testunit>""",
        encoding="utf-8",
    )

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    units = split_tests(vtt)
    findings, _ = check_tests(units, db, {})
    # Value 9500 exceeds max 8000 -> out_of_range
    oor = [f for f in findings if f["category"] == "out_of_range"]
    assert len(oor) == 1
    assert oor[0]["evidence"] == "9500"


def test_batch_k_docs_and_tradeoffs():
    """Batch K findings 7, 8, 11: docs accuracy and J1939 TP length trade-off documentation."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    anvil_review = (root / "docs" / "wiki" / "Anvil-Review.md").read_text(encoding="utf-8")
    assert "both set to 1" not in anvil_review
    assert "EDP=1, DP=0" in anvil_review
    assert "lengths from 9 to 1785 bytes are accepted as declared multi-packet" in anvil_review

    checks_ref = (root / "docs" / "wiki" / "Checks-reference.md").read_text(encoding="utf-8")
    assert "lengths between 9 and 1785 bytes are accepted as declared multi-packet" in checks_ref

    team_server = (root / "docs" / "wiki" / "Team-server.md").read_text(encoding="utf-8")
    assert "non-metadata link-local addresses" in team_server


def test_batch_l_vteststudio_unknown_step_tags(tmp_path):
    """Batch L finding 7: XML unknown step tags with misspelt signals report unknown_signal and avoid false no_setup."""
    from harness.anvil.dbc import CanDb, Message, Signal
    from harness.outside import check_tests, split_tests

    sig = Signal("EngineSpeed", "EEC1", "rpm", 0.0, 8000.0, 0.125, {}, cluster_receives=False)
    msg = Message("EEC1", 0x0CF00400, 8, True, ["EngineSpeed"])
    db = CanDb("truck.dbc", "sha", "ICX", {"EEC1": msg}, {"EngineSpeed": sig})

    # Case 1: Misspelt signal in unknown step tag (<stimulate channel="EngineSpeeed">)
    # Must flag unknown_signal for EngineSpeeed and NOT flag false no_setup
    vtt1 = tmp_path / "stimulate_typo.vtt"
    vtt1.write_text(
        """<testunit>
  <testcase name="StimTypo">
    <stimulate channel="EngineSpeeed">9500</stimulate>
    <check signal="EngineSpeed">100</check>
  </testcase>
</testunit>""",
        encoding="utf-8",
    )
    units1 = split_tests(vtt1)
    findings1, _ = check_tests(units1, db, {})
    unknown1 = [f for f in findings1 if f["category"] == "unknown_signal"]
    assert len(unknown1) == 1
    assert unknown1[0]["evidence"] == "EngineSpeeed"
    assert not any(f["category"] == "no_setup" for f in findings1)

    # Case 2: Single-line unknown tag with valid signal (<stimulate channel="EngineSpeed">)
    # Must NOT flag false no_setup
    vtt2 = tmp_path / "single_line_stim.vtt"
    vtt2.write_text(
        '<testunit><testcase name="SingleLine"><stimulate channel="EngineSpeed">9500</stimulate><check signal="EngineSpeed">100</check></testcase></testunit>',
        encoding="utf-8",
    )
    units2 = split_tests(vtt2)
    findings2, _ = check_tests(units2, db, {})
    assert not any(f["category"] == "no_setup" for f in findings2)

    # Case 3: Test with check but no setup steps must still report real no_setup
    vtt3 = tmp_path / "real_no_setup.vtt"
    vtt3.write_text(
        """<testunit>
  <testcase name="NoSetupCase">
    <check signal="EngineSpeed">100</check>
  </testcase>
</testunit>""",
        encoding="utf-8",
    )
    units3 = split_tests(vtt3)
    findings3, _ = check_tests(units3, db, {})
    assert any(f["category"] == "no_setup" for f in findings3)


