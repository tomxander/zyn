# Zyn positioning

14 November 2026. Working positioning, to be tested in the first pilots.

Sources: the internal test team (requirement, test and IT engineers, on synthetic and public data only), the market analysis, the product marketer's notes, "Zyn savings evidence.md" and the repo docs.

## 1. The positioning

AI tools and suppliers now hand engineers requirements, tests and CAN databases faster than anyone can review them. Zyn is the independent checker that sits before sign-off. Its code checks compare the work with its source and flag what was changed, invented or weakened. They use no model, give the same answer every run and send nothing out. An optional AI reviewer adds advice, but only with quotes that code can find in the source. A named person makes every call and the log keeps the record. Zyn does not claim the work is right. It shows the reviewer where to look, publishes what it misses, and measures the time it saves on the buyer's own work instead of quoting a percentage.

| | |
|---|---|
| For | requirement and test engineers at vehicle makers and their suppliers |
| who | sign off requirement sets, test suites and CAN databases written by AI tools, suppliers or colleagues |
| Zyn is | an independent checker for AI engineering output |
| that | flags what changed, was invented or was weakened against the source, before a named person decides |
| unlike | the AI built into an ALM or test tool, which checks its own generation or scores wording alone |
| because | its code checks need no model and repeat exactly, every AI finding must carry a quote that code can locate, and Zyn publishes its misses |

## 2. Category

We pick **"independent checker for AI engineering output"**, with the plain job on first use: "pre-review checks for requirements, tests and CAN databases".

| Option | Verdict |
|---|---|
| AI output verification | Rejected. In automotive, verification is a defined V-model activity with an evidence bar. Zyn runs nothing and misses meaning errors, and the word invites a tool-qualification argument. |
| Independent review layer | Used as a description. "Layer" sounds like infrastructure. |
| Evidence assurance | Rejected. Reads as a certification Zyn does not offer. |
| Engineering AI benchmark | Secondary job (Assay), and only Anthropic and Ollama models run today. |
| Review ledger | Rejected. Needs a subtitle and leans on the unproven team server. |

"Independent" is the claim incumbents cannot make: every vendor found checks its own generation or scores human text. "Checker" promises only what the engineers saw.

## 3. Who buys and who uses

**ICP**

| Dimension | First target |
|---|---|
| Company type | Vehicle makers (passenger first, commercial once J1939 checks land) and Tier-1 suppliers that send or receive requirement sets |
| Programme | Body, cluster or ECU programmes with a supplier specification, a ReqIF or Excel requirement set, a DBC and automated tests, in an active revision cycle |
| Signal | AI drafting already in use; ASPICE or ISO 26262 work products in scope |
| Region | EU (Germany first), then US. Hypothesis: ASPICE and ReqIF are routine there |

**User personas (from the test team)**

| Persona | Job Zyn does | What they need next |
|---|---|---|
| Requirement engineer | Drift check of a supplier set against its spec, and between revisions | Findings and decisions from the CLI, ReqIF import into DOORS Next or Polarion, honest "pass" and "approved" wording |
| HIL and test engineer | Pre-flight lint of tests and DBC in CI; the faults a suite misses | Fewer false positives, fault-kill scores for their own tests, readable output |
| Tooling and IT lead | Gatekeeper and first internal champion; owns the CI step | A team container run end to end; a model list that matches the code |

**Buyers and blockers**

| Role | Position | What moves them |
|---|---|---|
| Engineering manager (requirements, V&V or programme) | Pays for the pilot | A measured with-and-without pilot on their own work |
| IT security | Hard veto on data leaving the network | Code checks only and offline mode first; written data flows, hosts and model list |
| Functional safety | Can block use inside a safety argument | "Advisory pre-review, a person decides"; a reviewed tool confidence argument |
| Procurement | Late gate | Vendor viability, fixed scope, everything exportable as plain files |
| Works council (Germany) | Possible blocker | Zyn records who decided and when, and the time to first decision; per-person timing needs agreement first |

**Adoption path**

1. Engineer trial: light install, code checks only, no key, public or synthetic data. No security ticket.
2. CI lint: Anvil Review and the DBC check in a pipeline, as a lint, not a gate.
3. Team server on a test host: company sign-in, roles, four-eyes approval, Ollama or an approved Claude account. Blocked until the container has run end to end.
4. Programme pilot: one real specification, its tests and one revision, measured with and without Zyn.
5. Rollout, only if the pilot shows reviewer minutes saved.

