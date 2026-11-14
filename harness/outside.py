"""Checker mode: code checks on requirements and tests that another tool or model produced.

Zyn does not need to have generated the work to check it.

Requirements against their source (Sift Review with a source document):
- ungrounded:      no sentence in the source matches the requirement closely enough
- invented_value:  numbers in the requirement that are not in the matched source sentence
                   or its section
- modal_changed:   the requirement's modal verb differs from the source's ("should" made
                   "shall")

Tests against a CAN database and a requirement set (Anvil Review):
- unknown_signal:    a name that is close to, but not, a DBC signal or message (a typo or an
                     invented signal), or a quoted name used as a signal that the DBC lacks
- out_of_range:      a number next to a signal that is outside the signal's DBC range
- value_not_traced:  a number used with a signal that is not in the requirement the test
                     refers to (nor the signal's own limits)
- no_requirement:    the test refers to no requirement ID from the set
- unknown_requirement: the test refers to a requirement ID the set does not have
- no_tolerance:      an exact equality on a scaled signal (resolution below 1) with no
                     tolerance stated
- no_setup:          the test checks a signal but sets none first, so its result depends on
                     what ran before
- duplicate_test:    the same code as an earlier test (steps, values and checks), apart
                     from its name, docstring and comments
- no_check:          the test sets signals but checks none, so it cannot fail
- duplicate_name:    two tests share a name, so results and findings cannot tell them apart
The DBC itself is checked first (harness.anvil.dbc_check); its findings sit on a row named
after the file. Coverage, listed not decided: requirements no test refers to, input signals
never set at their DBC minimum, maximum or a value inside, and tests that name no DBC signal
(nothing for code to check, reported as skipped, never as passed).

All checks are deterministic and conservative heuristics over text: they read any language
(pytest, CAPL, Robot Framework, plain steps) without parsing it. A finding is a question for
a person, not a verdict.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from harness.anvil.dbc import CanDb
from harness.sift import checks

_WORDS = re.compile(r"[a-z0-9][a-z0-9.'-]*")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+")
_NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
_IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
_QUOTED = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]{2,})[\"']")
_SIGNAL_CONTEXT = re.compile(r"signal|sig\b|set|expect|check|read|write|get|\$", re.IGNORECASE)
_TIME_AFTER = re.compile(r"^\s*(ms|s|sec|seconds|_ms|millis)", re.IGNORECASE)
# Lines that state an expected result, as opposed to ones that only set an input.
_EXPECT = re.compile(r"assert|expect|verify|check|==|!=|<=|>=|testStepPass|testStepFail|"
                     r"Should Be", re.IGNORECASE)
_EQUALS = re.compile(r"==|Should Be Equal(?! As Numbers)|testStepPass", re.IGNORECASE)
_TOLERANCE = re.compile(r"approx|isclose|\babs\s*=|\brel\s*=|tol|\u00b1|\+/-|within|"
                        r"precision|delta|margin|As Numbers", re.IGNORECASE)

# Share of the requirement's words found in one source sentence (lightly stemmed) needed to
# call it the requirement's origin. Containment, not overlap, so a requirement split out of a
# longer sentence or table row still matches.
MATCH_MIN = 0.5
CLOSE_MATCH = 0.5  # at or above this the requirement is taken from that one sentence
_STOP = {"the", "and", "shall", "should", "must", "will", "may", "when", "with", "for",
         "from", "that", "this", "are", "its", "into", "then", "after", "while", "not"}


# ---- requirements against their source ---------------------------------------------------


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in _WORDS.findall(checks.normalise(text))
            if len(w) > 2 and w not in _STOP}


def source_sentences(doc) -> list[dict]:
    """Sentences of a loaded SourceDocument, with their section for context."""
    out = []
    for sec in doc.sections:
        for s in _SENT.split(sec.text):
            s = s.strip(" -*#|")
            if len(_tokens(s)) >= 3:
                out.append({"text": s, "section": sec.number or sec.heading,
                            "section_text": sec.text, "page": sec.page})
    return out


def best_match(text: str, sentences: list[dict]) -> tuple[dict | None, float]:
    t = _tokens(text)
    best, score = None, 0.0
    for s in sentences:
        st = _tokens(s["text"])
        if not st:
            continue
        sc = len(t & st) / len(t) if t else 0.0
        if sc > score:
            best, score = s, sc
    return best, round(score, 3)


def ground_findings(reqs: list[dict], doc, profile=None) -> tuple[list[dict], dict]:
    """reqs: [{ext_id, text, quote?}]. Returns findings and, per requirement, its match."""
    sentences = source_sentences(doc)
    on = (lambda c: profile.on(c)) if profile is not None else (lambda c: True)
    out, matches = [], {}

    def add(r, cat, evidence, why, question):
        out.append({"req_id": r["ext_id"], "category": cat, "evidence": evidence,
                    "explanation": why, "question_for_author": question, "related_ids": []})

    for r in reqs:
        quote = (r.get("quote") or "").strip()
        if quote and checks.is_grounded(quote, doc.markdown):
            m, score = best_match(quote, sentences)
            m = m or {"text": quote, "section": None, "section_text": quote, "page": None}
            score = 1.0
        else:
            m, score = best_match(r["text"], sentences)
        matches[r["ext_id"]] = ({"sentence": m["text"], "section": m["section"],
                                 "page": m["page"], "score": score} if m else None)
        if m is None or score < MATCH_MIN:
            if on("ungrounded"):
                add(r, "ungrounded", " ".join(r["text"].split()[:6]),
                    f"No sentence in {doc.filename} matches this requirement (best match "
                    f"{score:.0%}). It may be invented, merged from several places or "
                    "heavily reworded.", "Where in the source does this requirement come from?")
            continue
        src = m["text"] + " " + m["section_text"]
        new = checks.new_numbers(r["text"], src)
        # A close match to one sentence that carries its own numbers: the requirement's
        # numbers must come from that sentence, not from elsewhere in the section (a value
        # swapped for another value from a neighbouring sentence).
        swapped = ([] if new or score < CLOSE_MATCH or not checks.new_numbers(m["text"], "")
                   else checks.new_numbers(r["text"], m["text"]))
        if (new or swapped) and on("invented_value"):
            vals = new or swapped
            where = ("the matching source sentence or its section" if new else
                     "the matching source sentence (it appears elsewhere in the section)")
            add(r, "invented_value", vals[0],
                f"{', '.join(vals)} not in {where} ({m['section']}).",
                f"Where does {vals[0]} come from?")
        if checks.modal_changed(m["text"], r["text"]) and on("modal_changed"):
            add(r, "modal_changed", checks.modal_of(r["text"]) or "",
                f"The source says '{checks.modal_of(m['text'])}', the requirement says "
                f"'{checks.modal_of(r['text'])}'.", "Which obligation does the source intend?")
    return out, matches


# ---- tests against the DBC and the requirement set ---------------------------------------


@dataclass
class Unit:
    name: str
    file: str
    text: str
    order: int


_PY_TEST = re.compile(r"^(?:async\s+)?def\s+(test\w*)\s*\(", re.MULTILINE)
_CAPL_TEST = re.compile(r"^\s*testcase\s+(\w+)\s*\(", re.MULTILINE)
_ROBOT_SECTION = re.compile(r"^\*{3}\s*test cases?\s*\*{3}", re.IGNORECASE | re.MULTILINE)
_VTEST_CASE = re.compile(
    r"""<\s*(?:testcase|testtablecase|testcasedefinition)\b[^>]*(?:name|title)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def _parse_xml_safely(raw_bytes: bytes, filename: str):
    import xml.etree.ElementTree as ET
    from xml.parsers import expat

    parser = expat.ParserCreate()
    tb = ET.TreeBuilder()
    parser.StartElementHandler = tb.start
    parser.EndElementHandler = tb.end
    parser.CharacterDataHandler = tb.data

    def on_doctype(*args):
        raise ValueError(f"{filename} contains forbidden DOCTYPE declaration.")

    def on_entity(*args):
        raise ValueError(f"{filename} contains forbidden ENTITY declaration.")

    parser.StartDoctypeDeclHandler = on_doctype
    parser.EntityDeclHandler = on_entity
    try:
        parser.Parse(raw_bytes, True)
    except expat.ExpatError as e:
        raise ValueError(f"{filename} is not valid XML: {e}") from e
    return tb.close()


