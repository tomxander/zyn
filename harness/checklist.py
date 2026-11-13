"""Anvil Review findings as a confirmation checklist in the layout the public Automotive
Engineering Suite uses (Title, Checklist, Findings, Dashboard, Signoff tabs; FC / LC / PC /
NO ratings), so people already using that suite can put Zyn in as the reviewer.

The check IDs and the sorting into code, AI and person checks are in
docs/07-check-catalogue.md. Rules here:

- A check is rated only when a Zyn code check ran for it. Every other check is "NA" with
  the reason (needs a person, not built yet, not applicable). Nothing is rated by default.
- Ratings use the ISO/IEC 33020 scale that ASPICE assessments use, over the share of tests
  that meet the check: above 85 % FC, above 50 % LC, above 15 % PC, else NO.
- A test fails a check when it has a confirmed or an undecided finding of a mapped kind.
  Dismissed findings do not count. While any finding is undecided the rating is marked
  provisional.
- CAN database checks are rated FC when no finding of that kind exists, else NO.
"""

from __future__ import annotations

from pathlib import Path

from harness import PROTOTYPE_LABEL

# (ID, measure, Zyn categories or a coverage key, note). Categories are per-test findings.
TEST_CHECKS: list[tuple[str, str, tuple[str, ...] | str | None, str]] = [
    ("TC001", "All test cases have unique IDs", ("duplicate_name",), ""),
    ("TC002", "Titles are descriptive and unambiguous", None, "Needs a person."),
    ("TC003", "Preconditions defined for each test case", ("no_setup",), ""),
    ("TC004", "Inputs specified with valid signals and ranges",
     ("unknown_signal", "out_of_range"), "Against the CAN database."),
    ("TC005", "Expected outputs defined", ("no_check",), ""),
    ("TC006", "Pass/fail criteria are measurable", ("no_tolerance",),
     "In part: only exact comparisons on scaled signals are checked."),
    ("TC007", "Each test case traces to at least one requirement", ("no_requirement",), ""),
    ("TC008", "Test references point to real requirements", ("unknown_requirement",), ""),
    ("TC009", "Requirement coverage (no orphan requirements)", "requirements", ""),
    ("TC010", "Test coverage (no orphan tests)", ("no_requirement",), ""),
    ("TC011", "Test level allocated", None, "Needs a person."),
    ("TC012", "Component or subsystem allocation documented", None, "Needs a person."),
    ("TC013", "Automation status recorded", None,
     "Not applicable: Anvil Review reads automated tests only."),
    ("TC014", "Automated test tool specified", None, "Needs a person."),
    ("TC015", "Automation date populated", None, "Needs a person."),
    ("TC016", "Execution priority assigned", None, "Needs a person."),
    ("TC017", "Execution sequence provided", None, "Needs a person."),
    ("TC018", "Rationale for high-priority cases", None, "Needs a person."),
    ("TC019", "System state set up before checking", ("no_setup",), ""),
    ("TC020", "Input boundary values covered (min, max, nominal)", "boundaries", ""),
    ("TC021", "Error and edge cases included", None,
     "Not checked: needs the AI reviewer, not built for tests yet."),
    ("TC022", "Tolerances specified", ("no_tolerance",), ""),
    ("TC023", "Verification method linked to each test case", None, "Needs a person."),
    ("TC024", "No conflicting or duplicate test cases", ("duplicate_test",), ""),
    ("TC025", "Test case count documented", "count", ""),
    ("TC026", "Automation ratio target specified", None, "Needs a person."),
    ("TC027", "Document control and version management", None,
     "Not rated: applies to the catalogue document. Zyn records the sha256 of every input."),
    ("TC028", "Traceability report available", None,
     "Not rated: Zyn's evidence report is that report."),
]

DBC_CHECKS: list[tuple[str, str, tuple[str, ...]]] = [
    ("TSA-01", "Message IDs are unique", ("duplicate_frame_id",)),
    ("TSA-02", "Message lengths are valid", ("invalid_length",)),
    ("TSA-03", "All signals fit within the message", ("outside_frame",)),
    ("TSA-04", "No signal bit overlap within messages", ("signal_overlap",)),
    ("TSA-05", "Min and max defined", ("range_missing",)),
    ("TSA-06", "Multiplexer references defined", ("mux_undefined",)),
    ("TSA-09/10", "Senders and receivers are defined nodes", ("unknown_node",)),
    ("TSA-11/12", "Byte order and sign are valid", ("bad_encoding",)),
    ("TSA-13", "Min and max are sensible", ("range_inverted", "range_unreachable")),
]

RATINGS = ("FC", "LC", "PC", "NO", "NA")


def rate(share: float) -> str:
    return "FC" if share > 0.85 else "LC" if share > 0.5 else "PC" if share > 0.15 else "NO"


