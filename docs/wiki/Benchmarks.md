# Benchmarks

Five benchmarks, each answering a question engineers ask before they trust an AI engineering tool. The questions come from the [practitioner research](Research-basis.md). Every number names its dataset and method. Machine-readable results for all five are in [docs/bench/showcase/showcase.json](../bench/showcase/showcase.json).

| # | Question | Measured on | Model cost |
|---|---|---|---|
| S1 | Does it catch what AI gets wrong? | Planted mistakes in requirements, tests and a CAN database | None: code only |
| S2 | Free-written tests or a checked template? | 15 requirements, a simulated cluster, 67 injected faults | Claude, three models |
| S3 | Which model, at what cost, and does it repeat itself? | Six tasks, three repeats each | Claude, three models |
| S4 | Does it hold up on real files? | 58 public CAN databases | None: code only |
| S5 | How much review work do the flags create? | 200 automotive requirements with human labels | Claude, two models |

---

## S1. Does it catch what AI gets wrong?

**Why it matters.** "Plausible false facts" is the second most common reason engineers reject a tool (9 of 23 discussions). A checker is only useful if it catches those mistakes without flooding people with false alarms.

**Method.** Start from clean items that match their source with no finding. Plant one known mistake at a time, run Zyn's code checks, and count whether the intended check fires. Run the clean originals too, and count any flag on them as a false alarm. No model is involved, so every run gives the same result. Some kinds of mistake are planted on purpose although no code check targets them, to show what still needs a person.

Data: 46 ICX-100 requirements (synthetic) and 110 RTEMS behaviour statements (public), each against its source document; 43 automated ICX-100 tests from Anvil's template path; the ICX-100 CAN database.

### Requirements against their source

| Planted mistake | ICX-100 | RTEMS | Check |
|---|---|---|---|
| A number changed (10 becomes 20) | 19 of 20 | 2 of 2 | `invented_value` |
| A timing value the source never gives | 44 of 46 | 106 of 110 | `invented_value` |
| "shall" weakened to "should" | 39 of 43 | 107 of 110 | `modal_changed` |
| A requirement the source does not contain | 4 of 4 | 4 of 4 | `ungrounded` |
| A name swapped for another valid one from the same document | 1 of 12 | 0 of 40 | none targets it |
| **False alarms on the clean originals** | **0 of 46** | **0 of 110** | |

Where it misses, and why:
- The six timing values not caught as invented were all still flagged: the added words broke the match, so they came up as "no source sentence matches" instead.
- The modal changes not caught come from table rows ("Low fuel | FuelLow = 1 | Amber"), which have no modal verb to compare against.
- The one changed number not caught ("Table 1" made "Table 2") changed to a number that is also in the same source sentence ("lit for 2 s").
- Swapped names pass every code check. One status code for another, or one signal for another, needs the AI reviewer or a person.

### Tests against a CAN database and requirements

| Planted mistake | Caught | Check |
|---|---|---|
| A signal name misspelt | 28 of 28 | `unknown_signal` |
| An input value outside the DBC range | 40 of 40 | `out_of_range` |
| A requirement ID that does not exist | 43 of 43 | `unknown_requirement` |
| Every requirement ID removed | 43 of 43 | `no_requirement` |
| The test's checks deleted, so it can never fail | 40 of 40 | `no_check` |
| A copy of another test under a new name | 41 of 42 | `duplicate_test` |
| An exact equality on a scaled signal | 43 of 43 | `no_tolerance` |
| The expected on/off value flipped | 0 of 15 | none targets it |
| **Clean tests flagged** | **3 of 43** | all `value_not_traced`: values the template assumed because the requirement gives none |

A flipped on/off expectation stays inside the signal's range and the requirement's values, so no text check can see it. Running the test against a simulated cluster does: that is what the fault-kill score in S2 measures.

### CAN database

10 kinds of fault, each planted alone in the ICX-100 DBC: **10 of 10 caught**, 0 findings on the clean file. Three of them (an invalid byte-order code, a multiplexed signal with no multiplexer, an impossible message length) are read without complaint by the common Python parser, which silently changes their meaning.

### What building S1 fixed in Zyn

The first run caught 0 of 40 tests whose checks had been deleted. The cause: Zyn read the docstring line "Expected: TT_LowFuel = 1" as a check. Zyn now reads steps and checks from code only. The same fix stopped seven false duplicate-test flags, and a number taken from a neighbouring sentence of the same section is now flagged (RTEMS changed numbers went from 0 of 2 to 2 of 2, ICX-100 from 14 of 20 to 19 of 20) with no new false alarm on the 156 clean requirements.

Run it: `python -m evals.showcase planted`

---

## S2. Free-written tests or a checked template?

