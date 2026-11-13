# Competitive landscape and what Zyn should take from it

> Forge was renamed **Anvil** on 13 November 2026 (it clashed with AskUI's Forge). Older text below keeps the name it had when written.

Date: 13 November 2026.
Status: research note. No code changed.
Sources: all 176 pages of askui.com (read in full), plus web research on about 45 products across requirements quality, requirements-based test tools, AI-native engineering agents, agentic UI testing and LLM evaluation. Almost every number below is vendor-reported. Several vendor pages blocked automated reading; those rows rest on search summaries.

---

## 1. The short answer

The market is full of generators and short on checkers.

- **Crowded:** requirement quality scoring against INCOSE and EARS rules, requirements-to-test generation, "multi-agent across the V-model" platforms, generic LLM eval harnesses, agentic UI testing.
- **Open:** an independent tool that checks AI engineering output and measures the models behind it. No product found combines quote-verified findings, persistent human decisions, a signal-database (DBC) oracle, a fault-kill score for generated tests, a multi-model accuracy/stability/cost benchmark, and an air-gapped, append-only log of every prompt.
- **Nobody publishes accuracy.** Not one requirements or test vendor publishes precision and recall on a public dataset. IBM describes an internal benchmark method but no numbers. No one publishes run-to-run stability for requirements tasks. A critic of Flow Engineering's USD 50M round pointed at exactly this gap.
- **Qualification certificates cover the classic engines, never the AI part.** VectorCAST, Parasoft, BTC and MathWorks all certify their deterministic core; none qualifies its LLM feature.

Zyn's current direction (checker and benchmark, [03-direction.md](03-direction.md)) sits in the open space. The research does not show anyone already there. The biggest risks are the expected basics Zyn lacks (connectors, bench export formats, multi-user review, an evidence pack), not a rival with the same idea.

Proposed positioning line: **the independent checker for AI engineering output. Every finding quoted, every generated test fault-scored, every model measured, nothing leaves the machine unless you allow it.**

---

## 2. What to take from AskUI

AskUI (Karlsruhe, founded 2021) runs plain-language UI tests on real screens through a vision agent. It does not compete with Zyn; it starts where Zyn stops ("your manual test cases, often written from requirements"). Its product design has ideas worth borrowing.

| AskUI idea | What it is there | Zyn version |
|---|---|---|
| `ui.md` app knowledge file ("the biggest reliability win") | A plain file describing the app, loaded into every run, kept in Git | **Project knowledge file**: glossary, signal naming, units, house rules for requirement wording, known exceptions. One file per project, versioned, fed to every model call and shown in the audit log. |
| Dreaming | After at least 3 runs, proposes edits to tests and rules as reviewable diffs; never applies them | **Reviewer learning from decisions**: after N reviews, analyse confirmed and dismissed findings and propose rule-profile or prompt changes (for example "stop flagging 'appropriate' in section 4, dismissed 11 of 11 times"). Benchmark the change on the answer key before a person accepts it. |
| Five verdicts (PASSED, FAILED, WARN, SKIPPED, BROKEN) | Separates "the app misbehaves" from "a precondition is missing" from "the infrastructure is down" | Same split for Zyn: a check can **fail**, be **skipped** (missing input, e.g. no DBC), or be **broken** (model or API error). Today API failures and real findings risk looking alike in counts. |
| Per-step report: expected, observed, screenshot, reasoning | Execution, Test, Summary and Management reports; exports to PDF, JSON, JUnit XML | **Evidence report** per run: each finding or test with the quoted source, the check that fired, the reviewer's reasoning, the human decision and the reason. Exports to PDF and JUnit XML so it lands in CI dashboards. |
| Trajectory caching | First run uses the model, repeats replay at near-zero cost and re-check | Zyn already stores every response. Add **replay for unchanged input**: when a requirement's text and the prompt version are unchanged, reuse the stored answer and say so. Only changed text costs a model call. |
| ToolForge | Write a custom tool from a description, verify it, accept it | **Custom checks**: a user describes a house rule ("every timing requirement names a unit"), Zyn drafts a Python check, runs it on the answer key, shows hits and misses, a person accepts it into the rule profile. Deterministic once accepted. |
| "Where it's the wrong tool" on every page | Plain statement of limits | A **limits section** in the README and on each screen: what Zyn does not check, what a pass does not prove. Already matches the no-productivity-claims rule. |
| "Send us ten test cases" | Pilot offer with a fixed, small scope | **Ten-requirement trial**: one command takes ten requirements (CSV or ReqIF) and produces the evidence report, cost and time. The fastest way for anyone to judge Zyn. |
| Tests are files in your Git repo | No lock-in; leave and keep everything | Export the full project (requirements, decisions, answer keys, rule profile, knowledge file) as plain files that diff cleanly. |
| AskUI is itself an MCP server | Claude and other clients can call it | **Zyn as an MCP server** (see item 9 below). |

Not worth taking: self-healing, volume claims, "thousands a day" framing, screen automation itself.

**Name clash:** AskUI sells "Forge" (PromptForge, ToolForge, TestForge), and TestForge writes tests from written specs, the same job as Zyn Forge. Rename Zyn Forge before anything is public.

---

## 3. The landscape, by category

### 3.1 Requirements quality and management

| Product | AI | Grounding and audit | Deployment and models | Evidence |
|---|---|---|---|---|
| QRA QVscribe + ReqWriter | Deterministic rule engine scores 1 to 5; LLM rewrites since Mar 2026; EARS in v7 | Highlights trigger words, records engine version; rewrites re-scored | QRA cloud or on-prem; model not named | No accuracy, no named customers |
| IBM DOORS Next, Engineering AI Hub | Rule-based quality agent, 10 categories, "needs clarification" instead of guessing, re-checks its own rewrites | Temperature 0, fixed seed, versioned prompts; internal multi-model benchmark | Inside IBM ELM only | Method described, numbers not published |
| Jama Connect Advisor | INCOSE and EARS scoring, rewrites, test generation, MCP server | Review Center is the best formal review workflow on the market | Cloud; no model choice | None published |
| Siemens Polarion X | INCOSE checker, duplicate detection, multi-level consistency check over trace links | Inside ALM history | Azure SaaS; custom LLM connectors since 2606 | None |
| PTC Codebeamer AI 1.2 | Requirements and Test Case Assistants (ISTQB technique stored per test) | ALM history | PTC or customer Azure only; GPT-5-mini/nano fixed | "40% less review effort", no method |
| Visure, Visure X (GA 12 Nov 2026) | Quality, decomposition, tests, impact; MCP server | Role-based access | Self-hosted, bring your own model | None |
| Innoslate | 9-attribute NLP check, project heuristics | Not described | Air-gapped NLP; local LLM optional | None |
| Copilot4DevOps | Agile quality frameworks in Azure DevOps | n/a | BYO OpenAI key; about USD 30/user/month | n/a |
| Altium Requirements Portal (ex-Valispace) | Proposed edits with side-by-side preview, AI Skills | No AI audit trail described | Cloud only | n/a |
| Flow Engineering | Graph-based gaps, impact agents, "AI provenance" review queue | Audit of every AI action | Cloud; USD 50M Series B at USD 750M | Rivian, Anduril, Joby; no accuracy |
| Trace.Space | Requirements, gaps, conflicts, tests; deterministic rules for agents (Trinity, Oct 2026) | n/a | Private VPC or air-gapped, own LLM | Lucid, Serve Robotics |

### 3.2 Requirements-based test design and generation

| Product | AI | How AI output is checked | Notes |
|---|---|---|---|
| Vector VectorCAST 2026 Reqs2x | Requirement mapped to function by program slicing, LLM writes unit tests | Tests compile and run with coverage; engineer reviews every result | **Closest incumbent to Zyn Forge.** Bring your own model, on-prem. Free for licence holders. Unit level only, no DBC, no fault score, no model comparison |
| Vector CANoe AI agents + MCP (Aug 2026) | Agent writes CAPL from a requirement, runs, fixes, reruns | Engineer validates in CANoe before approving | Bring your own LLM |
| BTC EmbeddedPlatform | Formal requirements (EmbeddedSpecifier), TestAgent for HIL, AI-code verification | "Trust from deterministic verification, not from the AI" | Qualified for ISO 26262 and more |
| TPT (Synopsys) | AI-supported requirement formalisation (2026 R1) | Not published | Back-to-back testing |
| MES Test Manager | Semi-formal MARS requirements to test sequences | Deterministic | No AI |
| Razorcat TESSY | Classification trees; **mutation testing** in V4.3 | Deterministic | Only tool found that measures test strength by mutation |
| LDRA TBextremePLUS | Boundary and equivalence generation for coverage | Deterministic | Qualification packs |
| Parasoft C/C++test | Agent + MCP closes coverage gaps, fixes MISRA | Structured results | Certified GoogleTest framework, not the agent |
| MathWorks R2026a | Requirements Table formalisation, SLDV generation, Copilot explains models | Formal methods | Qualification kits |
| dSPACE + Hyperpilot | Hyperpilot generates traceable suites as dSPACE SDK executables, regenerates on change | Engineer sign-off | Pilots since Aug 2026 |
| tracetronic ecu.test agent | Packages from block specs plus signals | Vendor says quality depends on spec and model | On-prem or cloud model |
| Keysight Eggplant | Image-based HMI tests; Generator writes tests from requirements | On-prem GenAI | NIO: about 40% less manual effort |
| Qt Squish + MCP | Agents drive Squish; Coco MCP for coverage-guided generation | Squish as deterministic executor | Schaeffler, Nissan, Stellantis |
| BootLoop Test (May 2026) | Agent generates and runs tests on HIL | User reviews | New |

### 3.3 AI-native engineering agents (safety-critical)

Hyperpilot (see [02-hyperpilot-research.md](02-hyperpilot-research.md)), Ketryx (USD 55M raised, compliance agents moving from medtech into ISO 26262 and ASPICE, "90% less documentation time"), Flow, Trace.Space, Dalus (YC), Modelwise (FMEA), Osos AI, EltegraAI, Fennec. Large-vendor assistants: SodiusWillert Mercury (Rhapsody), itemis ANALYZE (AI FMEA, engineers keep approval), Ansys medini Copilot, Tata Elxsi DevStudio.ai (multi-agent across ASPICE SYS and SWE, generation-heavy). **Omnex AutoAssesspro.AI** reviews ASPICE work products against checklists: the only product found that checks rather than generates, and it checks human work, not AI output.

An industry webinar (AUMOVIO, Dec 2025) states what assessors will want from AI use under ASPICE: evidence that is objective, stable and verifiable, and records showing how each AI finding was reviewed, confirmed or rejected. That is Zyn's audit design, almost word for word.

### 3.4 Agentic UI testing

AskUI, Keysight Eggplant, Qt Squish MCP, testRigor, Momentic, QA Wolf, Octomind, Testsigma, mabl, Functionize, Tricentis agentic Tosca, Applitools, raw computer use. All automate interaction with a screen. None checks whether a test matches its requirement or its signal database. Not Zyn's market; possible downstream consumers of Zyn-checked tests.

### 3.5 LLM evaluation and benchmarks

Generic harnesses: promptfoo (acquired by OpenAI, Mar 2026, which weakens its neutrality), Braintrust (USD 800M valuation), LangSmith, Arize Phoenix, DeepEval, Inspect AI, OpenAI Evals. None ships automotive tasks, quote verification or a domain test oracle.

Domain data worth knowing: QuRE (already used, E1), SAFARI (ISO 26262 HARA benchmark, 9 frontier models, best ASIL macro-F1 0.261: plausible output, poor classification), a semisynthetic automotive NLI set (21k requirement pairs for consistency), ReqEBench, Mercedes Req2Road (32 of 36 requirements to executable scenarios), an LLM CAN-signal mapping case study, Fraunhofer FOKUS LESS (LLM translates to a controlled grammar, validated, then tests generated). No published benchmark of run-to-run stability on requirements tasks was found.

### 3.6 Open-source Claude skill packs

**Automotive Engineering Suite** (jherrodthomas/automotive-skills-suite, MIT, about 3,300 stars, last push 16 Oct 2026). 152 installable Claude skills: 76 builders (HARA, FMEDA, TARA, DFMEA, DBC, UDS, test case catalog, traceability matrix, verification plan and more) each paired with a "checklist reviewer". The closest public match to Zyn's builder-plus-reviewer idea, and the one most likely to be put next to Zyn.

How it works, read from the skill files on 13 Nov 2026: Claude writes a JSON file from the conversation, and a Python script lays that JSON out as an Excel workbook. The reviewers are Python scripts that read the workbook and rate checks FC, LC, PC or NO. There is no AI reviewer pass, no quote check against a source, no answer key and no record of who confirmed what.

What its own example notes admit:
- Before a repair on 8 Sep 2026, the traceability matrix builder ignored its input and wrote five headings, and its reviewer rated an empty matrix "broadly compliant": 22 of 25 checks were hard-coded, and "no orphan test cases" was always Fully Compliant.
- After the repair, 12 traceability checks are labelled "AUTO-SUGGEST DRAFT" because code cannot verify them.

What we found ourselves: the test case catalog builder advertises 11 tabs (preconditions, inputs, expected outputs, requirement links) but writes three, with only ID, title and status per test.

What it means for Zyn:
- It shows the failure Zyn is built to prevent: a reviewer that passes work it never looked at. Zyn's code checks either fire on evidence or stay silent, and every AI finding has to quote the source.
- It covers far more work products than Zyn (ISO 26262, 21434, SOTIF, APQP, ASPICE). Zyn is deeper on two: requirements and tests.
- **Checker-mode test: not possible yet.** We planned to run its output through Sift Review and Anvil Review. That didn't work, for three reasons. The test catalog holds no signals, values or requirement links, so Anvil Review has nothing to check. The DBC builder writes an Excel spec, not a `.dbc` file. And the AI-written part (the JSON) isn't published. Making that JSON ourselves would test our own output, not theirs. Revisit if the suite publishes real session outputs or a catalog that carries expected values and requirement IDs.

Not counted: im-hashim/automotive-claude-code-agents (personas and generated standards notes installed into the global Claude folder, an unproven "2 hours to 2 minutes" claim, and an install command that clones a different author's repository).

---

## 4. What Zyn already does that few or none do

1. Accuracy on public data (QuRE, PROMISE, RTEMS). Nobody else publishes.
2. Run-to-run stability as a reported number.
3. Comparing models on the buyer's own answer keys, with cost and reviewer effort.
4. Offline mode that refuses cloud calls.
5. AI findings whose quotes are mechanically verified in the source.
6. Dismissals that carry over to unchanged text across runs.
7. `<TBD>` placeholders with questions to the spec author instead of invented numbers (IBM's "needs clarification" is the only parallel).
8. Every prompt and response kept for replay.
9. Extraction with exact page and quote position.
10. Model proposes a template with quoted parameters; code checks them against the requirement and the DBC.
11. Generated tests run against injected faults to show what they catch.
12. Assumed values listed per test case; "not automatable" as an explicit outcome.

These are the differentiators. They are invisible today because they live in a local prototype and a few docs.

## 5. What buyers expect that Zyn lacks

From the incumbents, in rough order of how often they appear: ALM connectors (DOORS Next, Polarion, Codebeamer, Jama), ReqIF round-trip export, multi-user review with roles and SSO, trace links and impact across levels, customisable rule profiles and glossaries, semantic near-duplicate detection, coverage measurement on real code, export to the buyer's bench formats, requirement formalisation, tool qualification documents, an API or MCP surface, and a written security and AI data policy.

---

## 6. Recommendations, ranked

Value is judged against the open space in section 1. Effort is relative to what Zyn already has.

| # | Feature | Why | Effort | How to prove it |
|---|---|---|---|---|
| 1 | **Checker mode for outside AI output** | Import requirements or tests produced by any generator (Reqs2x, CANoe agent CAPL, Hyperpilot, a Copilot) and run quote checks, DBC conformance and the fault-kill score on them. Turns every generator into a source of work for Zyn instead of a rival | Medium: importers plus reuse of existing checks | Run it on tests a model writes freely vs Forge's template path; report the difference |
| 2 | **Fault-kill score as a headline metric** | "This test set catches X of Y injected faults." No AI vendor publishes a test-adequacy score; only TESSY does mutation at all. Add DBC-derived faults (boundary off by one, timeout too long, wrong signal, stuck value) | Small to medium | Already partly built (42 of 42); publish per run and per model |
| 3 | **Published, versioned benchmark pack** | Accuracy, agreement across N runs and cost per correct item, on QuRE, PROMISE, RTEMS and the synthetic ICX-100, rerunnable offline. Offer the task format in an Inspect or promptfoo compatible shape so others can run it | Medium | The pack is the proof; publish results with the caveats |
| 4 | **Evidence report and export** | AskUI-style per-item report (quote, check, reasoning, human decision and reason), five-way verdicts (pass, fail, warn, skipped, broken), PDF and JUnit XML, hash-chained audit export. Map sections to the ASPICE base practices assessors ask about (SYS.2, SWE.4, SUP.8, SUP.9) | Medium | Show the report to two practitioners; ask what an assessor would still ask for |
| 5 | **Change impact on tests** | Already built before this note (commit "Stale tests from Delta"): Delta impact, one-action stale marking, selective re-proposal, stale and superseded cases left out of exports | Done | Synthetic ICX-100 revision 2 |
| 6 | **Replay for unchanged input** | Built 13 Nov 2026: same profile, model, prompt (including the knowledge file) and input reuse the stored answer, logged as "replayed" with zero tokens; stability passes, benchmarks, re-proposals and the smoke test always ask again | Done | "Answers reused" on the Audit log tab |
| 7 | **Project knowledge file and rule profiles** | Knowledge file built 13 Nov 2026 (`knowledge_file` in config.yaml, template `knowledge.example.md`, added to every call, version recorded per answer, shown in the sidebar and audit tab; the benchmark leaves it out). Saved rule profiles still to do | Half done | Benchmark with and without the file run 13 Nov 2026: no measurable effect from the generic template ([bench 1.1](bench/2026-11-13-pack-zyn-bench-1.1.md)) |
| 8 | **Reviewer learning from decisions** | Dreaming for reviewers: after N reviews, propose rule or prompt changes from confirmed and dismissed findings, benchmark them, a person accepts | Medium | Precision before and after on the answer key |
| 9 | **Zyn as an MCP server** | Lets Claude Code, CANoe agents or any MCP client call Zyn's checks (quote check, DBC conformance, fault-kill) as the deterministic checker inside their loop. This is the 2026 integration pattern (CANoe, Parasoft, Jama, Visure, Squish all ship MCP) | Medium | A Claude Code session that writes tests and has Zyn reject the bad ones |
| 10 | **Bench export formats** | Robot Framework and a dSPACE-SDK-shaped pytest first (both Python), then CAPL test units for CANoe, then ecu.test packages. Without these, generated tests do not run on the bench a buyer owns | Medium each | Lint and dry-run each format on the simulated bench |
| 11 | **ReqIF round-trip and a read-only ALM bridge** | Export decisions and accepted rewrites back as ReqIF; later a read-only reader for DOORS Next or Polarion. QVscribe's browser extension (uses the engineer's own session, never writes) is the cheapest pattern | Medium | Round-trip the ICX-100 set without loss |
| 12 | **Calibrated reviewer** | Show each finding category's measured precision next to the finding, computed from human decisions over time. Nobody does this | Small once decisions accumulate | The numbers are the proof |
| 13 | **Custom checks drafted from a description** | ToolForge idea: user describes a rule, Zyn drafts a deterministic check, shows hits and misses on the answer key, person accepts | Medium | Hits and misses table per new check |
| 14 | **Requirement formalisation** | Store Forge's chosen template as a structured requirement (EARS-like or a small controlled grammar) so consistency and completeness can be checked formally across the set. Matches BTC, TPT, MES and the FOKUS research | Medium to large | Conflicts found by formal check vs by the AI pass |
| 15 | **Tool confidence document** | ISO 26262-8 tool classification argument: the human gate plus deterministic generation support a low tool confidence level. A short document set, not certification | Small to medium | Review by someone who has done tool qualification |
| 16 | **Coverage on real code** | Run exported tests against compiled C with gcov for statement and branch coverage. Every incumbent sells on coverage | Large | Needs real code; RTEMS is a candidate |
| 17 | **Multi-user review, roles, SSO** | Required for any team use, irrelevant for a personal prototype | Large | Only if Zyn leaves the laptop |

Not recommended from this research: building a screen-automation runner (AskUI, Eggplant, Squish own it), autonomous HARA or ASIL classification (SAFARI shows frontier models at 0.26 macro-F1; at most a benchmark task), and any productivity claim before a measured pilot.

### Suggested order

1. Items 5, 6, 7 (small, make what exists sharper). 5 and 6 done, 7 half done.
2. Items 2 and 4 (make the differentiators visible).
3. Items 1 and 9 (checker positioning; the strongest distinct value).
4. Item 3 (publish).
5. Items 10, 11, 12, 13 as demand shows.
6. Items 14 to 17 only with a real user asking.

Rename Forge before step 3.

---

## 7. Caveats

- Vendor claims are self-reported; comparison blogs in this space are often sponsored or written by competitors.
- Pages that blocked automated reading: Jama blog, PTC news, Visure X release, piketec.com, parts of Synopsys and G2. Those rows use search summaries.
- Startups with little public detail: Osos AI, EltegraAI, Fennec, Dalus.
- Elektrobit, ETAS and MES showed no AI agent product; they may have unannounced work.
- The AskUI page text is kept in the session scratchpad, not in this repository.

## 8. Key sources

- AskUI: https://www.askui.com (all sitemap pages, 13 Nov 2026)
- VectorCAST Reqs2x: https://www.vector.com/en/company/press/press-releases/vectorcast-2026-launches-ai-powered-requirements-based-test-creator/
- CANoe AI agents: https://www.eenewseurope.com/en/canoe-ai-agents-automate-automotive-test-workflows/
- BTC: https://www.btc-embedded.com/
- TESSY mutation testing: https://www.eenewseurope.com/en/tessy-v4-3-offers-automated-mutation-test/
- dSPACE and Hyperpilot: https://www.mbtmag.com/software/news/22972625/hyperpilot-dspace-automate-testing-for-safetycritical-automotive-software
- tracetronic ecu.test agent: https://www.tracetronic.com/products/extras/et-agent/
- Squish and Kiro: https://aws.amazon.com/blogs/industries/accelerate-automotive-ui-development-with-kiro-squish-and-virtual-targets-on-aws
- QVscribe: https://qracorp.com/qvscribe/
- IBM AI Hub quality agent: https://community.ibm.com/community/user/blogs/bhawana-gupta/2026/05/13/ai-hub-delivers-trustworthy-reqmts-quality-scores
- Codebeamer AI hosting: https://support.ptc.com/help/codebeamer_ai/en/codebeamer/install_guide/ig_private_hosted_cbai.html
- Polarion X 2606: https://blogs.sw.siemens.com/polarion/polarion-x-2606-whats-new-and-noteworthy/
- Visure X: https://www.globenewswire.com/news-release/2026/11/12/3402086/0/en/visure-solutions-launches-visure-x-the-ai-native-engineering-platform-built-for-the-rigor-of-safety-critical-development.html
- Flow Engineering: https://siliconangle.com/2026/10/01/flow-engineering-raises-50m-to-bring-the-power-of-ai-to-hardware-engineering/
- Trace.Space Trinity: https://tech.eu/2026/10/01/tracespace-launches-trinity-to-tackle-hardware-engineerings-next-bottleneck/
- Ketryx automotive: https://ketryx.com/industries/automotive
- Omnex AutoAssesspro: https://omnexsystems.com/aspice-obot-autoassesspro-ai
- AUMOVIO AI and ASPICE webinar: https://engineering-solutions.aumovio.com/wp-content/uploads/2025/12/AI_ASPICE_WEBINAR.pdf
- promptfoo acquisition: https://openai.com/index/openai-to-acquire-promptfoo/
- SAFARI: https://arxiv.org/pdf/2609.20584
- QuRE: https://arxiv.org/html/2508.08868v1
- Req2Road: https://arxiv.org/abs/2602.15591
- Automotive Engineering Suite: https://github.com/jherrodthomas/automotive-skills-suite (skill files and `examples/*/README.md`, read 13 Nov 2026)

## 9. Built on 13 November 2026

All recommendations except 16 (coverage on real code) and 17 (multi-user, roles, SSO), which Tom chose to leave until someone needs them. Forge was renamed Anvil first.

| # | Built as |
|---|---|
| 1 | Checker mode: Sift Review against a source document; Anvil Review for tests from any tool (`harness/outside.py`) |
| 2 | Fault-kill score with 24 fault types (`harness/anvil/score.py`) |
| 3 | Benchmark pack `zyn-bench-1.1` with Inspect and promptfoo exports (`harness/pack.py`); run on Opus, Sonnet and Haiku ([1.0](bench/2026-11-13-pack-zyn-bench-1.0.md), [1.1](bench/2026-11-13-pack-zyn-bench-1.1.md)) |
| 4 | Evidence report: five verdicts, HTML, JUnit, hash-chained audit export (`harness/evidence.py`) |
| 5 | Already built before this note |
| 6 | Replay of stored answers |
| 7 | Project knowledge file and rule profiles (`rules/`) |
| 8 | Reviewer learning from decisions (`harness/learn.py`) |
| 9 | Zyn as an MCP server (`harness/mcp_server.py`) |
| 10 | Robot Framework, CAPL and step-table exports; native ecu.test packages not written |
| 11 | ReqIF round-trip into the original file (`harness/sift/roundtrip.py`) |
| 12 | Calibrated reviewer (`harness/calibration.py`) |
| 13 | Custom checks drafted by a model, accepted by a person (`harness/sift/custom.py`) |
| 14 | Formal set check of Anvil specs (`harness/anvil/formal.py`) |
| 15 | Draft tool confidence argument ([06-tool-confidence.md](06-tool-confidence.md)) |

Screen work, done the same evening: the calibration record on each finding card, formal statements on each Anvil spec card with contradictions shown above the list and on the cards involved, and the ReqIF file named on the Sift Review export button.
