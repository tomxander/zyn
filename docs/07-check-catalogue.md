# Check catalogue: the skills suite's checks, sorted

Built on 13 November 2026 from the reviewer skills of the Automotive Engineering Suite (jherrodthomas/automotive-skills-suite, MIT licence; see [05-competitive-landscape.md](05-competitive-landscape.md) §3.6). Their check IDs are kept so the two can be compared line by line. Measures are shortened.

Each check is sorted into one of three groups, by what can decide it:

- **Code**: decidable from the files alone. Zyn runs it as a code check, or could.
- **AI (quote)**: needs reading, but the AI reviewer can only raise it by quoting words that code finds in the document. It stays a question for a person.
- **Person**: needs knowledge the files do not hold (project plans, intent, organisation). Zyn says it did not check it, and never rates it.

Their reviewers treated many Person checks as rated by default (22 of 25 traceability checks were hard-coded before their September 2026 repair). Zyn's rule: a check that did not run is reported as not checked.

## Test case catalogue (TC, 28 checks), against Anvil Review

| ID | Measure | Group | Zyn |
|---|---|---|---|
| TC001 | Unique test IDs | Code | `duplicate_name` |
| TC002 | Titles descriptive | Person | not checked |
| TC003 | Preconditions per test | Code | `no_setup` |
| TC004 | Inputs with types and ranges | Code | `unknown_signal`, `out_of_range` (against the DBC) |
| TC005 | Expected outputs defined | Code | `no_check` |
| TC006 | Pass/fail measurable | Code, then AI (quote) | `no_tolerance` for scaled signals; the rest not checked |
| TC007 | Each test traces to a requirement | Code | `no_requirement` |
| TC008 | Traceability both ways | Code | `unknown_requirement` and the coverage line |
| TC009 | Orphan requirements | Code | coverage: "No test refers to" |
| TC010 | Orphan tests | Code | `no_requirement` |
| TC011 | Test level allocated | Person | not checked |
| TC012 | Component allocation | Person | not checked |
| TC013 | Automation status | Code | Anvil marks "not automatable" when it writes tests; Anvil Review only reads automated tests |
| TC014 | Tool named for automated tests | Person | not checked |
| TC015 | Automation date | Person | not checked |
| TC016 | Execution priority | Person | not checked |
| TC017 | Execution order | Person | not checked |
| TC018 | Rationale for high priority | Person | not checked |
| TC019 | System state set up | Code | `no_setup` |
| TC020 | Boundary values (min, max, nominal) | Code | coverage: signals never set at their DBC limits |
| TC021 | Error and edge cases included | AI (quote) | not checked yet |
| TC022 | Tolerances stated | Code | `no_tolerance` |
| TC023 | Verification method per test | Person | not checked |
| TC024 | No duplicate tests | Code | `duplicate_test` |
| TC025 | Test count | Code | shown on every run |
| TC026 | Automation ratio target | Person | not checked |
| TC027 | Document control | Code (for Zyn's own runs) | sha256 of every input, append-only audit log, hash-chained export |
| TC028 | Traceability report | Code | evidence report and exports |

## CAN database (DBC reviewer, 36 checks), against the DBC checks

Their DBC reviewer checks an Excel description of a network. Zyn checks the DBC file itself (`harness/anvil/dbc_check.py`), which is what a test bench actually loads.

| ID | Measure | Group | Zyn |
|---|---|---|---|
| TSA-01 | Message IDs unique | Code | `duplicate_frame_id` |
| TSA-02 | DLC valid | Code | `invalid_length` (CAN 0 to 8, or a CAN FD length) |
| TSA-03 | Signals fit the DLC | Code | `outside_frame` |
| TSA-04 | No bit overlap | Code | `signal_overlap` (multiplexed signals allowed) |
| TSA-05 | Scale, offset, min, max, unit defined | Code | `range_missing` for min/max; unit not checked (many real DBCs leave it empty) |
| TSA-06, VA-09 | Multiplexer references defined | Code | `mux_undefined`: the parser drops such multiplexing without a word, so Zyn reads the DBC text |
| TSA-07, VA-04 | Every signal in a message | Code | true by the DBC format |
| TSA-08 | Every message has a sender | Code | not checked: `Vector__XXX` (no sender) is common and legal |
| TSA-09, TSA-10, VA-05 | Senders and receivers are defined nodes | Code | `unknown_node` |
| TSA-11, TSA-12 | Byte order and sign valid | Code | `bad_encoding`: the parser silently reads an invalid code as Intel unsigned |
| TSA-14 | Frame type valid | Code | true by the DBC format (the ID sets it) |
| TSA-13 | min not above max | Code | `range_inverted`, plus `range_unreachable` (limits the bits cannot carry), which they lack |
| TSA-15 | Cycle time for cyclic messages | Person | not checked: the DBC does not say which messages must be cyclic |
| TSA-16 | Transmission type valid | Person | not checked |
| TSA-17 | Value tables for state signals | AI (quote) | not checked: needs to know which signals are states |
| TSA-18, VA-02 | Topology and ECU list documented | Person | not checked |
| VA-01, VA-03 | Signal counts match | Code | not needed: Zyn reads the file, it does not compare two descriptions of it |
| VA-06 | Scaling consistent | Person | not checked |
| VA-07 | Bit allocation verified | Code | `signal_overlap`, `outside_frame` |
| VA-08 | DLC efficient | Person | not checked |
| CR-01 to CR-10, VA-10 | Document structure, revision, TOC, references | Person | not applicable: they describe an Excel document, not a DBC |

## Traceability matrix (TM, 25 checks)

Zyn has no traceability matrix tool. Anvil Review covers the requirement-to-test slice from the tests themselves:

| IDs | Group | Zyn |
|---|---|---|
| TM002, TM003, TM004, TM005, TM006, TM008, TM009, TM012, TM015, TM016 | Code | requirement-to-test coverage, orphan requirements, orphan tests (`no_requirement`), counts |
| TM007, TM020 | Code | not checked: no target is set in Zyn; the coverage numbers are shown, not rated |
| TM001, TM011, TM013, TM021, TM022 | Code, if the links exist | not checked: needs need, design and code levels Zyn does not import |
| TM010, TM018 | Code | ID shapes are learnt from the requirement set; no convention file is read |
| TM014, TM017, TM019, TM023, TM024, TM025 | Person | not checked |

## Verification plan (VP, 28 checks)

Zyn has no verification plan tool. If one is added, the split would be:

- **Code**: VP002 (requirements traced to a method), VP020 (coverage target stated), VP026 (traceability linked). These need a structured plan with requirement IDs.
- **AI (quote)**: VP003 to VP019 and VP021, VP022 (methods, environments, levels, criteria and thresholds defined). Each would have to be raised with a quote showing what is there or naming the missing section.
- **Person**: VP001 (scope covers all safety goals, which needs the safety goals), VP015 to VP017 (schedule and budget), VP023 to VP025 (risk, roles, independence per ISO 26262-2), VP027, VP028.

## What this tells us

- Of the 28 test case checks, 17 can be decided by code, and Zyn now runs a check for each (TC006 only in part). TC021 needs the AI reviewer and is not checked yet.
- About a third of their checks, across all four lists, need a person. A rating for those from a script is a guess. Zyn reports them as not checked.
- On the DBC, Zyn checks the file a bench loads rather than a spreadsheet about it. It adds one check their list lacks (limits the signal's bits cannot carry) and catches three faults the common Python parser reads without complaint.

## Which of their work products Zyn should take on next

Only ones where code has something to check against, so a finding rests on evidence:

| Work product | What code checks it against | Verdict |
|---|---|---|
| UDS and DTC catalogue | The diagnostic description (ODX or CDD): service IDs, DTC codes, data identifiers | Good next tool. Same pattern as Anvil Review against a DBC. |
| Calibration (A2L) | The DBC and the code's map file: names, addresses, ranges | Good, if public A2L samples can be found. |
| HW-SW interface | The C header it generates against the signal list | Narrow, but fully checkable. |
| Traceability matrix | The requirement set and the tests | Already covered in part by Anvil Review coverage. |
| HARA, FMEA, TARA, safety case | Judgement on hazards and ratings | Not a fit: no reference to check against. The public SAFARI benchmark (best ASIL macro-F1 0.261) shows models classify these badly. |
| APQP, PPAP, 8D, SPC | Manufacturing quality | Out of Zyn's scope. |

## Other public lists read on 13 November 2026

- **awesome-canbus** (iDoka): source of the DBC tools above. Zyn already uses cantools; it reads DBC, KCD, SYM and ARXML, so Anvil Review now accepts all four (tested with KCD). The real DBC files came from opendbc, listed there. canmatrix was not needed.
- **awesome-automotive** (Marcin214): a place to look for public requirement sets and specs for new benchmark tasks. Nothing to build from it.
- **awesome-vehicle-security** (jaredthecoder): attack research. Only relevant if Zyn adds an ISO 21434 check.
- **automotive-claude-code-agents** (im-hashim): nothing taken. See [05-competitive-landscape.md](05-competitive-landscape.md) §3.6.