**Why it matters.** Generated tests that "follow existing bugs, assert little, or multiply redundant scenarios" are a recurring complaint (5 of 23 discussions), and one automotive tester said they would rather validate a template than hundreds of generated cases. This is the first published comparison of the two paths on the same faults.

**Method.** For the 15 ICX-100 requirements Anvil can automate, each model writes pytest tests freely from the requirement and the CAN database, twice. Every test then runs on a simulated cluster built from the requirement's approved spec: first the correct simulation, then once per injected fault. A fault counts as caught when a test that passes on the correct simulation fails on the faulty one. Anvil's template path is scored the same way on the same faults. No answer is reused; every repeat asks the model again.

The simulation models one input driving one output. Seven requirements are exactly that: a telltale switching on or off, a timeout, a displayed value following its input. The other eight include behaviour the simulation does not produce (a sequence of cluster states, flashing, two input conditions, a timed bulb check), so a correct free test can fail on them for the simulation's sake. The headline uses the seven; the full table is below it.

### On the seven requirements the simulation models fully (31 faults)

| Path | Faults caught | Tests that pass on the correct simulation | Requirements with no valid test |
|---|---|---|---|
| **Template (Anvil)** | **30 of 31** | all | none |
| Sonnet, run 1 / run 2 | 25 / 26 | 36 of 48 / 36 of 48 | none |
| Opus, run 1 / run 2 | 25 / 23 | 43 of 54 / 43 of 52 | none |
| Haiku, run 1 / run 2 | 22 / 21 | 30 of 55 / 30 of 66 | 1 / 2 |

### What it shows

- **The template path catches more with fewer tests.** 30 of 31 faults, against 21 to 26 for free-written tests from the same requirements.
- **More tests is not more coverage.** Haiku wrote the most tests and caught the fewest faults. In each of its runs, every test for at least one requirement failed to run at all (broken indentation, or steps written outside a test function).
- **The same model, asked twice, gives a different test set.** Opus caught 25 faults in one run and 23 in the other; Haiku covered the fuel telltale in one run and missed it in the other.
- **The biggest model is not the best test writer here.** Sonnet caught as much as Opus or more, at about a third of the cost (USD 0.53 against 1.58 per run of 15 requirements; Haiku 0.04).

### Across all 15 requirements (67 faults)

| Run | Tests | Run at all | Pass on correct simulation | Faults caught | Tests Zyn flags | Cost (USD) |
|---|---|---|---|---|---|---|
| Template (Anvil) | 43 cases | 43 | 43 | 66 of 67 | | |
| Sonnet 1 | 103 | 103 | 53 | 36 | 8 | 0.53 |
| Sonnet 2 | 99 | 99 | 55 | 44 | 17 | 0.52 |
| Opus 1 | 111 | 111 | 52 | 37 | 14 | 1.58 |
| Opus 2 | 106 | 106 | 49 | 31 | 13 | 1.49 |
| Haiku 1 | 114 | 105 | 54 | 39 | 24 | 0.04 |
| Haiku 2 | 121 | 98 | 53 | 38 | 20 | 0.04 |

"Run at all": Haiku wrote 9 and 23 tests that do not run: code with broken indentation, or test steps written outside any test function. "Tests Zyn flags": Anvil Review's code findings, almost all `value_not_traced`, values the requirement never gives, such as an assumed reaction time.

### What building S2 fixed in Zyn

The first run made model-written tests look far worse than they are, because of two Zyn bugs:
- The simulated cluster treated every `bench.set(...)` as the requirement's input, so a precondition such as "ignition on" counted as the brake warning changing. Anvil's own tests only ever set the input, which is why this never showed. It now reacts only to its own input and message.
- Anvil Review read the time in `value_after('TT_MIL', 137) == 1` as the signal's value and flagged 137 as out of range. It now reads the compared value.

All stored answers were scored again after the fixes (`python -m evals.showcase rescore`), with no new model calls.

Limits: two runs per model. The simulation is built from Zyn's approved specs, so a test that reads a requirement differently from the spec fails on it. ICX-100 is synthetic. Not a measure of time saved.

Run it: `python -m evals.showcase freetests --profiles claude-haiku,claude-sonnet,claude-opus --repeat 2`

---

## S3. Which model, at what cost, and does it repeat itself?

**Why it matters.** Engineers object to different output on repeated runs, and nobody publishes cost per correct answer. The benchmark pack (`zyn-bench-1.1`) runs every task three times per model, asking the model again each time.

Score is the mean of three repeats; the range is lowest to highest.