def _local_tag(elem) -> str:
    if not getattr(elem, "tag", None):
        return ""
    tag = elem.tag
    if "}" in tag:
        tag = tag.split("}")[-1]
    if ":" in tag:
        tag = tag.split(":")[-1]
    return tag.lower()


def _local_attr(elem, key: str) -> str | None:
    target = key.lower()
    for k, v in elem.attrib.items():
        attr_name = k
        if "}" in attr_name:
            attr_name = attr_name.split("}")[-1]
        if ":" in attr_name:
            attr_name = attr_name.split(":")[-1]
        if attr_name.lower() == target:
            return v
    return None


def _find_local_child(elem, tag: str):
    target = tag.lower()
    for child in elem:
        if _local_tag(child) == target:
            return child
    return None


def split_tests(path: Path, start: int = 0) -> list[Unit]:
    """One unit per test: pytest functions, CAPL testcases, Robot Framework test cases,
    vTESTstudio XML testcases, else rows of a CSV/JSON/text file are kept whole as one unit."""
    suffix = path.suffix.lower()

    if suffix in (".vtt", ".vts", ".vxt"):
        import copy
        import xml.etree.ElementTree as ET

        root = _parse_xml_safely(path.read_bytes(), path.name)

        tc_tags = ("testcase", "testtablecase", "testcasedefinition")
        tc_elements = [e for e in root.iter() if _local_tag(e) in tc_tags]

        if not tc_elements:
            raise ValueError(
                f"{path.name} contains no recognized test cases "
                "(expected <testcase>, <testtablecase>, or <testcasedefinition>)."
            )

        units = []
        for i, elem in enumerate(tc_elements):
            tc_name = _local_attr(elem, "name")
            if not tc_name:
                tc_name = _local_attr(elem, "title")
            if not tc_name:
                title_elem = _find_local_child(elem, "title")
                if title_elem is not None and title_elem.text:
                    tc_name = title_elem.text.strip()
            if not tc_name:
                name_elem = _find_local_child(elem, "name")
                if name_elem is not None and name_elem.text:
                    tc_name = name_elem.text.strip()
            if not tc_name:
                tc_name = _local_attr(elem, "id")
            if not tc_name:
                tc_name = f"test_{i + 1}"

            # Check steps under innermost test case: remove descendant test cases so steps are not checked twice
            elem_copy = copy.deepcopy(elem)
            for child in list(elem_copy.iter()):
                for sub in list(child):
                    if _local_tag(sub) in tc_tags:
                        child.remove(sub)

            # Carry namespace declarations from root into fragment so prefixed namespaces are bound (Finding 5)
            root_xmlns = {k: v for k, v in root.attrib.items() if k.startswith("xmlns")}
            elem_copy.attrib.update(root_xmlns)

            xml_text = ET.tostring(elem_copy, encoding="unicode")
            units.append(Unit(tc_name.strip(), path.name, xml_text.strip(), start + i))
        return units

    text = path.read_text(encoding="utf-8", errors="replace")

    spans: list[tuple[str, int]] = []
    if suffix == ".py":
        spans = [(m.group(1), m.start()) for m in _PY_TEST.finditer(text)]
    elif suffix in (".can", ".cin"):
        spans = [(m.group(1), m.start()) for m in _CAPL_TEST.finditer(text)]
    elif suffix == ".robot":
        sec = _ROBOT_SECTION.search(text)
        if sec:
            body_start = sec.end()
            nxt = re.search(r"^\*{3}", text[body_start:], re.MULTILINE)
            body_end = body_start + nxt.start() if nxt else len(text)
            spans = [(m.group(1).strip(), body_start + m.start()) for m in
                     re.finditer(r"^([^\s#].*)$", text[body_start:body_end], re.MULTILINE)]
            text = text[:body_end]
    if not spans:
        return [Unit(path.stem, path.name, text, start)]
    units = []
    for i, (name, pos) in enumerate(spans):
        end = spans[i + 1][1] if i + 1 < len(spans) else len(text)
        units.append(Unit(name, path.name, text[pos:end].rstrip(), start + i))
    return units