## 4. Competitive alternatives

Vendor facts are vendor-stated; none has independent accuracy data.

| Alternative | Where it wins | Where Zyn wins | Where Zyn loses |
|---|---|---|---|
| Do nothing: manual review | Free, trusted, already in the process | Flags value drift, invented items and weakened modals in about a second. Peer review misses about 40 percent of defects ([Boehm and Basili](https://www.cs.umd.edu/projects/SoftEng/ESEG/papers/82.78.pdf)) | Meaning errors: swapped names, flipped values, word numbers |
| AI in the ALM: [Codebeamer AI](https://community.ptc.com/codebeamer-445/codebeamer-ai-1-1-has-released-173736), DOORS Next AI Hub, Polarion, Jama Advisor, [Visure](https://visuresolutions.com/engineering-intelligence-platform/) | In the system of record, often bundled into the licence | Checks against the source spec, not wording alone; works across tools and suppliers; publishes misses | Integration: ReqIF only, import untested. Bundling is a high threat |
| Rule-based checkers: [QVscribe](https://qracorp.com/qvscribe/) | Owns "deterministic requirement checker" in buyers' minds | Checks against the source and between revisions; also checks tests and DBCs | Wording rules: Zyn's EARS profile flagged 11 of 46 on a set not written in EARS |
| Test tools with AI: [VectorCAST Reqs2x](https://www.vector.com/en/product/vectorcast/vectorcast-ai/), CANoe agents, [Hyperpilot with dSPACE](https://www.mbtmag.com/software/news/22972625/hyperpilot-dspace-automate-testing-for-safetycritical-automotive-software) | Execute tests, own the bench, hold qualification stories | Checks any tool's tests against the DBC and requirements; names surviving faults in cases Zyn generated | No execution or coverage; exports are unrun stubs; no ecu.test |
| AI-native platforms: [Flow Engineering](https://siliconangle.com/2026/10/01/flow-engineering-raises-50m-to-bring-the-power-of-ai-to-hardware-engineering/), [Ketryx](https://ketryx.com/industries/automotive), Trace.Space | Funded, broad, claim human-in-the-loop | Independent of the generator; runs locally; published accuracy | Breadth, money, SSO, support |
| A chat model or skill pack ([Automotive Engineering Suite](https://github.com/jherrodthomas/automotive-skills-suite)) | Free and fast | Quotes verified by code; no silent pass. The pack's reviewer once rated an empty matrix compliant | Breadth of work products |

## 5. Differentiators and proof

| Differentiator | Proof today |
|---|---|
| Checks against the source | On a mutated set the test team caught a changed value, "shall" to "should", an invented 40 ms, an invented requirement, a duplicate ID and a TBD, each with what the source says. No false alarms on the 42 clean items |
| Same answer every run, nothing sent | 46 items in about a second with no key. With offline mode on, a model call was refused before sending and logged. 58 opendbc files in 2.5 seconds |
| Works on anyone's output | Read hand-written pytest, CAPL and Robot with no config; caught a typo'd signal, out-of-range values, `==` on scaled signals, unknown requirement IDs, a copied body and an invented signal |
| Shows what a suite misses | Template cases caught 30 of 30 injected faults on six specs. A thin two-case suite, rebuilt by hand as Zyn cases, scored 5 of 7 and named the faults that survived. Zyn cannot yet score your own test files |
| Change list by ID | Delta on a revised set: 43 unchanged, 2 changed with word diff and value flags, 1 removed, 1 added |
| Publishes its misses | Swapped names 1 of 52 and flipped values 0 of 15, on the README and site |
| A record a person stands behind | HTML, JUnit and a hash-chained log; `verify` returned "Audit chain intact". The AI cannot approve; 79 team-mode tests pass with a stand-in sign-in |

## 6. Messaging

**Tagline.** Replace "AI writes the work. Zyn proves which parts you can trust." with:

> **AI writes the work. Zyn checks it before you sign.**

All three engineers objected to "proves". The code checks missed a word-number change, and "pass" only means they found nothing. The new line names sign-off as the moment and leaves the person in charge.

| Pillar | Message | Proof |
|---|---|---|
| Checked against the source | "See what was changed, invented or weakened before you sign." | Benchmark catch rates; the test team's mutated set |
| Inside your walls, same answer every time | "Code checks run on your laptop with no model and no key. In offline mode every cloud call is refused and logged." | Code-only timings; the offline refusal the IT lead saw |
| Honest about where it stops | "A named person decides. We publish what Zyn misses and measure the time saved with you." | 1 of 52 and 0 of 15 published; the AI cannot approve |

| Persona | Message |
|---|---|
| Requirement engineer | "Run a supplier set against its spec: drifted values, weakened modals and invented requirements, each with the source quote. When revision 2 lands, get the change list by ID." |
| Test engineer | "Lint your tests and DBC before you book the bench: wrong signals, impossible values, untraced tests and tests that can never fail." |
| Tooling and IT lead | "Code checks need no key and no network. Offline mode and the allowed-model list are enforced in code and logged." |
| Engineering manager | "We don't quote a saving. We run a fixed-scope pilot on your work and measure reviewer minutes with and without Zyn." |
| Safety and quality | "An advisory pre-review. A named person makes every decision, and the record can be verified. Not a qualified tool." |

| Use | Avoid |
|---|---|
| checks, flags, catches planted mistakes | proves, verifies, guarantees |
| against the source | catches the errors that matter |
| no code-check findings | pass, clean (unqualified) |
| AI reviewer advises | reliable AI review; "AI agent" for the MCP server |
| Claude, or local models through Ollama | any model, any private cloud |
| designed for teams; container not yet run end to end | enterprise-ready, deployed |
| pilot measured on your work; lint in CI | saves X percent, cuts testing cost, 100 times, gate |

## 7. Proof and claims

| Safe to say | Not safe to say |
|---|---|
| "On planted mistakes, code checks caught 21 of 22 changed numbers, 40 of 40 tests that could never fail and 10 of 10 CAN database faults, with no false alarms on 156 clean requirements." Always say "planted" and "synthetic or public data" | Any time or cost saving, or any figure from the illustrative hours model (minus 13 to plus 950 hours) |
| "Code checks need no model and repeat exactly." | "Catches the errors that matter." It misses swapped names, flipped values and word numbers |
| "Template tests caught 66 of 67 injected faults with 43 tests; free-written model tests caught 31 to 44 with 99 to 121." Add: simulated cluster, Zyn's own specs | "Checks your tests" without saying it reads text and runs nothing |
| "Sonnet matched Opus on review at under half the cost per correct finding; 46 requirements cost about eight US cents." | "AI review is reliable." Only 60 percent of findings recur between runs |
| "The AI reviewer found 63 of 72 real defects on public automotive requirements; more than half its weak-word flags were ones people would dismiss." | "Works with any model or private cloud." The code supports Anthropic and Ollama only |
| "Code checks and offline mode send nothing out." | "Nothing leaves your machine" once an Anthropic key is set |
| "Team mode is built and tested with a stand-in sign-in; the container has not yet run end to end." | "Enterprise-ready", "qualified", "certified" |
| "In 23 public practitioner discussions, checking AI output was the top cost (14)." Add: mostly embedded and QA, not only automotive | "Automotive engineers say" for the whole study |

## 8. Objections and answers

| Objection | Answer |
|---|---|
| "Our ALM already has AI." | Keep it. It scores wording in one tool. Zyn checks the set against its source, across suppliers. Run both on one set and compare. |
| "Does our text go to a US cloud?" | Not with code checks or offline mode. The AI step uses Claude only if you add a key, or a local model through Ollama. |
| "We only approve Azure OpenAI or Bedrock." | Not supported today; it is the next build item. Code checks need no model. |
| "A 'pass' looks like a clean bill." | It means the code checks found nothing. We are renaming it. A person still reviews meaning. |
| "Your numbers are self-graded." | Yes. ICX-100 is synthetic with an AI-checked key. That is why we sell a pilot on your data, with mistakes your engineers plant. |
| "The AI reviewer is noisy." | More than half its weak-word flags were dismissable on QuRE. Start code-only; switch the reviewer on and measure it. |
| "Is this a qualified tool?" | No. It is advisory and a person decides. The draft tool confidence argument still needs a safety engineer's review. |
| "Has the team server been deployed anywhere?" | No. We bring it up on your test host with you before anyone relies on it. |
| "One person built this." | True. You keep everything as plain files, it runs inside your network, and the pilot has a fixed scope. |

## 9. What the engineers said

Paraphrased, from Zyn's internal test team on synthetic and public data. Not customers.

- Requirement engineer: "A fast, repeatable drift checker for supplier sets and revisions. I wouldn't call a set reviewed from code-only output."
- Requirement engineer: "The best catch was the line saying a value wasn't in the matching source sentence, with the quotes beside it."
- Test engineer: "A cheap pre-flight lint for my tests and DBC. I'd run it in CI, not trust it as a gate."
- Test engineer: "The list of surviving faults turned 'add boundary tests' into a to-do list."
- Tooling and IT lead: "A written refusal when something would leave the machine is what gets a tool past security."
- Tooling and IT lead: "I won't take it to IT until the team container has run end to end and the model list matches the code."

## 10. Go-to-market

**First motions**

1. Supplier drift walkthrough: install, run a mutated ICX-100 set against its spec, then Delta on revision 2. It ends with "now try your own file, code-only, offline".
2. Publish the misses: one short post per result, leading with the 1 of 52 and 0 of 15 table and the method.
3. CI lint recipe: a copy-paste pipeline step for Anvil Review and the DBC check.
4. Side-by-side offer: run an ALM's AI and Zyn on the same public set and publish both.

**The pilot offer: sell the pilot, not a percentage**

| Element | Offer |
|---|---|
| Scope | One real specification, its requirement set and tests, through one revision; four to six weeks |
| Where | Customer machines; code checks first, then Ollama or the customer's Claude account if IT allows |
| Design | Matched sections with and without Zyn; code only, plus AI reviewer, plus three-pass filter; mistakes planted by the customer's engineers |
| Measured | Active minutes per item, minutes per dismissal, confirmed share by source, planted misses per arm, re-review minutes on the revision, model spend |
| Customer keeps | Every finding, decision, log and the measurement, as plain files |
| Risk reversal | If there is no reviewer-minute gain, the report says so |

**Build or fix first, because it blocks the story**

| Order | Fix | Unblocks |
|---|---|---|
| 1 | Rename "pass" to "no code-check findings"; fix Delta's "approved" count and "sources: code, ai" when no AI ran | Pillar 3 |
| 2 | Correct Team-server.md (Azure OpenAI, vLLM) or build an OpenAI-compatible connector; default new homes to Sonnet | IT conversations |
| 3 | Run the team container end to end with a real OIDC provider; publish recipe, data flows and hosts | Adoption steps 3 to 5 |
| 4 | Readable CLI summary, pipeable JSON, run labels, decisions from the CLI | Daily use |
| 5 | Anvil Review false positives (the word "check", test-case names, `== 1` return codes, Zyn's own exports); warn on ID mismatch | CI lint motion |
| 6 | Fault-kill scoring of the customer's own tests from the CLI; portable pytest export | Test engineer story |
| 7 | Number-word comparison; ReqIF import tested in DOORS Next and Polarion; MCP version matching the wheel | Weekly requirement use |

**Website changes (`site/src/content.ts`, README)**

- New tagline. Subline: "Requirements, tests and CAN databases, checked against their source before you sign."
- Lead with two jobs, checking requirements and checking tests. Move generation, Assay and the planned tools below the fold.
- "Your models, your walls" and the "any you configure" row: change to "Claude, or local models through Ollama".
- Data FAQ: add that requirement text goes to Anthropic's API once a key is set.
- Roadmap: move Team server from "Done" to "Built, not yet proven".
- Integrations: "ReqIF round trip on files; import into DOORS Next and Polarion not yet tested"; test exports are "stubs to map in your tool".
- Study: say the 23 discussions are mostly embedded and QA.
- Add "What a clean result means" and a pilot call to action.

## 11. Open questions and risks

| Item | Note |
|---|---|
| Pilot price and selling entity | Not decided; needed before the first pilot |
| Who signs: requirements, V&V or programme | Test in the first five conversations |
| Works council and per-person timing | Check before any German pilot |
| ALM checkers bundled free and called "good enough" (high) | Answer with the side-by-side offer |
| Vector or dSPACE add a checking layer (medium-high) | They hold the bench and the customer |
| Self-graded evidence | Engineer-reviewed answer key on the roadmap; no company data run yet |
| AI reviewer noise, 60 percent recurrence | Lead code-only |
| Local model quality unknown | Run the pack on Ollama before any air-gap pitch |
| Eight tool names | Buyers cannot tell the one job; simplify the front door |
| No forcing event | EU AI Act dates moved; ASPICE AI guidance seen only in training and blog sources. Do not sell on regulation |
| Evidence for assessors | Test only after the team server is proven |