| Task | Opus | Sonnet | Haiku |
|---|---|---|---|
| ICX-100 section mapping (accuracy) | 1.0 | 1.0 | 1.0 |
| ICX-100 requirement review (recall) | 0.608 (0.529 to 0.706) | 0.647 (0.647 to 0.647) | 0.49 (0.412 to 0.588) |
| Same findings in another repeat (item agreement) | 0.6 | 0.6 | 0.44 |
| QuRE defect flags (F1, human labels) | 0.543 | 0.547 | 0.557 |
| PROMISE requirement type (accuracy, human labels) | **0.914** | 0.886 | 0.881 |
| RTEMS extraction, behaviour sections (recall) | 1.0 | 1.0 | 1.0 |
| RTEMS extraction, whole components (F1) | 0.994 | 0.988 | 0.985 |

Cost per correct item, USD:

| Task | Opus | Sonnet | Haiku |
|---|---|---|---|
| ICX-100 review | 0.01667 | 0.00728 | 0.00063 |
| QuRE defect flags | 0.01744 | 0.00691 | 0.00044 |
| PROMISE requirement type | 0.00082 | 0.00034 | 0.00003 |
| RTEMS whole components | 0.00437 | 0.0021 | 0.00013 |

What it shows:
- **The biggest model does not buy better review.** Opus scored below Sonnet on ICX-100 review on average and varied more between repeats.
- **The same score is not the same answer.** Sonnet's review score was identical in all three repeats, yet only 60 percent of its individual findings recurred. This is why Zyn keeps human decisions persistent and shows how many passes reported each finding.
- **The cheapest model is the value choice for narrow tasks:** the same score band at about one fortieth of Opus's cost per correct item on QuRE.
- **A generic knowledge file changed nothing measurable** on review or QuRE flags, while raising the cost of every call.

Limits: three repeats; ranges are indicative, not confidence intervals. The ICX-100 key is author-made and AI-reviewed. Local models were not run. Full report: [docs/bench/2026-11-13-pack-zyn-bench-1.1.md](../bench/2026-11-13-pack-zyn-bench-1.1.md).

Run it: `python -m harness pack run --profiles claude-opus,claude-sonnet,claude-haiku --repeat 3`

---

## S4. Does it hold up on real files?

**Why it matters.** A checker tuned on its own example can fail on files written by many hands.

**Method.** Zyn's DBC checks on the 58 CAN databases of comma.ai's opendbc (MIT licence, pinned commit). Most are reverse-engineered by the community, so a finding is about the file, not the vehicle. There is no answer key, so this is not a precision figure.

| Result | Count |
|---|---|
| Files read and checked | 50 of 58 (22,909 signals) |
| Files refused, with the parser's reason | 8: five extended frame IDs written as standard ones, three syntax errors |
| Files with at least one finding | 49 of 50 |
| Signals whose limits their bits cannot carry | 545 |
| Messages with signals sharing bits | 191 |
| Undeclared sender or receiver nodes | 85 |

Spot check: every file flagged for overlapping signals or signals outside their frame is also refused by the strict reader of the cantools library, for the same reason.

What it changed in Zyn: a DBC range of `[0|0]` used to be read as "only zero", which would have flagged every test value on 27 of the 50 files. It now means "no range given". The first run produced over 8,600 findings, far too many to decide one by one; they are now grouped per node, per message and per file.

Run it: `python -m evals.opendbc fetch`, then `python -m evals.opendbc run`

---

## S5. How much review work do the flags create?

**Why it matters.** Correction and review cost eating the saving is the third most common objection (8 of 23). A flag a person must dismiss is work.

**Method.** QuRE: 200 requirements from automotive industrial specifications, 209 weak words, of which human reviewers judged 72 to be real defects. A weak word counts as flagged when a finding quotes it. Scores are for the defect class, before any human review in Zyn.

| Flagged by | Precision | Recall | Flags a person would dismiss |
|---|---|---|---|
| Code checks only | 0.31 | 0.35 | 55 of 80 |
| AI reviewer, Sonnet | 0.43 | 0.88 | 85 of 148 |
| AI reviewer, Opus | 0.44 | 0.88 | 81 of 144 |
| Flag every weak word (baseline) | 0.34 | 1.0 | 137 of 209 |

What it shows: the AI reviewer finds most real defects (63 of 72), but more than half of its flags are words the human reviewers judged acceptable in context. That is why Zyn makes dismissing a finding one key, carries dismissals over to unchanged text, and shows each kind of finding's record of how often people agreed with it.

Full report: [docs/04-public-evals.md](../04-public-evals.md).

---

## Not measured yet

- **Local models.** The research found no published comparison of local and hosted models on automotive tasks. The pack runs on Ollama models unchanged; it has not been run on a machine with them installed.
- **Real engineers' effort.** No benchmark here measures time saved. The research is clear that review and correction time must be counted, and that needs a pilot with real engineers on real work.