def _req_pattern(req_ids: list[str]) -> re.Pattern | None:
    """A pattern for IDs shaped like the set's (letters, digits and separators)."""
    if not req_ids:
        return None
    shapes = {re.sub(r"\d+", r"\\d+", re.sub(r"[A-Za-z]+", "[A-Za-z]+", re.escape(i)))
              for i in req_ids}
    return re.compile(r"\b(?:" + "|".join(sorted(shapes)) + r")\b")


def _near_requirement_value(val: float, req_text: str, resolution: float) -> bool:
    """True when val is a value of the requirement or a boundary next to one (within two
    resolution steps or 2 percent), which is how boundary tests are built."""
    for n in _NUM.findall(checks.normalise(req_text)):
        x = float(n)
        if abs(val - x) <= max(2 * (resolution or 1), 0.02 * abs(x)) + 1e-9:
            return True
    return False


def prepare(test_paths: list[Path], dbc_path: Path) -> tuple[CanDb, list[dict], list[Unit]]:
    """The database, its own findings and the non-empty test units. Raises ValueError for
    an unreadable or empty database or for test files with no tests, so empty input never
    comes back as a clean run."""
    from harness.anvil.dbc import load_dbc
    from harness.anvil.dbc_check import check_file

    dbc_found = check_file(dbc_path)
    db = load_dbc(dbc_path)
    units: list[Unit] = []
    for p in test_paths:
        units += [u for u in split_tests(Path(p)) if u.text.strip()]
    for i, u in enumerate(units):
        u.order = i
    if not units:
        raise ValueError("No tests found in " + ", ".join(Path(p).name for p in test_paths)
                         + ": the files are empty.")
    return db, dbc_found, units


