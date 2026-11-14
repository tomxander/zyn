"""ReqIF round-trip: Sift Review results go back into the original ReqIF file."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from harness.sift import check
from harness.sift.export import _reqif
from harness.sift.importer import load_requirement_set
from harness.sift.roundtrip import FINDINGS, NS, REVIEW
from tests.test_check import _csv

FOREIGN = [("id", "Object Identifier"), ("text", "Object Text"), ("owner", "Owner")]
ROWS = [{"id": "DNG-101", "text": "The gauge shall update quickly.", "owner": "Ana"},
        {"id": "DNG-102", "text": "The low-fuel telltale shall be lit below 10 percent.",
         "owner": "Ben"}]


def _foreign_reqif(tmp_path):
    p = tmp_path / "from_doors.reqif"
    p.write_text(_reqif(ROWS, "Cluster SRS", "doors", FOREIGN), encoding="utf-8")
    return p


def test_review_goes_back_into_the_original_reqif(cfg, audit, tmp_path):
    src = _foreign_reqif(tmp_path)
    run = check.start(cfg, audit, src).run_id
    fid = next(f["item_id"] for f in audit.list_items(run, "finding")
               if f["payload"]["req_id"] == "DNG-101")
    audit.decide(fid, "approved", "Tom")
    res = check.export_findings(audit, run, "Tom", tmp_path / "out")
    out = res["files"]["reqif"]
    back = {r.ext_id: r for r in load_requirement_set(out).requirements}
    assert set(back) == {"DNG-101", "DNG-102"}
    assert back["DNG-101"].attrs[REVIEW] == "fail" and "quickly" in back["DNG-101"].attrs[FINDINGS]
    assert back["DNG-102"].attrs[REVIEW] == "no findings"
    assert back["DNG-101"].attrs["Owner"] == "Ana"  # untouched attributes survive
    orig = {o.get("IDENTIFIER") for o in ET.parse(src).getroot().iter(f"{{{NS}}}SPEC-OBJECT")}
    new = {o.get("IDENTIFIER") for o in ET.parse(out).getroot().iter(f"{{{NS}}}SPEC-OBJECT")}
    assert orig == new  # same objects, so the tool imports it as an update


def test_reviewing_the_reviewed_file_again_does_not_duplicate_attributes(cfg, audit, tmp_path):
    src = _foreign_reqif(tmp_path)
    run = check.start(cfg, audit, src).run_id
    first = check.export_findings(audit, run, "Tom", tmp_path / "a")["files"]["reqif"]
    run2 = check.start(cfg, audit, first).run_id
    second = check.export_findings(audit, run2, "Tom", tmp_path / "b")["files"]["reqif"]
    root = ET.parse(second).getroot()
    names = [a.get("LONG-NAME") for a in root.iter(f"{{{NS}}}ATTRIBUTE-DEFINITION-STRING")]
    assert names.count(REVIEW) == 1 and names.count(FINDINGS) == 1
    obj = next(root.iter(f"{{{NS}}}SPEC-OBJECT"))
    assert len(obj.find(f"{{{NS}}}VALUES")) == 5  # 3 original + 2 review values


def test_csv_input_gets_a_fresh_reqif(cfg, audit, tmp_path):
    run = check.start(cfg, audit, _csv(tmp_path)).run_id
    res = check.export_findings(audit, run, "Tom", tmp_path / "out")
    back = load_requirement_set(res["files"]["reqif"])
    assert [r.ext_id for r in back.requirements] == ["R1", "R2", "R3", "R4", "R4"]
    ev = [e for e in audit.events(run_id=run) if e["object_type"] == "reqif"][-1]
    assert ev["detail"]["mode"].startswith("new ReqIF")
    assert ev["detail"]["roundtrip"]["lost"] == [] and ev["detail"]["roundtrip"][
        "review_attribute"]
