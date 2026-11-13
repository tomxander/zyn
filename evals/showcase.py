"""Showcase benchmarks: the questions engineers ask before they trust an AI engineering tool.

Each benchmark answers one finding of the practitioner research
(research/automotive-embedded-ai-practitioner-research-2026-11-13):

S1 planted  "Does it catch what AI gets wrong?" Known mistakes are planted, one at a time,
            into clean requirements, tests and CAN databases. Zyn's code checks run on each.
            Reported: share caught per kind of mistake, and flags raised on the clean
            originals (false alarms). Code only: no model, no cost, same result every run.
            Some kinds are planted on purpose although no code check targets them (a
            swapped term, a flipped boolean); they show what still needs a person.
S2 freetests "Free-written tests or a checked template?" Models write pytest tests freely for
            the 15 automatable ICX-100 requirements. The tests run on the same simulated
            cluster and against the same 48 injected faults as Zyn's template path.
            Reported per model: tests that run, tests that pass on the correct simulation,
            faults caught, and Zyn's code findings on the tests.

Run from the project root:
  python -m evals.showcase planted
  python -m evals.showcase freetests --profiles claude-haiku,claude-sonnet,claude-opus --repeat 2
  python -m evals.showcase rescore     # score stored answers again, no model calls
  python -m evals.showcase report      # gathers every result into docs/bench/showcase/showcase.json

Results describe these datasets. ICX-100 is synthetic (author-made, AI-reviewed), RTEMS and
opendbc are public. The simulated cluster is built from Zyn's approved specs, so a free test
that reads a requirement differently fails on it; that is reported, not hidden. It models only
the output the requirement is about: checks on other signals (a precondition such as
ClusterState = ACTIVE) are not judged and pass; their count is reported.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

OUT = ROOT / "docs" / "bench" / "showcase"
WORK = ROOT / "runs" / "showcase"
DATA = ROOT / "data" / "synthetic"
FORGE_RUN = "20261113-182131-30ee1c"   # template path: approved specs and generated tests
SIFT_RUN = "20261113-165443-9c129b"    # the approved requirements those specs came from


# ---------------------------------------------------------------- S1: planted mistakes ----

FABRICATED = {
    "icx": ["The cluster shall support wireless phone charging at 15 W.",
            "The cluster shall announce lane departure warnings with a voice prompt.",
            "The cluster shall download map updates over the air every 30 days.",
            "The cluster shall pair with up to five Bluetooth headsets."],
    "rtems": ["The directive shall write an entry to the persistent audit journal.",
              "The directive shall encrypt the object name before it is stored.",
              "The directive shall notify the remote debugger over the serial console.",
              "The directive shall reserve a backup stack for the calling task."],
}


def _num_change(t: str) -> str | None:
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", t)
    if not m:
        return None
    v = float(m.group(1))
    new = v * 2 if v else 7
    s = f"{new:g}"
    return t[:m.start()] + s + t[m.end():]


def _add_number(t: str) -> str:
    return re.sub(r"\.\s*$", "", t.strip()) + " within 250 ms."


def _weaken(t: str) -> str | None:
    return re.sub(r"\bshall\b", "should", t, count=1) if re.search(r"\bshall\b", t) else None


def _swap_term(t: str, terms: list[str]) -> str | None:
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", t):
            other = next((o for o in terms if o != term and o not in t), None)
            if other:
                return re.sub(rf"\b{re.escape(term)}\b", other, t, count=1)
    return None


def _req_sources() -> dict:
    """Two requirement sets with their source documents: ICX-100 (synthetic) and RTEMS
    (public). Both match their source with no grounding finding, which S1 re-checks."""
    import evals.rtems as rt
    from harness.sift.importer import load_requirement_set

    rs = load_requirement_set(DATA / "icx100_reqset.csv")
    icx = [{"ext_id": r.ext_id, "text": r.text} for r in rs.requirements]
    doc, gold = rt.render()
    WORK.mkdir(parents=True, exist_ok=True)
    rendered = WORK / "rtems_rendered.md"
    rendered.write_text(doc, encoding="utf-8")
    rtems = [{"ext_id": f"RT{i + 1:03d}", "text": g["text"]} for i, g in enumerate(gold)]
    return {"icx": {"source": DATA / "icx100_srs.md", "reqs": icx,
                    "label": "ICX-100 requirement set (synthetic, 46)"},
            "rtems": {"source": rendered, "reqs": rtems,
                      "label": "RTEMS behaviour statements (public, 110)"}}


REQ_KINDS = {
    # kind: (what, expected category or None when no code check targets it)
    "changed_number": ("A number in the requirement changed (10 becomes 20)", "invented_value"),
    "added_number": ("A timing value added that the source never gives", "invented_value"),
    "weakened_modal": ("'shall' weakened to 'should'", "modal_changed"),
    "fabricated": ("A requirement the source does not contain", "ungrounded"),
    "swapped_term": (("A signal or status name swapped for another one from the same "
                      "document"), None),
}


def planted_requirements() -> dict:
    from harness.outside import ground_findings
    from harness.sift.ingest import load_document

    out = {}
    for key, s in _req_sources().items():
        doc = load_document(s["source"])
        clean = s["reqs"]
        base, _ = ground_findings(clean, doc)
        terms = sorted({w for r in clean for w in re.findall(r"\b[A-Z][A-Za-z0-9_]{3,}\b",
                                                             r["text"])
                        if re.search(r"[A-Z].*[A-Z]|_", w)})
        mutants = []
        for i, r in enumerate(clean):
            t = r["text"]
            cand = {"changed_number": _num_change(t), "added_number": _add_number(t),
                    "weakened_modal": _weaken(t), "swapped_term": _swap_term(t, terms)}
            for kind, text in cand.items():
                if text and text != t:
                    mutants.append({"ext_id": f"{r['ext_id']}~{kind}", "text": text,
                                    "kind": kind, "original": t})
        for j, text in enumerate(FABRICATED[key]):
            mutants.append({"ext_id": f"FAB{j + 1}", "text": text, "kind": "fabricated",
                            "original": None})
        found, _ = ground_findings([{"ext_id": m["ext_id"], "text": m["text"]}
                                    for m in mutants], doc)
        by_id = defaultdict(set)
        for f in found:
            by_id[f["req_id"]].add(f["category"])
        kinds = {}
        for kind, (what, expect) in REQ_KINDS.items():
            ms = [m for m in mutants if m["kind"] == kind]
            if not ms:
                continue
            caught = [m for m in ms if (expect in by_id[m["ext_id"]] if expect
                                        else bool(by_id[m["ext_id"]]))]
            kinds[kind] = {"what": what, "expected_check": expect, "planted": len(ms),
                           "caught": len(caught),
                           "flagged_any": sum(1 for m in ms if by_id[m["ext_id"]]),
                           "example": {"before": ms[0]["original"], "after": ms[0]["text"],
                                       "flagged": sorted(by_id[ms[0]["ext_id"]])}}
        out[key] = {"label": s["label"], "clean_items": len(clean),
                    "false_alarms": len({f["req_id"] for f in base}),
                    "false_alarm_categories": dict(Counter(f["category"] for f in base)),
                    "kinds": kinds}
    return out


TEST_KINDS = {
    "signal_typo": ("A signal name misspelt (FuelLevel becomes FuelLevl)", "unknown_signal"),
    "out_of_range": ("An input value outside the signal's DBC range", "out_of_range"),
    "unknown_requirement": ("The test cites a requirement ID that does not exist",
                            "unknown_requirement"),
    "no_requirement": ("Every requirement ID removed from the test", "no_requirement"),
    "no_check": ("The test's checks deleted, so it can never fail", "no_check"),
    "duplicate_test": ("A copy of an existing test under a new name", "duplicate_test"),
    "exact_scaled": ("An exact equality on a scaled signal with no tolerance", "no_tolerance"),
    "flipped_expectation": ("The expected on/off value flipped (1 becomes 0)", None),
}


def _automated_units():
    from harness.outside import split_tests

    src = ROOT / "runs" / "exports" / FORGE_RUN / "test_generated.py"
    return [u for u in split_tests(src) if "pytest.skip" not in u.text]


def _sift_reqs() -> dict[str, str]:
    from harness.audit.store import AuditStore

    a = AuditStore(ROOT / "runs" / "audit.sqlite")
    return {i["item_id"].split("@")[0]: i["payload"].get("source_quote") or i["payload"]["text"]
            for i in a.approved_items(SIFT_RUN, "requirement")}


def _mutate_test(u, kind: str, db) -> str | None:
    t = u.text
    if kind == "signal_typo":
        m = re.search(r"bench\.set\('(\w+)'", t)
        if not m or len(m.group(1)) < 6:
            return None
        s = m.group(1)
        return t.replace(f"'{s}'", f"'{s[:-2] + s[-1]}'", 1)
    if kind == "out_of_range":
        m = re.search(r"bench\.set\('(\w+)', ([-\d.]+)\)", t)
        if not m or m.group(1) not in db.signals:
            return None
        sig = db.signals[m.group(1)]
        return t.replace(m.group(0), f"bench.set('{m.group(1)}', {sig.maximum * 10 + 7:g})", 1)
    if kind == "unknown_requirement":
        return re.sub(r"REQ-[A-Z]+-\d+", "REQ-XYZ-999", t) if "REQ-" in t else None
    if kind == "no_requirement":
        return re.sub(r"\(?REQ-[A-Z]+-\d+\)?:?", "", t) if "REQ-" in t else None
    if kind == "no_check":
        lines = [ln for ln in t.splitlines() if not re.search(r"assert|expect", ln)]
        body = "\n".join(lines)
        return body if "bench.set" in body and body != t else None
    if kind == "exact_scaled":
        return t + "\n    assert bench.value_after('DisplayedSpeed', 100) == 52.37"
    if kind == "flipped_expectation":
        m = re.search(r"expect_(?:within|for)\('(\w+)', 1\.0", t)
        return t.replace(m.group(0), m.group(0)[:-3] + "0.0", 1) if m else None
    return None


def planted_tests() -> dict:
    from harness.anvil.dbc import load_dbc
    from harness.outside import Unit, check_tests

    db = load_dbc(DATA / "icx100.dbc")
    reqs = _sift_reqs()
    units = _automated_units()
    base, _ = check_tests(units, db, reqs)
    kinds = {}
    for kind, (what, expect) in TEST_KINDS.items():
        planted = caught = flagged = 0
        example = None
        for i, u in enumerate(units):
            if kind == "duplicate_test":
                if i == 0:
                    continue
                prev = units[i - 1]
                copy = Unit(prev.name + "_copy", u.file,
                            prev.text.replace(prev.name, prev.name + "_copy", 1), 999)
                found, _ = check_tests([prev, copy], db, reqs)
                hit = any(f["category"] == expect and f["req_id"] == copy.name for f in found)
                any_new = any(f["req_id"] == copy.name for f in found)
                before, after = prev.text, copy.text
            else:
                new = _mutate_test(u, kind, db)
                if not new or new == u.text:
                    continue
                found, _ = check_tests([Unit(u.name, u.file, new, 0)], db, reqs)
                cats = {f["category"] for f in found}
                clean_cats = {f["category"] for f in base if f["req_id"] == u.name}
                hit = (expect in cats) if expect else bool(cats - clean_cats)
                any_new = bool(cats - clean_cats) or hit
                before, after = u.text, new
            planted += 1
            caught += hit
            flagged += any_new
            if example is None:
                example = {"before": before.strip()[:400], "after": after.strip()[:400]}
        kinds[kind] = {"what": what, "expected_check": expect, "planted": planted,
                       "caught": caught, "flagged_any": flagged, "example": example}
    return {"label": "ICX-100 tests from Zyn's template path (synthetic, "
                     f"{len(units)} automated tests)",
            "clean_items": len(units), "false_alarms": len({f["req_id"] for f in base}),
            "false_alarm_categories": dict(Counter(f["category"] for f in base)),
            "kinds": kinds}


DBC_KINDS = {
    "duplicate_frame_id": "Two messages given the same frame ID",
    "signal_overlap": "A signal moved onto bits another signal uses",
    "outside_frame": "A message shortened so its signals no longer fit",
    "range_inverted": "A signal's minimum and maximum swapped",
    "range_unreachable": "A maximum the signal's bits cannot carry",
    "range_missing": "A signal's range removed ([0|0])",
    "unknown_node": "A receiver that is not a declared node",
    "bad_encoding": "An invalid byte-order code the parser silently accepts",
    "invalid_length": "A message length CAN does not allow",
    "mux_undefined": "A multiplexed signal with no multiplexer",
}


def _dbc_mutants(text: str) -> dict[str, str]:
    bos = re.findall(r"^BO_ (\d+) (\w+): (\d+) (\w+)$", text, re.MULTILINE)
    (id1, *_), (id2, n2, *_) = bos[0], bos[1]
    m = {}
    m["duplicate_frame_id"] = text.replace(f"BO_ {id2} {n2}:", f"BO_ {id1} {n2}:", 1)
    m["signal_overlap"] = text.replace(" SG_ FuelLow : 8|1@1+", " SG_ FuelLow : 3|1@1+", 1)
    m["outside_frame"] = re.sub(r"(BO_ \d+ Fuel: )\d+", r"\g<1>1", text, count=1)
    m["range_inverted"] = text.replace("[0|8000]", "[8000|0]", 1)
    m["range_unreachable"] = text.replace('[0|100] "%"', '[0|300] "%"', 1)
    m["range_missing"] = text.replace("[0|8000]", "[0|0]", 1)
    m["unknown_node"] = re.sub(r'("rpm" )ICX100', r"\1ICX10O", text, count=1)
    m["bad_encoding"] = text.replace("0|16@1+ (0.25,0)", "0|16@3+ (0.25,0)", 1)
    m["invalid_length"] = re.sub(r"(BO_ \d+ Fuel: )\d+", r"\g<1>9", text, count=1)
    m["mux_undefined"] = text.replace(' SG_ FuelLow : 8|1@1+', ' SG_ FuelLow m0 : 8|1@1+', 1)
    return m


def planted_dbc() -> dict:
    from harness.anvil.dbc_check import check_file

    text = (DATA / "icx100.dbc").read_text(encoding="utf-8")
    WORK.mkdir(parents=True, exist_ok=True)
    clean = check_file(DATA / "icx100.dbc")
    kinds = {}
    for kind, t in _dbc_mutants(text).items():
        assert t != text, kind
        p = WORK / f"planted_{kind}.dbc"
        p.write_text(t, encoding="utf-8")
        try:
            cats = {f["category"] for f in check_file(p)}
            err = None
        except ValueError as e:
            cats, err = set(), str(e)
        kinds[kind] = {"what": DBC_KINDS[kind], "expected_check": kind, "planted": 1,
                       "caught": int(kind in cats), "refused": err}
    return {"label": "ICX-100 CAN database (synthetic, 1 file, 10 single faults)",
            "clean_items": 1, "false_alarms": len(clean), "kinds": kinds}


def planted() -> dict:
    res = {"benchmark": "S1 planted mistakes", "at": datetime.now().isoformat(timespec="seconds"),
           "requirements": planted_requirements(), "tests": planted_tests(),
           "dbc": planted_dbc()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "s1-planted.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


# ---------------------------------------------------- S2: free-written vs template tests ----

BENCH_API = """The test receives a `bench` fixture with exactly these methods (nothing else):
    bench.set(signal, value)              send an input signal value (keeps sending it)
    bench.stop(message)                   stop sending an input message
    bench.wait_ms(ms)                     let time pass
    bench.expect_within(signal, value, ms) -> bool   value seen within ms from now
    bench.expect_for(signal, value, ms) -> bool      value held for ms from now
    bench.periods(message, count) -> list[float]     next count frame intervals in ms
    bench.value_after(signal, ms) -> float           the signal's value ms from now