def start_tests(audit, test_paths: list[Path], dbc_path: Path,
                reqset_path: Path | None = None) -> str:
    """An Anvil Review run: tests (any text format) against a DBC and a requirement set.
    Stored like a Sift Review so findings are decided, exported and carried over the same
    way. Returns the run id."""
    from harness.sift import check
    from harness.sift.importer import load_requirement_set

    db, dbc_found, units = prepare(test_paths, dbc_path)
    reqs: dict[str, str] = {}
    rs = None
    if reqset_path:
        rs = load_requirement_set(reqset_path)
        reqs = {r.ext_id: r.text for r in rs.requirements}
    found, coverage = check_tests(units, db, reqs)
    names = ", ".join(Path(p).name for p in test_paths)
    run_id = audit.start_run(TEST_WORKFLOW, note=f"{names} vs {db.filename}")
    meta = {"name": names, "filename": names, "sha256": files_sha256(
                [Path(p) for p in test_paths]),
            "source_format": "tests", "columns_used": {"tests": names, "dbc": db.filename,
                                                      "requirements": rs.filename if rs
                                                      else "none"},
            "count": len(units), "kind": "tests", "dbc": db.filename, "dbc_sha256": db.sha256,
            "requirement_set": rs.filename if rs else None, "coverage": coverage}
    audit.add_item(run_id, "requirement_set", meta, created_by="code:import",
                   item_id=f"SET-{run_id}")
    audit.log_event("code:import", "ingested", run_id=run_id, object_type="test_set",
                    detail=meta)
    for u in units:
        audit.add_item(run_id, "imported_requirement",
                       {"ext_id": u.name, "text": u.text[:4000], "heading": u.file,
                        "order": u.order, "attrs": {}},
                       created_by="code:import", item_id=f"IR-{u.order + 1:04d}@{run_id}")
    if dbc_found:
        n = len(units)
        listing = "\n".join(f"{f['subject']}: {f['category']}" for f in dbc_found)
        audit.add_item(run_id, "imported_requirement",
                       {"ext_id": db.filename, "text": f"CAN database {db.filename}\n{listing}",
                        "heading": "CAN database", "order": n, "attrs": {"kind": "dbc"}},
                       created_by="code:import", item_id=f"IR-{n + 1:04d}@{run_id}")
    check._store_findings(audit, run_id, dbc_found + found, "code", TEST_ACTOR)
    return run_id


