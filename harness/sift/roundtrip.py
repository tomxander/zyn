"""ReqIF round-trip: send Sift Review results back to the requirements tool.

When the set came in as ReqIF and the original file is still there unchanged, Zyn writes a
copy of that file with two attributes added to every requirement, "Zyn review" (pass, fail,
warn, broken) and "Zyn findings" (each finding, its state and who decided). Identifiers,
types, hierarchy and every other attribute stay as they were, so DOORS Next, Polarion or
Codebeamer can import it as an update of the same objects.

Otherwise (CSV or Excel input, or the original file is gone or changed) Zyn writes a fresh
ReqIF with ID, text, heading and the two review attributes.

Either way the file is read back with Zyn's own importer to confirm every requirement
survives with its ID and text.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT

NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
ET.register_namespace("", NS)
ET.register_namespace("xhtml", "http://www.w3.org/1999/xhtml")
REVIEW, FINDINGS = "Zyn review", "Zyn findings"


def _q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def review_rows(audit: AuditStore, run_id: str) -> list[dict]:
    from harness.evidence import _check_rows

    rows = []
    for r in _check_rows(audit, run_id):
        d = r["decision"]
        rows.append({"id": r["id"], "text": r["title"], "verdict": r["verdict"],
                     "findings": "; ".join(r["checks"]) or "none",
                     "decided": f"{d['decision']} by {d['by']}" if d else ""})
    return rows


def _augment(src: Path, rows: dict[str, dict], ident_to_id: dict[str, str]) -> bytes:
    tree = ET.parse(src)
    root = tree.getroot()
    content = root.find(f"{_q('CORE-CONTENT')}/{_q('REQ-IF-CONTENT')}")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    dts = content.find(_q("DATATYPES"))
    ET.SubElement(dts, _q("DATATYPE-DEFINITION-STRING"),
                  {"IDENTIFIER": "DT-ZYN-STRING", "LONG-NAME": "Zyn string",
                   "LAST-CHANGE": now, "MAX-LENGTH": "10000"})
    defs = {}
    for sot in content.iter(_q("SPEC-OBJECT-TYPE")):
        attrs = sot.find(_q("SPEC-ATTRIBUTES"))
        if attrs is None:
            attrs = ET.SubElement(sot, _q("SPEC-ATTRIBUTES"))
        existing = {a.get("LONG-NAME"): a.get("IDENTIFIER") for a in attrs}
        for name in (REVIEW, FINDINGS):
            if name in existing:  # reviewed before: reuse the attribute, replace its values
                defs[(sot.get("IDENTIFIER"), name)] = existing[name]
                continue
            aid = f"AD-ZYN-{name.split()[1].upper()}-{sot.get('IDENTIFIER')}"
            ad = ET.SubElement(attrs, _q("ATTRIBUTE-DEFINITION-STRING"),
                               {"IDENTIFIER": aid, "LONG-NAME": name, "LAST-CHANGE": now})
            t = ET.SubElement(ad, _q("TYPE"))
            ET.SubElement(t, _q("DATATYPE-DEFINITION-STRING-REF")).text = "DT-ZYN-STRING"
            defs[(sot.get("IDENTIFIER"), name)] = aid
    ours = set(defs.values())
    for obj in content.iter(_q("SPEC-OBJECT")):
        ext = ident_to_id.get(obj.get("IDENTIFIER"))
        row = rows.get(ext) if ext else None
        if row is None:
            continue
        sot = obj.find(f"{_q('TYPE')}/{_q('SPEC-OBJECT-TYPE-REF')}").text
        values = obj.find(_q("VALUES"))
        if values is None:
            values = ET.SubElement(obj, _q("VALUES"))
        for old in list(values):
            ref = old.find(f"{_q('DEFINITION')}/{_q('ATTRIBUTE-DEFINITION-STRING-REF')}")
            if ref is not None and ref.text in ours:
                values.remove(old)
        for name, val in ((REVIEW, row["verdict"]), (FINDINGS, row["findings"])):
            av = ET.SubElement(values, _q("ATTRIBUTE-VALUE-STRING"), {"THE-VALUE": val})
            d = ET.SubElement(av, _q("DEFINITION"))
            ET.SubElement(d, _q("ATTRIBUTE-DEFINITION-STRING-REF")).text = defs[(sot, name)]
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def export_reqif(audit: AuditStore, run_id: str, actor: str,
                 out_dir: Path | None = None) -> dict:
    from harness.sift.export import _reqif
    from harness.sift.importer import load_requirement_set

    meta = audit.get_item(f"SET-{run_id}")["payload"]
    rows = review_rows(audit, run_id)
    by_id = {r["id"]: r for r in rows}
    out = out_dir or PROJECT_ROOT / "runs" / "exports" / run_id
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "reviewed.reqif"
    src = Path(meta.get("path") or "")
    in_place = (meta.get("source_format") == "reqif" and src.is_file()
                and hashlib.sha256(src.read_bytes()).hexdigest() == meta["sha256"])
    if in_place:
        idents = {}
        for it in audit.list_items(run_id, "imported_requirement"):
            ident = it["payload"]["attrs"].get("ReqIF identifier")
            if ident:
                idents[ident] = it["payload"]["ext_id"]
        dest.write_bytes(_augment(src, by_id, idents))
        mode = "original file with two attributes added"
    else:
        heads = {it["payload"]["ext_id"]: it["payload"].get("heading", "")
                 for it in audit.list_items(run_id, "imported_requirement")}
        cols = [("id", "ID"), ("text", "Text"), ("heading", "Heading"),
                ("verdict", REVIEW), ("findings", FINDINGS), ("decided", "Zyn decided")]
        dest.write_text(_reqif([{**r, "heading": heads.get(r["id"], "")} for r in rows],
                               meta["filename"], run_id, cols), encoding="utf-8")
        mode = "new ReqIF (the original was not ReqIF or is not available unchanged)"
    back = load_requirement_set(dest)
    got = {r.ext_id: r for r in back.requirements}
    lost = [r["id"] for r in rows if r["id"] not in got]
    changed = [r["id"] for r in rows if r["id"] in got
               and " ".join(got[r["id"]].text.split()) != " ".join(r["text"].split())]
    review_ok = all(got[r["id"]].attrs.get(REVIEW) == r["verdict"] for r in rows
                    if r["id"] in got)
    res = {"file": str(dest), "mode": mode, "requirements": len(rows),
           "roundtrip": {"lost": lost, "text_changed": changed, "review_attribute": review_ok}}
    audit.log_event(actor, "exported", run_id=run_id, object_type="reqif",
                    detail={**res, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
    return res