Time only passes through wait_ms and the expect/periods/value_after calls."""

SYSTEM = """You write automated pytest tests for an automotive instrument cluster, tested on a
hardware-in-the-loop bench. Write the tests a careful test engineer would write to verify the
requirement you are given: cover its boundaries and the cases that would expose a faulty
implementation. Use only signals and messages from the CAN database. Each test is a complete
Python function named test_..., taking one argument `bench`, with no imports. Reference the
requirement ID in the docstring.

""" + BENCH_API


def _faults_for(spec: dict) -> list[str]:
    """The faults the fault check applies to a spec, from today's fault list."""
    from harness.anvil.simulate import FAULTS

    faults = dict(FAULTS.get(spec["template"], {}))
    if spec["template"] == "event_response" and not spec.get("hold_ms"):
        faults.pop("hold_short", None)
    if spec["template"] == "tracking":
        if spec.get("track_low_factor") is None:
            faults.pop("under_read", None)
        if spec.get("track_high_factor") is None:
            faults.pop("over_read", None)
    return sorted(faults)


def _specs() -> dict[str, dict]:
    """The 15 automatable specs of the template path, at their current version, with today's
    fault list and the template path's own result on it: req_id -> {spec, faults, template}."""
    from harness.anvil.dbc import load_dbc
    from harness.anvil.score import current_checks
    from harness.anvil.simulate import fault_check
    from harness.audit.store import AuditStore

    a = AuditStore(ROOT / "runs" / "audit.sqlite")
    db = load_dbc(DATA / "icx100.dbc")
    cases = [c["payload"] for c in a.list_items(FORGE_RUN, "test_case")]
    out = {}
    for sid, c in current_checks(a, FORGE_RUN).items():
        if not c.get("total"):
            continue
        item = a.get_item(sid)
        spec = item["payload"]
        mine = [x for x in cases if x.get("spec_item") == sid]
        newest = max((x.get("spec_version") or 1 for x in mine), default=1)
        mine = [x for x in mine if (x.get("spec_version") or 1) == newest]
        fc = fault_check(spec, mine, db)
        out[spec["req_id"]] = {"spec": spec, "faults": _faults_for(spec),
                               "template": {"cases": len([x for x in mine
                                                          if x["kind"] != "manual"]),
                                            "reference_passes": fc["reference_passes"],
                                            "caught": fc["detected"], "faults": fc["total"]}}
    return out


RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from harness.anvil.dbc import load_dbc
from harness.anvil.simbench import SimBench
job = json.loads(open(sys.argv[2], encoding="utf-8").read())
db = load_dbc(job["dbc"])
MODELLED = {job["spec"].get("output_signal")} - {None}
unjudged = {"n": 0}


class Bench(SimBench):
    """The simulation models only the behaviour this requirement covers. Checks on other
    signals (a precondition such as ClusterState = ACTIVE) are not judged: they pass."""

    def expect_within(self, signal, value, ms):
        if signal not in MODELLED:
            unjudged["n"] += 1
            self.wait_ms(ms)
            return True
        return super().expect_within(signal, value, ms)

    def expect_for(self, signal, value, ms):
        if signal not in MODELLED:
            unjudged["n"] += 1
            self.wait_ms(ms)
            return True
        return super().expect_for(signal, value, ms)


out = {}
for t in job["tests"]:
    ns = {}
    try:
        exec(compile(t["code"], t["name"], "exec"), ns)
        fn = next(v for k, v in ns.items() if k.startswith("test") and callable(v))
    except Exception as e:
        out[t["name"]] = {"error": "does not load: " + type(e).__name__ + ": " + str(e)[:160]}
        continue
    res = {}
    for fault in [None] + job["faults"]:
        try:
            fn(Bench(job["spec"], db, fault))
            res[fault or "reference"] = "pass"
        except AssertionError:
            res[fault or "reference"] = "fail"
        except Exception as e:
            res[fault or "reference"] = "error: " + type(e).__name__ + ": " + str(e)[:160]
    out[t["name"]] = res