TEST_WORKFLOW = "test-check"
TEST_ACTOR = "code:test-check"


def check_tests(units: list[Unit], db: CanDb, reqs: dict[str, str]) -> tuple[
        list[dict], dict]:
    """reqs: requirement ID -> text (may be empty). Returns findings and coverage."""
    names = {**{n: "signal" for n in db.signals}, **{n: "message" for n in db.messages}}
    lower = {n.lower(): n for n in names}
    id_pat = _req_pattern(list(reqs))
    referenced: set[str] = set()
    out = []
    no_signal: list[str] = []
    set_values: dict[str, set[float]] = {}
    first_with: dict[str, str] = {}
    names_seen: dict[str, str] = {}

    def add(u, cat, evidence, why, question):
        out.append({"req_id": u.name, "category": cat, "evidence": evidence,
                    "explanation": why, "question_for_author": question, "related_ids": []})

    for u in units:
        seen_cat: set[tuple[str, str]] = set()

        def once(cat, key, *a, _u=u, _seen=seen_cat):
            if (cat, key) not in _seen:
                _seen.add((cat, key))
                add(_u, cat, *a)

        is_xml = Path(u.file).suffix.lower() in (".vtt", ".vts", ".vxt")
        xml_checked = False
        if is_xml:
            # Build checks from parsed XML elements rather than source lines (Finding 9)
            import xml.etree.ElementTree as ET

            try:
                xml_root = _parse_xml_safely(code_only(u).encode("utf-8"), u.file)
            except Exception:  # noqa: BLE001
                try:
                    xml_root = ET.fromstring(code_only(u))
                except Exception:  # noqa: BLE001
                    xml_root = None
            if xml_root is not None:
                xml_signals_found = 0
                for elem in xml_root.iter():
                    if _local_tag(elem) in ("testcase", "testtablecase", "testcasedefinition", "testunit"):
                        continue
                    raw_sig = None
                    for attr_key in ("signal", "variable", "target", "sig", "channel", "chan"):
                        v = _local_attr(elem, attr_key)
                        if v and v.strip():
                            raw_sig = v.strip()
                            break
                    if not raw_sig:
                        for child_tag in ("signal", "variable", "target", "sig", "channel", "chan"):
                            ch = _find_local_child(elem, child_tag)
                            if ch is not None and ch.text and ch.text.strip():
                                raw_sig = ch.text.strip()
                                break
                    if not raw_sig:
                        # Check any attribute on a step-like element for candidate signal names or typos
                        for k, v in elem.attrib.items():
                            if k.lower() in ("id", "action", "value", "expected", "val", "wait", "delay", "timeout"):
                                continue
                            if v and v.strip() and (v.strip() in names or difflib.get_close_matches(v.strip(), list(names), n=1, cutoff=0.8)):
                                raw_sig = v.strip()
                                break
                    if raw_sig:
                        xml_signals_found += 1
                        if raw_sig not in names and raw_sig.lower() not in lower:
                            close = difflib.get_close_matches(raw_sig, list(names), n=1, cutoff=0.8)
                            if close and raw_sig.lower() != close[0].lower():
                                once("unknown_signal", raw_sig, raw_sig,
                                     f"'{raw_sig}' is not in the CAN database {db.filename}; the closest "
                                     f"{names[close[0]]} is {close[0]}.", f"Did the test mean {close[0]}?")
                            elif re.search(r"[A-Z0-9_]", raw_sig[1:]) or raw_sig[0].isupper():
                                once("unknown_signal", raw_sig, raw_sig,
                                     f"'{raw_sig}' is used like a signal name but is not in {db.filename}.",
                                     "Which DBC signal is this?")
                if xml_signals_found > 0:
                    xml_checked = True

        if not xml_checked:
            xml_structural = {
                "testcase", "testunit", "testtablecase", "testcasedefinition",
                "teststep", "stimulate", "channel", "signal", "value",
                u.name, u.name.lower(),
            }
            idents = {tok for tok in _IDENT.findall(u.text) if tok not in xml_structural and tok.lower() not in xml_structural}
            for tok in sorted(idents):
                if tok in names or tok.lower() in lower:
                    continue
                if not (re.search(r"[A-Z0-9_]", tok[1:]) or tok[0].isupper()):
                    continue  # a plain lowercase word, not an identifier
                close = difflib.get_close_matches(tok, list(names), n=1, cutoff=0.8)
                if close and tok.lower() != close[0].lower():
                    once("unknown_signal", tok, tok,
                         f"'{tok}' is not in the CAN database {db.filename}; the closest "
                         f"{names[close[0]]} is {close[0]}.", f"Did the test mean {close[0]}?")
            for line in u.text.splitlines():
                if not _SIGNAL_CONTEXT.search(line):
                    continue
                for q in _QUOTED.findall(line):
                    if q not in names and q.lower() not in lower and not q.lower().startswith(
                            "test") and q[0].isupper() and q not in xml_structural:
                        once("unknown_signal", q, q,
                             f"'{q}' is used like a signal name but is not in {db.filename}.",
                             "Which DBC signal is this?")
        refs = set(id_pat.findall(u.text)) if id_pat else set()
        known = {r for r in refs if r in reqs}
        referenced |= known
        for r in sorted(refs - known):
            once("unknown_requirement", r, r, f"{r} is not in the requirement set.",
                 "Which requirement does this test verify?")
        if reqs and not refs:
            once("no_requirement", "-",
                 (u.text.strip().splitlines() or ["(empty test)"])[0][:60],
                 "The test refers to no requirement ID, so it cannot be traced.",
                 "Which requirement does this test verify?")
        req_text = " ".join(reqs.get(r, "") for r in known)
        ops = _ops(u, db)
        if not ops and not any(re.search(rf"\b{re.escape(n)}\b", u.text) for n in names):
            no_signal.append(u.name)
        for kind, sname, raw, line in ops:
            sig = db.signals[sname]
            val = float(raw)
            if kind == "set":
                set_values.setdefault(sname, set()).add(val)
            if val < sig.minimum - 1e-9 or val > sig.maximum + 1e-9:
                basis = (" (the DBC gives no range; this is what its bits allow)"
                         if sig.range_from_bits else "")
                once("out_of_range", f"{sname}={raw}", raw,
                     f"{raw} is outside {sname}'s range {sig.minimum:g}..{sig.maximum:g} in "
                     f"{db.filename}{basis}.", f"What value of {sname} is intended?")
            elif (known and kind == "expect"
                  and val not in (sig.minimum, sig.maximum, 0.0, 1.0)
                  and not _near_requirement_value(val, req_text, sig.resolution)):
                once("value_not_traced", f"{sname}={raw}", raw,
                     f"{raw} (used with {sname}) is not in {', '.join(sorted(known))}.",
                     f"Where does {raw} come from: a boundary of a value in the "
                     "requirement, or an assumption to record?")
            if (kind == "expect" and _EQUALS.search(line) and not _TOLERANCE.search(line)
                    and not sig.choices and sig.resolution % 1 != 0):
                once("no_tolerance", sname, line.strip()[:80],
                     f"{sname} is compared for exact equality with {raw}, but its resolution "
                     f"is {sig.resolution:g} {sig.unit}; a measured value rarely hits it "
                     "exactly.", f"What tolerance on {sname} should the test accept?")
        expects = [o for o in ops if o[0] == "expect"]
        if ops and not expects and not _EXPECT.search(code_only(u)):
            once("no_check", "-", ops[0][3].strip()[:80],
                 f"The test sets {ops[0][1]} but checks no result, so it cannot fail.",
                 "What result should this test check?")
        if u.name in names_seen:
            once("duplicate_name", u.name, u.name,
                 f"Another test is also called {u.name} ({names_seen[u.name]}).",
                 "Which name should each test have?")
        names_seen.setdefault(u.name, u.file)
        typo = any(c == "unknown_signal" for c, _ in seen_cat)
        code = code_only(u)
        if is_xml:
            acts = [o for o in ops if o[0] == "set"]
            if not acts:
                # If XML parser didn't extract a set op (e.g. unknown tags or fallback),
                # check elements/tags for setup actions so single-line unknown tags don't false-alarm
                xml_chunks = re.findall(r"<[^>]+>[^<]*", code) or code.splitlines()
                acts = [ch for ch in xml_chunks if not _EXPECT.search(ch) and any(
                    re.search(rf"\b{re.escape(n)}\b", ch) for n in names)]
        else:
            acts = [ln for ln in code.splitlines() if not _EXPECT.search(ln) and any(
                re.search(rf"\b{re.escape(n)}\b", ln) for n in names)]
        if expects and not acts and not typo:
            once("no_setup", "-", expects[0][3].strip()[:80],
                 f"The test checks {expects[0][1]} but sets no input signal first, so its "
                 "result depends on what ran before it.",
                 "Which starting state does this test assume?")
        # Same body: every code line after the test's own name line, spacing ignored.
        body = "\n".join(" ".join(ln.split()) for ln in code.splitlines()[1:] if ln.strip())
        steps = body if ops else ""
        if steps:
            if steps in first_with:
                add(u, "duplicate_test", u.name,
                    f"Same steps, values and checks as {first_with[steps]}.",
                    f"Is this a copy of {first_with[steps]}, or should it test something "
                    "else?")
                out[-1]["related_ids"] = [first_with[steps]]
            else:
                first_with[steps] = u.name
    boundaries, considered = [], 0
    for sname, vals in sorted(set_values.items()):
        sig = db.signals[sname]
        if sig.boolean or sig.choices or sig.range_from_bits:
            continue
        considered += 1
        eps = (sig.resolution or 1) / 2
        missing = [w for w, ok in (
            ("minimum", any(abs(v - sig.minimum) <= eps for v in vals)),
            ("maximum", any(abs(v - sig.maximum) <= eps for v in vals)),
            ("a value inside", any(sig.minimum + eps < v < sig.maximum - eps for v in vals)))
            if not ok]
        if missing:
            boundaries.append({"signal": sname, "minimum": sig.minimum,
                               "maximum": sig.maximum, "values": sorted(vals),
                               "missing": missing})
    coverage = {"requirements": len(reqs), "tested": len(referenced),
                "untested": sorted(set(reqs) - referenced), "boundaries": boundaries,
                "boundary_signals": considered,
                "no_signal": no_signal}
    return out, coverage


