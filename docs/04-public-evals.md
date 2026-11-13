# Zyn on public data (13 November 2026)

First scores against datasets Zyn did not author. Everything else so far was scored against the synthetic ICX-100 key (written by Claude, reviewed by an AI). These are benchmark numbers for this prototype on these datasets, not productivity or accuracy claims, and not comparable to published results without the same splits and metrics.

Data handling: both datasets are downloaded to `data/public/` (ignored by git, not redistributed), licences checked at source, file hashes recorded in the result JSON. Raw results: [docs/evals/](evals/). Every model call is in the audit log under the run IDs listed.

## E1: Sift Review quality flags against human review labels (QuRE)

**Data.** QuRE 1.0.1, Femmer, Houdek, Unterbusch et al., Zenodo record 16049822, CC BY 4.0. 2,111 requirements from automotive industrial specifications (Mercedes-Benz among the authors' affiliations). Each row is one weak word in one requirement, judged by a human reviewer as a quality defect or acceptable in context. 31 percent of weak words are defects.

**Method.** 200 unique requirements sampled with a fixed seed (209 labelled weak words, 72 defects), imported as a set and checked by Sift Review (code checks plus the AI batch review; no conflict pass). A weak word counts as flagged when a finding quotes it. Scored on the defect class, before any human review.

| | Precision | Recall | F1 |
|---|---|---|---|
| Baseline: flag every weak word | 0.34 | 1.00 | 0.51 |
| Zyn code checks | 0.31 | 0.35 | 0.33 |
| Zyn AI reviewer, Claude Opus 5.5 | 0.44 | 0.88 | 0.58 |
| Zyn AI reviewer, Claude Sonnet 5.5 | 0.43 | 0.88 | 0.57 |

Cost: Opus USD 1.15, Sonnet USD 0.46 (14 calls each). Runs 20261113-193300-374147 and 20261113-193519-cc8ddc.

**Reading.**
- The AI reviewer beats flagging everything, but only modestly: it finds 88 percent of the defects while about half of what it flags was judged acceptable by the human reviewers. Its false alarms concentrate on words the reviewers usually accepted in context ("special", "short", "soon", "similar").
- The code checks' weak-word list barely overlaps QuRE's vocabulary ("detail", "close", "several", "special" are not on it) and does worse than the baseline. A list built from QuRE would score better here and would be tuning to the test.
- The AI raised 290 findings on 200 requirements, 86 of them "unclear reference": the requirements are excerpts that point to other documents. QuRE labels only weak words, so these count neither for nor against.
- Matching is lenient: a finding that quotes a clause containing the weak word counts as flagging it.
- Sonnet matches Opus at 40 percent of the cost, as in the ICX-100 benchmark.

## E2: requirement type classification (PROMISE NFR)

**Data.** PROMISE NFR, original 625 requirements, (c) 2007 Jane Cleland-Huang, tera-PROMISE repository, CC BY-SA 3.0 (licence in the file header); mirror commit 1f5dc45. Student project specifications, not automotive. 255 functional, 370 non-functional in 11 classes.

**Method.** The model classifies each requirement into Zyn's own type list with the definitions Sift extraction uses (prompt `eval_classify_type_v1`, 25 per call). PROMISE's 12 classes and Zyn's 9 types are mapped onto six coarse classes: functional, performance (with scalability), security, usability (with look and feel), reliability (availability, fault tolerance; Zyn's safety), other (legal, operational, maintainability, portability; Zyn's constraint).

| | F vs NFR accuracy | NFR precision | NFR recall | NFR F1 | Coarse macro F1 | Cost (USD) |
|---|---|---|---|---|---|---|
| Claude Opus 5.5 | 0.91 | 0.95 | 0.90 | 0.93 | 0.86 | 0.46 |
| Claude Sonnet 5.5 | 0.89 | 0.95 | 0.86 | 0.90 | 0.84 | 0.19 |

Per coarse class (Opus): functional 0.90, security 0.90, usability 0.88, performance 0.87, reliability 0.85, other 0.76. Runs 20261113-193655-d64e84 and 20261113-193949-5b9ee3.

**Reading.**
- Type classification is reliable on this data; the weakest class is "other", where the mapping itself is the coarsest (legal, operational, maintainability and portability folded together).
- No few-shot examples or tuning to PROMISE; the prompt is Zyn's own type list.

## E3: requirement extraction and grounding (RTEMS)

**Data.** RTEMS rtems-central at the pinned commit 82230386 (2023-12-19). Eight action requirements, one per component (barrier create, event send/receive, message broadcast, partition create, rate monotonic cancel, semaphore create, signal catch, timer cancel), chosen deterministically from files offered as CC-BY-SA-4.0 OR BSD-2-Clause and used under BSD-2-Clause. Embedded RTOS, not automotive.

**Method.** The YAML is rendered into one Markdown specification by our eval script (cross-references resolved against the referenced items at the same commit): per component an introduction, a "Conditions" section (the "While ..." pre-condition states) and a "Required behaviour" section (the post-condition states). Gold: the 110 sentences with "shall" in the behaviour sections. Test code and transition maps are never shown to the model. Extraction uses Sift's own prompt (extract_v2) and code checks. Two variants: the model sees only each behaviour section, or the whole component, conditions included; some RTEMS conditions themselves contain "shall", so extracting them as requirements is a real trap.

| Variant | Model | Recall | Extracted | Extra items | Quotes verbatim | Modal kept | Cost (USD) |
|---|---|---|---|---|---|---|---|
| Behaviour sections | Claude Opus 5.5 | 110/110 | 110 | 0 | 100% | 100% | 0.45 |
| Behaviour sections | Claude Sonnet 5.5 | 110/110 | 110 | 0 | 100% | 100% | 0.19 |
| Whole components | Claude Opus 5.5 | 110/110 | 111 | 1 | 100% | 100% | 0.46 |
| Whole components | Claude Sonnet 5.5 | 110/110 | 113 | 3 | 100% | 100% | 0.23 |

Runs: 20261113-194616-77f153, 20261113-194842-b9241d (behaviour), 20261113-195040-963d7f, 20261113-195307-a36c68 (whole). Every extra item is a pre-condition that contains "shall" ("The buffer_size parameter shall not an integral multiple of the pointer size") extracted as a requirement.

**Reading.**
- On clean, well-formed requirement text, extraction loses nothing, invents nothing and changes no modal verb. This is the easy case: RTEMS behaviour statements are short, atomic "shall" sentences, unlike the ICX-100 spec with its vague and compound wording.
- With conditions in view, Opus mistook 1 of about 90 condition lines for a requirement, Sonnet 3. A person would reject these in review; the check that they are conditions is not automated.
- The rendering is our construction; RTEMS publishes YAML, not a document. Scores say nothing about PDF tables or messy layouts.

## E4: test coverage (RTEMS), not applicable

RTEMS validation tests drive RTOS API calls in C. Forge generates tests for signals on a vehicle bus from a CAN database; it has nothing to work on here. Scoring it would mean a different kind of generator, so it is recorded as not applicable rather than forced.

## E5: CAN database checks on real DBC files (opendbc)

Source: comma.ai opendbc, pinned commit 27fa1c5d (8 Nov 2026), the 58 files in `opendbc/dbc/`, MIT licence. Most are reverse-engineered by the community, not published by carmakers, so a finding is about the file, not the vehicle. Run with `python -m evals.opendbc fetch`, then `run`.

There is no answer key, so this is not a precision or recall figure. It shows that Zyn reads real files and what its DBC checks report on them (`harness/anvil/dbc_check.py`, built 13 Nov 2026).

| Result | Count |
|---|---|
| Files read and checked | 50 of 58 (22,909 signals) |
| Files refused, with the parser's reason | 8: five extended frame IDs written as standard ones, three syntax errors (names starting with a digit, a malformed message line) |
| Files with at least one finding | 49 of 50 |
| `range_unreachable`: limits the bits cannot carry | 545 signals (for example a 1-bit signal with maximum 3) |
| `signal_overlap`: messages with signals sharing bits | 191 messages; 1 GM file has whole-group signals that span their members on purpose |
| `unknown_node`: sender or receiver not in the node list | 85 nodes |
| `range_missing`: no min/max given | 27 files |
| `outside_frame`, `mux_undefined`, `range_inverted` | 19, 4, 3 |

Spot checks: every file flagged for overlap or outside-frame is also refused by the strict cantools reader for the same reason; the range findings read correctly against the signal definitions.

What it changed:
- Zyn used to read a DBC range of `[0|0]` (no range given) as "only zero", so every test value on such a signal would have been flagged out of range. 27 of the 50 files have such signals. Fixed: Zyn now checks against the range the bits allow and says so in the finding.
- Zyn used to stop at the first faulty file with a parser error. It now reads leniently, reports each fault as a finding, and refuses only files it cannot read at all, with the reason.
- The first run gave 5,010 range findings and 3,595 node findings, one per signal. Nobody can decide that many. They are now grouped: one finding per undeclared node, one per file for missing ranges, one per message for overlaps.

## Bugs the public data found

- The CSV importer failed on long quoted requirements full of commas, typical of real specifications (fixed, test added).
- The evaluation scripts did not load the API key, and a missing key surfaced as a raw TypeError (fixed: the provider now reports missing credentials clearly).