def build(audit, run_id: str) -> dict:
    """Rows for the checklist: {checklist: [...], findings: [...], counts: {...}}."""
    from harness.sift.check import finding_rows

    meta = audit.get_item(f"SET-{run_id}")["payload"]
    if meta.get("kind") != "tests":
        raise ValueError("The checklist export is for Anvil Review runs.")
    cov = meta.get("coverage") or {}
    dbc_name = meta.get("dbc")
    tests = [i["payload"]["ext_id"] for i in audit.list_items(run_id, "imported_requirement")
             if (i["payload"].get("attrs") or {}).get("kind") != "dbc"]
    rows = [r for r in finding_rows(audit, run_id) if r["status"] != "dismissed"]
    open_n = sum(1 for r in rows if r["status"] == "open")

    out = []

    def row(cid, measure, rating, evidence, note="", provisional=False):
        out.append({"id": cid, "measure": measure, "rating": rating, "evidence": evidence,
                    "note": note, "provisional": provisional})

    for cid, measure, how, note in TEST_CHECKS:
        if how is None:
            row(cid, measure, "NA", "", note)
        elif how == "count":
            row(cid, measure, "FC", f"{len(tests)} tests read", note)
        elif how == "requirements":
            if not cov.get("requirements"):
                row(cid, measure, "NA", "", "No requirement set given.")
            else:
                share = cov["tested"] / cov["requirements"]
                row(cid, measure, rate(share),
                    f"{cov['tested']} of {cov['requirements']} requirements referenced by a "
                    f"test" + (f"; none for {', '.join(cov['untested'])}"
                               if cov["untested"] else ""), note)
        elif how == "boundaries":
            n = cov.get("boundary_signals") or 0
            if not n:
                row(cid, measure, "NA", "", "No ranged input signal is set by the tests.")
            else:
                gaps = cov.get("boundaries") or []
                row(cid, measure, rate((n - len(gaps)) / n),
                    f"{n - len(gaps)} of {n} input signals set at min, max and a value inside"
                    + (f"; gaps: {', '.join(g['signal'] for g in gaps)}" if gaps else ""),
                    note)
        else:
            hit = [r for r in rows if r["category"] in how and r["req_id"] in tests]
            failing = {r["req_id"] for r in hit}
            if (cid in ("TC007", "TC008", "TC010")) and not cov.get("requirements"):
                row(cid, measure, "NA", "", "No requirement set given.")
                continue
            share = (len(tests) - len(failing)) / len(tests) if tests else 0.0
            ev = (f"{len(tests) - len(failing)} of {len(tests)} tests meet it"
                  + (f"; not: {', '.join(sorted(failing))}" if failing else ""))
            row(cid, measure, rate(share), ev, note,
                provisional=any(r["status"] == "open" for r in hit))
    for cid, measure, cats in DBC_CHECKS:
        hit = [r for r in rows if r["category"] in cats and r["req_id"] == dbc_name]
        row(cid, measure, "NO" if hit else "FC",
            (f"{len(hit)} finding(s): {', '.join(sorted({r.get('subject') or r['evidence'] for r in hit}))}"
             if hit else f"No finding in {dbc_name}"), "CAN database check.",
            provisional=any(r["status"] == "open" for r in hit))
    counts = {k: sum(1 for r in out if r["rating"] == k) for k in RATINGS}
    return {"checklist": out, "findings": rows, "counts": counts, "open": open_n,
            "tests": len(tests), "meta": meta}


def write(audit, run_id: str, path: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    data = build(audit, run_id)
    meta = data["meta"]
    bold = Font(bold=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Title"
    for line in [
        "Confirmation checklist: test case catalogue",
        f"{PROTOTYPE_LABEL} Anvil Review run {run_id}",
        f"Tests: {meta.get('filename')}",
        f"CAN database: {meta.get('dbc')}",
        f"Requirement set: {meta.get('requirement_set') or 'none'}",
        ("Ratings come from Zyn code checks only. NA means Zyn did not check it; it is not a "
         "pass."),
        (f"Provisional: {data['open']} finding(s) not decided by a person yet."
         if data["open"] else "Every finding has been decided by a person."),
    ]:
        ws.append([line])
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 100

    ws = wb.create_sheet("Checklist")
    ws.append(["Check", "Measure", "Rating", "Provisional", "Evidence", "Note"])
    for c in ws[1]:
        c.font = bold
    for r in data["checklist"]:
        ws.append([r["id"], r["measure"], r["rating"], "yes" if r["provisional"] else "",
                   r["evidence"], r["note"]])
    for col, w in zip("ABCDEF", (10, 50, 8, 12, 70, 50), strict=True):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"

    ws = wb.create_sheet("Findings")
    ws.append(["Test or file", "Finding", "Status", "Quoted words", "Explanation",
               "Question for author", "Decided by"])
    for c in ws[1]:
        c.font = bold
    for r in data["findings"]:
        ws.append([r["req_id"], r["category"], r["status"], r["evidence"], r["explanation"],
                   r["question_for_author"], r["decided_by"]])
    ws.freeze_panes = "A2"

    ws = wb.create_sheet("Dashboard")
    ws.append(["Rating", "Checks"])
    for c in ws[1]:
        c.font = bold
    for k in RATINGS:
        ws.append([k, data["counts"][k]])
    ws.append([])
    ws.append([("FC fully, LC largely, PC partly, NO not met (ISO/IEC 33020 scale). "
                "NA: not checked by Zyn.")])

    ws = wb.create_sheet("Signoff")
    for line in ["Reviewed by:", "Date:", "Decision:", "",
                 ("A person signs this checklist. Zyn's ratings are evidence for that "
                  "decision, not the decision.")]:
        ws.append([line])
    ws.column_dimensions["A"].width = 90
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