_TRIPLE = re.compile(r'"""[\s\S]*?"""' + r"|'''[\s\S]*?'''")
_LINE_COMMENT = {".py": re.compile(r"#.*$", re.MULTILINE),
                 ".robot": re.compile(r"^\s*#.*$", re.MULTILINE),
                 ".can": re.compile(r"//.*$", re.MULTILINE),
                 ".cin": re.compile(r"//.*$", re.MULTILINE)}


def code_only(u: Unit) -> str:
    """The test without docstrings and comments, for reading its steps and checks. A
    docstring line such as "Expected: TT_LowFuel = 1" is not a check. Plain-text tests are
    kept whole: their lines are the steps."""
    suffix = Path(u.file).suffix.lower()
    text = _TRIPLE.sub("", u.text) if suffix == ".py" else u.text
    if suffix in (".can", ".cin"):
        text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    if suffix in (".vtt", ".vts", ".vxt"):
        text = re.sub(r"<!--[\s\S]*?-->", "", text)
    pat = _LINE_COMMENT.get(suffix)
    return pat.sub("", text) if pat else text


_CALL_BEFORE = re.compile(r"(\w+)\(\s*[\"']?$")
# Reads whose argument after the signal is a time, not a value: value_after, read_after,
# wait_for_signal, sample_delay and the like.
_TIMED_READ = re.compile(r"after$|wait|delay|sleep", re.IGNORECASE)
_COMPARED = re.compile(r"\)\s*(?:==|!=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)")