out["_unjudged_checks"] = unjudged["n"]
print(json.dumps(out))
'''


def _run_tests(tests: list[dict], spec: dict, faults: list[str]) -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    job = WORK / "job.json"
    job.write_text(json.dumps({"dbc": str(DATA / "icx100.dbc"), "spec": spec,
                               "faults": faults, "tests": tests}), encoding="utf-8")
    runner = WORK / "runner.py"
    runner.write_text(RUNNER, encoding="utf-8")
    try:
        p = subprocess.run([sys.executable, str(runner), str(ROOT), str(job)],
                           capture_output=True, text=True, timeout=120, cwd=WORK, check=False)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
        # a hang or crash counts against every test in the batch
        return {t["name"]: {"error": f"runner failed: {type(e).__name__}"} for t in tests}


def _score_run(tests_by_req: dict[str, list[dict] | str], specs: dict, db) -> dict:
    """Run one model run's tests on the simulation and through Zyn's code checks.
    tests_by_req: req_id -> tests, or an error string when the model call failed."""
    from harness.outside import Unit, check_tests

    reqs = {rid: s["spec"]["requirement_quote"] for rid, s in specs.items()}
    per_req, all_units = {}, []
    for rid, s in specs.items():
        tests = tests_by_req.get(rid, "no answer")
        if isinstance(tests, str):
            per_req[rid] = {"error": tests[:200], "tests": 0, "faults": len(s["faults"]),
                            "caught": 0}
            continue
        for k, t in enumerate(tests):
            t["name"] = f"{rid}_{k}"
        outcome = _run_tests(tests, s["spec"], s["faults"])
        unjudged = outcome.pop("_unjudged_checks", 0)
        good = [n for n, o in outcome.items() if o.get("reference") == "pass"]
        caught = {f for f in s["faults"] if any(outcome[n].get(f) == "fail" for n in good)}
        loads = [n for n, o in outcome.items() if "error" not in o]
        per_req[rid] = {"template": s["spec"]["template"], "tests": len(tests),
                        "load": len(loads), "pass_reference": len(good),
                        "faults": len(s["faults"]), "caught": len(caught),
                        "unjudged_checks": unjudged,
                        "errors": sorted({str(v)[:120] for o in outcome.values()
                                          for v in o.values()
                                          if str(v).startswith(("error", "does"))})[:3]}
        all_units += [Unit(t["name"], f"{rid}.py", t["code"], len(all_units)) for t in tests]
    found, _ = check_tests(all_units, db, reqs)

    def total(key):
        return sum(p.get(key, 0) for p in per_req.values())

    return {"per_requirement": per_req, "tests": total("tests"), "load": total("load"),
            "pass_reference": total("pass_reference"), "caught": total("caught"),
            "faults": total("faults"), "unjudged_checks": total("unjudged_checks"),
            "zyn_findings": dict(Counter(f["category"] for f in found)),
            "tests_with_findings": len({f["req_id"] for f in found})}


# Requirements whose whole stated behaviour the per-requirement simulation models: one input
# driving one steady output (a telltale on or off, a displayed value following its input).
# Left out, with the reason: REQ-PWR-001/002/003/005 (a sequence of cluster states the
# simulation does not model), REQ-TT-002 and REQ-AUD-001 (two input conditions, flashing),
# REQ-TT-005 (a timed bulb check of every telltale), REQ-GAUGE-005 (a periodic message,
# where free tests also check values the simulation does not produce).
FULLY_MODELLED = ["REQ-GAUGE-010", "REQ-TT-001", "REQ-TT-003", "REQ-TT-004", "REQ-TT-007",
                  "REQ-GAUGE-003", "REQ-GAUGE-004"]


def fair_subset(res: dict) -> dict:
    """Template and free-test results restricted to FULLY_MODELLED."""
    tp = res["template"]["per_requirement"]
    out = {"requirements": FULLY_MODELLED,
           "template": {"caught": sum(tp[r]["caught"] for r in FULLY_MODELLED),
                        "faults": sum(tp[r]["faults"] for r in FULLY_MODELLED)},
           "models": {}}
    for m, runs in res["models"].items():
        out["models"][m] = [{
            "run_id": r["run_id"],
            "tests": sum(r["per_requirement"][q].get("tests", 0) for q in FULLY_MODELLED),
            "pass_reference": sum(r["per_requirement"][q].get("pass_reference", 0)
                                  for q in FULLY_MODELLED),
            "caught": sum(r["per_requirement"][q].get("caught", 0) for q in FULLY_MODELLED),
            "faults": sum(r["per_requirement"][q].get("faults", 0) for q in FULLY_MODELLED),
            "requirements_with_no_valid_test": [
                q for q in FULLY_MODELLED
                if not r["per_requirement"][q].get("pass_reference")]}
            for r in runs]
    return out


def _result(specs: dict, models: dict) -> dict:
    tpl = [s["template"] for s in specs.values()]
    res = {"benchmark": "S2 free-written vs template tests",
           "at": datetime.now().isoformat(timespec="seconds"), "requirements": len(specs),
           "faults": sum(len(s["faults"]) for s in specs.values()),
           "template": {"cases": sum(t["cases"] for t in tpl),
                        "caught": sum(t["caught"] for t in tpl),
                        "faults": sum(t["faults"] for t in tpl),
                        "reference_passes": all(t["reference_passes"] is not False
                                                for t in tpl),
                        "per_requirement": {rid: s["template"] for rid, s in specs.items()}},
           "models": models}
    res["fully_modelled"] = fair_subset(res)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "s2-freetests.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def freetests(profiles: list[str], repeat: int = 2) -> dict:
    """Ask each model to write the tests, then score them."""
    from pydantic import BaseModel

    from harness.anvil.dbc import load_dbc
    from harness.audit.store import AuditStore
    from harness.config import load_config
    from harness.metrics import model_calls
    from harness.models.runner import StructuredOutputFailure, structured_call

    class FreeTest(BaseModel):
        name: str
        code: str

    class FreeTests(BaseModel):
        tests: list[FreeTest]

    cfg = load_config(ROOT / "config.yaml")
    cfg.replay = False
    cfg.knowledge_file = None
    audit = AuditStore(cfg.resolved_db_path())
    db = load_dbc(DATA / "icx100.dbc")
    specs = _specs()
    models = {}
    for prof in profiles:
        runs = []
        for rep in range(repeat):
            run_id = audit.start_run("eval-freetests", note=f"{prof} repeat {rep + 1}")
            tests_by_req = {}
            for rid, s in specs.items():
                user = (f"Requirement {rid}: \"{s['spec']['requirement_quote']}\"\n\n"
                        f"CAN database:\n{db.prompt_block()}\n\nWrite the tests.")
                try:
                    r = structured_call(cfg=cfg, audit=audit, run_id=run_id,
                                        role_or_profile=prof, task="free_tests",
                                        prompt_version="free_tests_v1", system=SYSTEM,
                                        user=user, output_model=FreeTests)
                    tests_by_req[rid] = [t.model_dump() for t in r.output.tests]
                except StructuredOutputFailure as e:
                    tests_by_req[rid] = str(e)
            runs.append({"run_id": run_id, **_score_run(tests_by_req, specs, db),
                         "cost_usd": round(model_calls(audit, run_id, cfg)["cost_usd"], 4)})
            print(prof, rep + 1, {k: v for k, v in runs[-1].items() if k != "per_requirement"})
        models[prof] = runs
    return _result(specs, models)


def rescore() -> dict:
    """Score the stored answers of the latest complete free-test runs again (after a change
    to the simulation or the checks). No model is called."""
    from harness.anvil.dbc import load_dbc
    from harness.audit.store import AuditStore
    from harness.config import load_config
    from harness.metrics import model_calls

    cfg = load_config(ROOT / "config.yaml")
    audit = AuditStore(cfg.resolved_db_path())
    db = load_dbc(DATA / "icx100.dbc")
    specs = _specs()
    latest: dict[tuple[str, str], str] = {}
    for r in audit.list_runs():
        if r["workflow"] != "eval-freetests" or not r.get("note"):
            continue
        prof, rep = r["note"].rsplit(" repeat ", 1)
        gen = [e for e in audit.events(run_id=r["run_id"]) if e["action"] == "generated"]
        if len(gen) == len(specs) and r["run_id"] > latest.get((prof, rep), ""):
            latest[(prof, rep)] = r["run_id"]
    models: dict[str, list] = {}
    for (prof, rep), run_id in sorted(latest.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        tests_by_req = {}
        for e in audit.events(run_id=run_id):
            if e["action"] != "generated":
                continue
            rid = e["detail"]["user"].split(":", 1)[0].replace("Requirement ", "").strip()
            resp = e["detail"]["response"]
            tests_by_req[rid] = (json.loads(resp) if isinstance(resp, str) else resp)["tests"]
        models.setdefault(prof, []).append(
            {"run_id": run_id, **_score_run(tests_by_req, specs, db),
             "cost_usd": round(model_calls(audit, run_id, cfg)["cost_usd"], 4)})
        print(prof, rep, {k: v for k, v in models[prof][-1].items() if k != "per_requirement"})
    return _result(specs, models)


# ------------------------------------------------------------- report: one file for a site ----

PACK_RUNS = {"1.0 (Sonnet, Haiku)": "20261113-221630", "1.1 (Opus)": "20261113-232031",
             "1.1 whole RTEMS (Sonnet, Haiku)": "20261113-233035"}


def _pack_table() -> dict:
    """model -> task -> summary, merged from the pack runs (the five 1.0 tasks and their data
    are unchanged in 1.1, so the runs combine)."""
    out: dict[str, dict] = {}
    for run in PACK_RUNS.values():
        p = ROOT / "runs" / "pack" / run / "results.json"
        if p.exists():
            for model, tasks in json.loads(p.read_text(encoding="utf-8"))["results"].items():
                out.setdefault(model, {}).update(tasks)
    return out


def report() -> dict:
    from harness.pack import TASKS

    def load(name):
        p = OUT / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    opendbc = ROOT / "runs" / "evals" / "opendbc.json"
    qure = ROOT / "docs" / "evals" / "e1-qure-2026-11-13.json"
    site = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "label": "Zyn prototype. Scores describe the named datasets, not general quality.",
        "s1_planted": load("s1-planted.json"),
        "s2_freetests": load("s2-freetests.json"),
        "s3_models": {"pack": "zyn-bench-1.1", "runs": PACK_RUNS,
                      "tasks": {k: {"title": v["title"], "score": v["score"],
                                    "data_note": v["data_note"]} for k, v in TASKS.items()},
                      "results": _pack_table()},
        "s4_real_dbc": ({k: v for k, v in json.loads(opendbc.read_text(encoding="utf-8")).items()
                         if k != "per_file"} if opendbc.exists() else None),
        "s5_qure": json.loads(qure.read_text(encoding="utf-8")) if qure.exists() else None,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "showcase.json").write_text(json.dumps(site, indent=2), encoding="utf-8")
    return site


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["planted", "freetests", "rescore", "report"])
    ap.add_argument("--profiles", default="claude-haiku,claude-sonnet,claude-opus")
    ap.add_argument("--repeat", type=int, default=2)
    a = ap.parse_args()
    if a.action == "planted":
        print(json.dumps(planted(), indent=2)[:6000])
    elif a.action == "rescore":
        rescore()
    elif a.action == "report":
        site = report()
        print(f"Wrote {OUT / 'showcase.json'}: " + ", ".join(k for k, v in site.items() if v))
    else:
        freetests(a.profiles.split(","), a.repeat)


if __name__ == "__main__":
    main()
