# Hyperpilot: what it does and what Zyn should take from it

Date: 13 November 2026.
Status: research note. No code changed.
Sources: the hyperpilot.ai homepage, third-party listings (G2, neura.market), funding press, and the New Eagle / Hyperpilot deck from the Raptor Innovation Summit, 24 Sep 2025 (text extracted and read in full). Two press articles on the dSPACE integration blocked automated reading; their content is taken from search summaries only.

---

## 1. The company

- **Legal name:** Hypercritical Ltd, trading as Hyperpilot (written "Hyperpilot^"). London. Founded 2023.
- **CEO / co-founder:** Elie Talj.
- **Funding:** about GBP 2M pre-seed, December 2025, led by Join Capital with Octopus Ventures, Plug and Play and tiny.vc. Aggregators quote USD 2.0M to 2.7M and call it seed; the sterling pre-seed figure is the consistent one.
- **Target:** control software for safety-critical systems. Automotive first (EV powertrain, inverters, motor control, BMS), then aerospace and defence.
- **Partners:** New Eagle (Raptor ECU and toolchain, US) since Sep 2025. dSPACE since Aug 2026 (joint pilots with a limited number of OEMs and suppliers).
- **Named customers:** none public.

## 2. The product

Three engines mapped onto the V-model. Each is "one-shot": structured input in, structured output out, no chat.

| Engine | Older name | Does | Tech |
|---|---|---|---|
| **Req.Gen^** | Systems Engineer^ (Copilot) | Generates system architecture and decomposed, traceable requirements from specs, standards, datasheets or **legacy code**. Analyses existing requirements for errors and missing data and **proposes corrections**. | LLM |
| **Test.Auth^** | QA Engineer^ (Copilot) | Writes executable test suites covering every requirement, for MiL, SiL, HiL, bench and vehicle. Exports native **dSPACE Test Automation SDK** executables. **Regenerates affected tests when a requirement changes.** | LLM |
| **SW.Syn^** | Controls Engineer^ / Autopilot^ | Synthesises control code that must pass the whole test suite, learning from test results run in simulation. Marketed as "no human approval required". | Proprietary "algorithm discovery foundation model", described as searching algorithms rather than tokens. No architecture, training data or evaluation published. |

The human stays at two points: stating intent and approving tests and requirements. Code is meant to be fully automatic.

## 3. How strong is the evidence

Thin. Everything is vendor-reported.

- **"20x" requirements case study:** one subsystem of a 20-subsystem motor control unit. One engineer, 15 minutes generating plus 1 hour reviewing, against a recorded team effort. Man-hours for the baseline are extrapolated (400 vs 20).
- **"30x" test case study:** one subsystem. 5 minutes generating plus 2 hours reviewing, 103 tests for an EV inverter unit. Baseline was QA engineers already using a Gemini copilot (1,200 vs 40 extrapolated man-hours).
- **"100% of tests pass, guaranteed":** a pass rate against tests the same system helped write says nothing about whether the tests are complete. No public result shows SW.Syn^ output in a vehicle.
- **Homepage numbers** (412 requirements, 1,840/1,840 tests passing) are illustrative examples, not customer results.
- **ISO 26262 / ASPICE:** no claim found that output is qualified or certified.

Useful takeaway: the measured value is in review time. Their own case studies say review took 4 to 24 times longer than generation. That is the step Zyn already designs around.

## 4. Side by side with Zyn

| Capability | Hyperpilot | Zyn today | Zyn plan |
|---|---|---|---|
| Spec document in, requirements out | Yes | **Built (P1)** | |
| Legacy code in, requirements out | Yes | No | Not planned |
| Quality flags on requirements | Yes, with proposed corrections | Flags only (weak words, ungrounded quotes, modal change) | |
| Traceability requirement to test | Yes | | P3 |
| Tests from requirements | Yes, executable | | P3, scripts generated but never run |
| Regenerate tests when a requirement changes | Yes | Audit store keeps versions, nothing reacts to them | Not planned |
| Run tests (SiL / HiL) | Yes, via dSPACE and Raptor Cloud | No | Out of scope |
| Control code synthesis | Yes (claimed) | No | No |
| One-shot structured calls, no chat | Yes | **Yes** | |
| Human approval at every step | Partly; code has none | **Yes, enforced by the database** | |
| Model choice | Their own; hosted only as far as public info goes | **Any: Claude or local** | |
| Published, reproducible evals | None | | P2 and P4 |