def _ops(u: Unit, db: CanDb) -> list[tuple[str, str, str, str]]:
    """(set | expect, signal, first number after it, line) for each signal use with a value
    in the test's code (docstrings and comments left out). Numbers followed by a time unit
    are skipped."""
    suffix = Path(u.file).suffix.lower()
    if suffix in (".vtt", ".vts", ".vxt"):
        import xml.etree.ElementTree as ET

        try:
            root = _parse_xml_safely(code_only(u).encode("utf-8"), u.file)
        except Exception:  # noqa: BLE001
            try:
                root = ET.fromstring(code_only(u))
            except Exception:  # noqa: BLE001
                root = None
        if root is not None:
            xml_ops = []
            for elem in root.iter():
                if _local_tag(elem) in ("testcase", "testtablecase", "testcasedefinition", "testunit"):
                    continue
                sname = None
                for attr_key in ("signal", "name", "target", "variable", "sig", "channel", "chan"):
                    v = _local_attr(elem, attr_key)
                    if v and v in db.signals:
                        sname = v
                        break
                if not sname:
                    for child_tag in ("signal", "name", "target", "variable", "sig", "channel", "chan"):
                        child = _find_local_child(elem, child_tag)
                        if child is not None and child.text and child.text.strip() in db.signals:
                            sname = child.text.strip()
                            break
                if not sname:
                    for v in elem.attrib.values():
                        if v and v.strip() in db.signals:
                            sname = v.strip()
                            break
                if not sname:
                    continue

                action_str = _local_attr(elem, "action") or ""
                if not action_str:
                    action_child = _find_local_child(elem, "action")
                    if action_child is not None and action_child.text:
                        action_str = action_child.text.strip()
                local_tag = _local_tag(elem)
                combined_act = f"{action_str} {local_tag}".lower()
                kind = "expect" if any(w in combined_act for w in ("check", "expect", "verify", "assert", "read")) else "set"

                # Look for value (explicitly ignoring wait, delay, timeout, cycle)
                # Check attributes, child elements, and element text alike (Finding 10)
                val_raw = None
                for val_key in ("value", "expected", "val", "targetvalue", "physvalue"):
                    v = _local_attr(elem, val_key)
                    if v is not None:
                        val_raw = v
                        break
                if val_raw is None:
                    for val_child_tag in ("value", "expected", "val", "targetvalue", "physvalue"):
                        child = _find_local_child(elem, val_child_tag)
                        if child is not None and child.text:
                            val_raw = child.text.strip()
                            break
                if val_raw is None and elem.text and elem.text.strip():
                    val_raw = elem.text.strip()

                if val_raw is not None:
                    num_match = _NUM.search(val_raw)
                    if num_match:
                        line_rep = ET.tostring(elem, encoding="unicode").strip()
                        xml_ops.append((kind, sname, num_match.group(0), line_rep))
            if xml_ops:
                return xml_ops
            # Fall back to line matching when parser finds no steps (Finding 6)

    out = []
    for line in code_only(u).splitlines():
        kind = "expect" if _EXPECT.search(line) else "set"
        for sname in [n for n in db.signals if re.search(rf"\b{re.escape(n)}\b", line)]:
            at = line.find(sname)
            after = line[at + len(sname):][:60]
            call = _CALL_BEFORE.search(line[:at])
            if call and _TIMED_READ.search(call.group(1)):
                # value_after('Speed', 130) == 52: the argument is a time; the value, if any,
                # is the one compared after the call.
                cmp = _COMPARED.search(after)
                if cmp:
                    out.append(("expect", sname, cmp.group(1), line))
                continue
            for m in _NUM.finditer(after):
                if _TIME_AFTER.match(after[m.end():]):
                    continue
                out.append((kind, sname, m.group(0), line))
                break  # first number after the signal name only
    return out


def files_sha256(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.read_bytes())
    return h.hexdigest()