Zyn's design already matches Hyperpilot's front half. The differences that matter are four features Zyn does not plan yet.

## 5. What to take into Zyn

You cannot plug Hyperpilot itself into Zyn. It has no public API, the model is closed, and access is a free trial behind a company email. What you can do is build the ideas. Ranked by value for effort:

### A. Proposed corrections on flagged requirements (small, do first). BUILT 13 Nov 2026
Built as "clarification proposals": the fix targets the flagged SOURCE wording (the existing AI reviewer already fixes extraction mistakes). Missing values become `<TBD: ...>` placeholders, never invented numbers. Not yet scored on QuRE.
When a requirement is flagged (weak word, not atomic, missing value), the model also returns a suggested rewrite plus the reason. The human accepts, edits or ignores it in the review screen; accepting creates a new version in the audit log. One schema field, one prompt version, one button.
*Can be scored:* QuRE has human defect labels, so we can measure whether the rewrite clears the flag.

### B. Change impact and selective regeneration (medium, strongest demo)
When a human edits an approved requirement, code finds every test that traces to it, marks those tests "stale", and regenerates only those. The review screen shows old test next to new. This is the dSPACE pitch in their own words, and Zyn's append-only audit store already has the version history it needs.
*Depends on:* P3 (tests must exist first). Build it into P3 rather than after.

### C. Requirements from legacy code (medium, new input mode)
A second Sift entry point: C source in, requirements out, each one citing the file and line range it came from (same grounding check as quotes today, but on code). Matches the case study Hyperpilot leads with.
*Can be scored:* the RTEMS slice already cleared in our research has both source code and its official requirements. Give the model the code, withhold the spec, compare. That is a real benchmark, not author-made gold.

### D. Run the generated tests in simulation (large)
Today the plan marks every script "UNTESTED". Adding a small Python plant model (for example the synthetic fuel gauge or cluster ECU) on the python-can virtual bus would let generated tests actually run and report pass/fail. This is a poor man's SiL, not dSPACE. It turns "scripts that parse" into "scripts that execute".
*Note:* only worth doing after B, and the plant model would be author-made, so results must say so.

### E. Code synthesis (do not build now)
SW.Syn^ rests on a proprietary model with no public evidence. An LLM generate-and-test loop on a toy controller is possible, but it would conflict with two Zyn principles: every step has a human gate, and nothing is presented as measured until it is. Park it. Revisit only if D works.

## 6. Proposed order

1. Finish and commit the current P1 changes.
2. A (proposed corrections) as a short P1.5.
3. P2 evals as planned, adding C as eval E8 on RTEMS code.
4. P3 test generation (now Anvil) with B built in.
5. D as an optional P5.

## Sources

- https://hyperpilot.ai
- https://ai.g2.com/marketplace/tools/hyperpilot
- https://www.neura.market/ai-tools-directory/new-ai-tools/hyperpilot
- https://neweagle.net/wp-content/uploads/Raptor-Innovation-Summit-2025-Hyperpilot-and-New-Eagle-An-AI-Augmented-Workflow.pdf
- https://www.mbtmag.com/software/news/22972625/hyperpilot-dspace-automate-testing-for-safetycritical-automotive-software (summary only, page blocked)
- https://www.automotivetestingtechnologyinternational.com/?p=66832 (summary only, page blocked)
- https://www.soapbox.vc/feed/hypercritical-2m-pre-seed
- https://www.startupmag.co.uk/funding/hypercritical-2025-pre-seed-funding/
- https://www.startup.eu/investments/hypercritical-2m-pre-seed-04-2026
- https://pitchbook.com/profiles/company/864165-34
