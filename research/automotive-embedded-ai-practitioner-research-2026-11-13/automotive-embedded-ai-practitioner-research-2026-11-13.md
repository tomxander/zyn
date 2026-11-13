# What automotive and embedded engineers want from AI engineering tools

**Research date: 13 November 2026. Preferred evidence window: 13 November 2024–13 November 2026.**

**Product conclusion:** Start with a source-grounded assistant that helps engineers inspect existing work and prepare small, editable changes. Make verification, review and integration part of the product. The evidence does not justify launching with autonomous safety analysis, autonomous requirements baselining, or a promise of a fixed percentage of total engineering savings.

This is a qualitative public-source study, not a representative industry survey. Every source used below was opened; search-result-only material was excluded. All practitioner examples are paraphrases. No participants were contacted.

## Evidence and counting method

The registry contains **41 distinct sources**: 27 community/issue records and 14 supplementary research, survey, historical, conference or vendor records. **23 community discussions** enter the frequency counts: P01–P15, P17–P23 and P25. P16 and P24 have conflicting date displays; P26 is process context; P27 contains a vendor announcement and a role-unverified local-model question. These four are supplementary.

A count is the number of distinct eligible threads/articles containing at least one relevant independent user statement, **once per theme per thread**, never comments or votes. Multiple themes can occur in one thread. These are observed source counts, not percentages of engineers, companies or market demand. Thread independence does not guarantee different people or companies; repeated contributors occur, and identities were not investigated. No cross-posted opener or repeated anecdote was counted twice.

For mixed threads, builder proposals, vendor claims and promotional replies do not establish user demand. The counted material comes from independent replies or firsthand use descriptions. Anonymous occupations and affiliations cannot be verified; “practitioner” means a self-described work context, not authenticated employment. P20 includes hobby contexts, P21 is a competition experiment, and P22’s employment context is unknown. These limit transferability.

**Only P01, P03, P12 and P13 contain explicit firsthand automotive-work identification in the counted material.** Even these do not establish OEM-versus-Tier-1 coverage. Adjacent regulated work and general QA are labeled throughout. German- and Japanese-language sources were read in their original language and paraphrased in English.

Confidence describes the evidence for the stated pattern: **high** = repeated concrete accounts across relevant sources; **medium** = narrower or partly inferred; **low** = isolated, indirect or missing automotive evidence. High confidence that a problem occurs is not high confidence about its prevalence.

## 1. Ten findings that should most change what you build

1. **Make review of existing work a first product mode. — High; automotive transfer medium.** Supplementary bug, requirement-quality and coverage checks recur more often than demands for independent completion. Findings must be dismissible and explainable. This does not mean AI can certify correctness. [P02][P04][P06][P25]

2. **The smallest useful artifact is often an editable draft or patch. — High in mixed embedded/QA; automotive medium.** Support bounded transformations, selected components and existing templates. Keep the engineer in charge of intended behavior. [P09][P10][P23]

3. **Total review effort is a primary success metric. — High.** Fast generation can create slower engineering. Measure preparation, validation, rework and maintenance alongside generation time. The independent productivity evidence also warns against relying on perceived gains. [P02][R05][R06]

4. **Source access alone will not earn trust. — High for the problem; medium for the design response.** Engineers report wrong low-level facts despite supplying documentation. Provide inspectable source spans, exact versions and checks that the cited text actually supports the result. A model-written citation is another claim to verify. [P03][P18][P19]

5. **Offer repeatable generators for repetitive structured cases. — Medium for the account; low breadth.** One automotive tester would validate a DBC-based template/generator rather than hundreds of varying generated cases. A deterministic generation path is worth testing even though it appears in only one eligible thread. [P01]

6. **Integrate with the team’s information model and workflow. — High process constraint; medium AI-placement evidence.** Export friction, review navigation and configuration work can overwhelm the benefit. An AI app that requires rebuilding the ALM process inherits this burden. [P06][P11][P12]

7. **Private operation can be a purchase gate even when its count is low. — High veto severity; prevalence unknown.** NDA-protected embedded inputs can prevent a cloud-only tool from being usable at all. Separate true offline operation, customer cloud hosting and approved external inference in the product offer. [P14][P15]

8. **Generated tests need an independently justified expected result. — High in QA; automotive validation medium.** Cases can follow existing bugs, assert little, or multiply redundant scenarios. Provide a reviewable oracle and evidence the test can detect a fault; test volume is a poor success measure. [P07][P08][P09]

9. **Safety, security and RFQ workflows have very different evidence depth. — High confidence in this gap.** The strongest TARA evidence here is research/prototype evaluation, including older studies. RFQ evidence does not validate an AI product. These should be separate discovery and pilot tracks. [R08][R09][R13]

10. **Do not make adoption a test of loyalty or an implied headcount reduction. — Medium generally; low automotive prevalence.** Some users associate forced usage with stress and lost competence. Preserve opt-in task selection and credit engineers for finding mistakes. Positioning that makes them the accountable reviewer of unbounded output invites resistance. [P17][P23]

## 2. Ranked wanted capabilities and where the pain is

### Capabilities ranked by observed source frequency

“Wanted” includes explicit requests and reported useful work. Where a capability is inferred from a failure or an existing workflow, that is stated. **Frequency is not product priority:** a rare NDA veto can matter more than a common convenience.

| Rank | Capability | Independent sources, of 23 | Evidence basis and limits | Confidence |
|---|---|---:|---|---|
| 1 | Supplementary review and gap suggestions | **10** — [P01](#p01), [P02](#p02), [P03](#p03), [P04](#p04), [P06](#p06), [P07](#p07), [P08](#p08), [P10](#p10), [P23](#p23), [P25](#p25) | Explicit requests and reported use; includes dissent about analytical traceability. | High for bounded assistance; medium for automotive demand |
| 2 | Small editable script, test and documentation drafts | **9** — [P01](#p01), [P02](#p02), [P03](#p03), [P08](#p08), [P09](#p09), [P10](#p10), [P21](#p21), [P23](#p23), [P25](#p25) | Reported use and requests; successful use is not universal. | High in mixed embedded/QA; medium automotive |
| 3 | Grounded document/code discovery and accurate context | **7** — [P03](#p03), [P06](#p06), [P07](#p07), [P14](#p14), [P18](#p18), [P19](#p19), [P25](#p25) | Explicit requests plus inferred requirement from documented context failures. | High as a need; medium for a specific retrieval design |
| 4 | Build, failure, log and debugging assistance | **7** — [P03](#p03), [P07](#p07), [P08](#p08), [P10](#p10), [P20](#p20), [P23](#p23), [P25](#p25) | Reported use; general QA failure analysis and embedded logs are different tasks. | Medium; automotive-specific evidence low |
| 5 | Work inside current ALM/model/IDE/CLI workflows | **6** — [P05](#p05), [P06](#p06), [P11](#p11), [P12](#p12), [P13](#p13), [P15](#p15) | Mix of explicit rejection, existing integrations and underlying process demand. | High workflow constraint; medium AI placement preference |
| 6 | Change-impact and traceability maintenance | **4** — [P04](#p04), [P05](#p05), [P11](#p11), [P13](#p13) | Two AI/model experiences plus two underlying workflow problems; not four proven AI wins. | Medium for pain; low–medium for AI benefit |
| 7 | Requirement formatting, wording and model-consistency assistance | **3** — [P04](#p04), [P05](#p05), [P06](#p06) | Specific systems-engineering feedback; mathematical derivation remains disputed. | Medium |
| 8 | Private deployment / control of data egress | **2** — [P14](#p14), [P15](#p15) | Explicit NDA objections and enterprise self-hosting request; P27 adds uncounted corroboration. | High as a veto for affected teams; unknown prevalence |
| 9 | Repeatable generation through validated templates | **1** — [P01](#p01) | One automotive testing account; high product relevance despite low frequency. | Medium for that account; low market breadth |

**Not validated by these counts:** autonomous TARA; automatic automotive CVE disposition; AI as a MISRA compliance authority; RFQ-to-quotation automation; autonomous safety requirements approval. Each has **zero eligible firsthand product-demand or successful deployment sources specifically establishing that capability**. Related concerns, traditional tools, prototypes or studies exist; absence here is a research gap, not proof there is no market. [R04][R08][R09][R13]

### Pain and effort categories ranked by mentions in the coded material

This separates present workflow friction from a wish for AI. Counts indicate that a work/effort category was discussed; not every contributing author called it tedious or a failure. They include accounts of work made harder by AI, which matters because your product can create the same burden.

| Rank | Pain / where time goes | Sources | What the evidence supports |
|---|---|---|---|
| 1 | Inspecting and correcting candidate artifacts | **14**: [P01](#p01), [P02](#p02), [P03](#p03), [P04](#p04), [P05](#p05), [P06](#p06), [P07](#p07), [P08](#p08), [P09](#p09), [P10](#p10), [P18](#p18), [P19](#p19), [P21](#p21), [P23](#p23) | Rechecking intent, facts, logic and generated structure is a recurring cost; no industry time share can be estimated. |
| 2 | Repetitive scripts, tests and documentation | **8**: [P01](#p01), [P02](#p02), [P03](#p03), [P08](#p08), [P09](#p09), [P10](#p10), [P23](#p23), [P25](#p25) | Useful candidates for bounded assistance, with mixed actual results. |
| 3= | Finding context and fitting fragmented workflows | **7**: [P03](#p03), [P06](#p06), [P07](#p07), [P11](#p11), [P12](#p12), [P13](#p13), [P15](#p15) | Information is spread across tools, documents and people; supplying it is real work. |
| 3= | Debugging builds, failed tests and logs | **7**: [P03](#p03), [P07](#p07), [P08](#p08), [P10](#p10), [P20](#p20), [P23](#p23), [P25](#p25) | Existing evidence suggests useful assistance, but CAN/ECU log root-cause triage is not separately established. |
| 5 | Maintaining traces and understanding changes | **4**: [P04](#p04), [P05](#p05), [P11](#p11), [P13](#p13) | Modeling, link maintenance and identifying affected downstream work remain manual in these accounts. |
| 6 | ALM setup, training and migration | **3**: [P11](#p11), [P12](#p12), [P13](#p13) | Process ownership and configuration matter; changing products does not automatically change the process. |

There is **no defensible hours-by-task breakdown** for automotive requirements, audits or test design in this corpus. One safety-adjacent team describes roughly three days handling downstream change impact; this is an isolated team account. An aerospace-adjacent migration ran longer than planned; the information-model decisions, rather than raw import, were difficult. Neither is an automotive average. [P13][P11]

### What engineers say about existing tools

| Tool family | Observed user feedback | Implication for your product |
|---|---|---|
| DOORS / DOORS Next | Users value structured traceability while criticizing navigation, training, custom configuration and clicks; some defend DOORS when the process works. These products and installations should not be conflated. [P11][P12] | Connect to existing schemas, IDs and reviews. Do not sell replacement based on a generic “old UI” claim. |
| Codebeamer | Mixed process/repository feedback; migration can preserve old frustrations. A local-model question exists in its community. [P11][P12][P27] | Pilot against an actual configured tracker and repository integration. |
| Polarion / Jama | Users disagree on usability. Pricing and imposed-workflow objections appear alongside successful use. [P12][P13] | Support the customer’s approved lifecycle, exports and external-review access; avoid declaring a universal winner. |
| Jira and test management | Ticket text often omits enough context for meaningful generated tests. [P07] | Retrieve relevant specifications, changes and prior tests, and ask about missing information. |
| CANoe / dSPACE | Direct searches mainly surfaced vendor capabilities; no opened independent user evaluation qualified for this report. | Treat CAPL, HIL and SIL integration quality as unvalidated until tested with practitioners. |
| Static analyzers / MISRA | The automotive vendor survey indicates existing standards and static-analysis use, but does not validate an LLM replacement. [R04] | A proposed AI layer should explain and organize actual analyzer results, preserving the underlying evidence. |
| MATLAB / Simulink | One user reports bad configuration advice and switching assistants; the exact assistant is ambiguous. [P22] | Tool-specific answers need version checks; embedding an assistant does not guarantee domain accuracy. |

## 3. Ranked rejections and deal-breakers

These are **observed objections or negative experiences**, not counts of complete refusal. Hard veto evidence is strongest for unapproved data disclosure; other objections can be reduced by narrowing the task.

| Rank | Rejection | Independent sources, of 23 | Interpretation | Confidence |
|---|---|---:|---|---|
| 1 | Unreviewed artifacts or loss of engineering control | **12** — [P01](#p01), [P02](#p02), [P03](#p03), [P04](#p04), [P05](#p05), [P06](#p06), [P07](#p07), [P08](#p08), [P09](#p09), [P10](#p10), [P21](#p21), [P23](#p23) | Mostly objections and desired boundaries; not twelve blanket AI refusals. | High |
| 2 | Plausible false facts, requirements or logic | **9** — [P02](#p02), [P03](#p03), [P04](#p04), [P05](#p05), [P06](#p06), [P07](#p07), [P18](#p18), [P19](#p19), [P21](#p21) | Includes false precision and missing constraints; not all reports were reproduced. | High |
| 3 | Correction/review costs consume the saving | **8** — [P01](#p01), [P02](#p02), [P03](#p03), [P06](#p06), [P08](#p08), [P18](#p18), [P21](#p21), [P23](#p23) | Measured anecdotes are self-reports; manual counterfactuals usually estimates. | High for occurrence; unknown frequency in industry |
| 4 | Missing application, hardware or architectural context | **7** — [P03](#p03), [P04](#p04), [P05](#p05), [P07](#p07), [P18](#p18), [P21](#p21), [P23](#p23) | Reported limitation across embedded and RE; no universal model-quality claim. | High |
| 5 | Bloated, brittle or weak tests/code | **5** — [P07](#p07), [P08](#p08), [P09](#p09), [P10](#p10), [P23](#p23) | General QA dominates the test evidence. | High in these accounts; medium automotive transfer |
| 6 | Autonomous analytical derivation or architecture decisions | **4** — [P04](#p04), [P05](#p05), [P06](#p06), [P23](#p23) | Practitioners retain control; some actively use constrained agents. | Medium |
| 7 | Forced adoption, skill loss and job-pressure effects | **4** — [P02](#p02), [P17](#p17), [P23](#p23), [P25](#p25) | Mixed developer sentiment; not evidence all engineers reject automation. | Medium overall; low automotive prevalence |
| 8 | Export friction or a tool that imposes the wrong process | **4** — [P06](#p06), [P11](#p11), [P12](#p12), [P13](#p13) | Several are ALM complaints independent of AI. | High process concern; medium AI-specific |
| 9 | Unpredictable cost, licensing or lock-in | **4** — [P05](#p05), [P12](#p12), [P15](#p15), [P17](#p17) | Mix of token concerns, ALM pricing and enterprise deployment cost questions. | Medium; low automotive AI willingness-to-pay evidence |
| 10 | Sensitive IP sent outside approved boundaries | **2** — [P14](#p14), [P15](#p15) | Only two eligible discussions; vendor claims do not count as successful mitigation. | High veto severity; low–medium prevalence confidence |
| 11 | Different generated artifacts on repeated runs | **2** — [P01](#p01), [P05](#p05) | Explicit repeatability objection; output replay is a proposed mitigation. | Medium |
| 12 | Unavailable regional service / no backend choice | **1** — [P22](#p22) | One mainland-China availability complaint, not a regional adoption rate. | Low breadth, direct user request |

**Specific refusal conditions to design around:** a mandatory external upload of protected inputs; a workflow requiring painful export/reimport; unsupported authoritative-looking results; large outputs the assigned reviewer cannot competently inspect; or automatic acceptance into an approved baseline. The first two have explicit user objections; the last three combine observed objections with product-design inference. [P14][P06][P23]

**Agentic tools are not universally rejected.** Users also report successful constrained agents, small commits and instrument feedback. The supported boundary is around scope, verification and ownership. This corpus does not establish acceptance of unattended flashing, modifying safety logic or changing expected test outcomes. [P10][P20][P23]

**Reactions to vendor productivity percentages:** no opened eligible thread directly tests a specific vendor percentage in an automotive team. There is broad skepticism toward hype and reports of both benefit and extra work. Sell a measurable pilot, not a borrowed percentage. [P02][P23]

METR’s early-2025 randomized experiment found **19% longer task completion** for 16 experienced open-source developers across 246 tasks, despite their perception of improvement. Its **February 2026 update** says later tools likely help more, but selection effects and time measurement prevent a reliable current estimate. Both are general software evidence, not automotive benchmarks. [R05][R06]

## 4. Must have, should have, avoid

The following is a **product recommendation derived from the evidence**, not a list of universally stated user requirements.

| Must have for an initial pilot | Should have after proving value | Avoid |
|---|---|---|
| Read existing requirements/code/tests with stable IDs and versions. | Additional ALM connectors selected by actual customer usage. | Requiring a complete ALM migration to try the AI. |
| Source-linked suggestions with explicit unknowns and assumptions. | Cross-document conflict and terminology checks. | Invented missing values, clauses or source references. |
| Small editable drafts, diffs, accept/reject and clear reviewer ownership. | Project-specific formatting and model-to-text transformations. | Automatic baselining or approving safety/security decisions. |
| Existing compiler, analyzer and test execution evidence when available. | Bounded execution in an approved bench or simulation environment. | LLM “MISRA compliant” or “fully tested” labels unsupported by checks. |
| A deployment option compatible with the pilot’s data restrictions. | Customer-managed model endpoints and a separately validated offline package. | Calling a customer cloud tenancy “air-gapped.” |
| Baseline comparison and explicit handling of stale source versions. | Reviewed change-impact and suspected-link suggestions. | Silently rewriting approved requirements or expected results. |
| End-to-end effort measurement and a manual fallback. | Finding deduplication and persistent review dispositions. | Counting generated requirements, tests or tokens as business value. |
| Deterministic parsing/validation for structured inputs. | Validated DBC-derived templates and approved reusable generators. | Nondeterministic regeneration of an already accepted large artifact set. |
| Per-project data boundaries and constrained write permissions. | Supplier package exchange and review-only access. | Indexing unrelated customers or exposing unauthorized material through retrieval. |

**Suggested first release:** requirement-quality review and narrowly scoped test drafting from an approved source set, connected to one customer ALM and one actual test stack. Offer log/build assistance as a separate bounded workflow. Do not assume that the same model/context setup works equally well for requirement extraction, CAPL, MISRA explanations, TARA and commercial RFQs.

**Suggested next experiment:** use AI to help author and check a reusable test generator, then produce cases through a validated structured path. This recommendation has narrow direct evidence and should be tested, not presented as a settled market preference. [P01]

## 5. Trust requirements: what the engineer should be able to inspect

The common demand is for a result an engineer can challenge and verify. The detailed acceptance design below is an **inference** from the reported failures and review workflows.

| Artifact | Evidence to show with every candidate | Engineer keeps |
|---|---|---|
| Extracted requirement / RFQ obligation | Exact source span, document revision, page/section, parent ID, original units, and whether the text was extracted or inferred. Flag conflicting clauses and unreadable tables. | Scope interpretation, contractual meaning and acceptance. |
| Rewritten / derived requirement | Before/after diff; affected IDs; assumptions; rationale and source basis. Separate arithmetic from generated prose. | Architecture choices, budget allocation and baseline approval. |
| Test case | Requirement and revision; preconditions; stimulus; expected result and its authority; boundary rationale; distinction between a new idea and an approved case. | Test intent, coverage sufficiency and acceptance of the oracle. |
| Test script | Candidate diff; exact stack/toolchain version; compile/run command; execution result; raw logs; environment and unresolved warnings. | Approval to run against hardware and product systems. |
| MISRA / unit-test analysis | Analyzer name/version/configuration, rule identifier and edition, actual finding, proposed change and rerun result. Preserve deviations and suppression rationale. | Compliance and deviation decisions; LLM explanations remain advisory. |
| CVE / TARA suggestion | Component/version evidence, applicability/reachability argument, source timestamps, attack prerequisites, existing controls and explicit unresolved assumptions. | Risk ratings, accepted risk and security sign-off. |
| Log / defect hypothesis | Referenced lines/events/timestamps, observed symptom versus hypothesis, supporting and conflicting evidence, and a reproducible next check. | Root-cause conclusion and repair authorization. |

Practical interaction: **select scope → inspect supporting evidence → inspect a small diff → run existing checks → approve or reject**. Retrieval must respect existing access controls; show when a source baseline changes after generation. Keep the accepted artifact, model/configuration identity and evidence available for replay.

**Confidence scores:** this corpus does not establish demand for a percentage badge or show that a model’s self-confidence predicts correctness. Prefer concrete support states such as “source text located,” “assumption unresolved,” “compiled,” and “executed in environment X.” A citation alone does not establish completeness.

**Traceability:** distinguish the existence of a link, evidence that the link is semantically appropriate, and evidence that the requirement is actually satisfied. These are different claims. Use deterministic checks for missing IDs or broken links; AI can propose semantic relationships for review. [P06]

**Repeatability:** storing and replaying an accepted output is different from making a model regenerate identical output. Offer immutable accepted versions and deterministic downstream generation where suitable. The exact mechanisms are design proposals, not documented assessor approvals.

## 6. Adoption blockers, practical workarounds and adoption reality

| Blocker | What is actually evidenced | How users have progressed / what remains proposed |
|---|---|---|
| IP and customer NDA restrictions | Embedded users explicitly reject external sharing. [P14] | Restrict use to approved material or use approved private deployment. No opened source proves a particular vendor’s promises resolved an automotive NDA review. |
| Company product-code bans | Embedded users report bans without enough detail on employer, policy or reason. [P23] | Separate permissible tasks from prohibited ones. No verified automotive reversal of a ban was found. |
| Local deployment quality/capacity | An enterprise requester wants private multi-IDE tooling. [P15] A Codebeamer user separately asks for local models. [P27] | Benchmark the permitted model on real work. No apples-to-apples automotive local-versus-hosted quality comparison was found; private hosting is not evidence of parity. |
| Missing/fragmented inputs | Requirements and tests lack necessary product context. [P07][P13] | Users narrow scope and reuse context/examples. Fix source ownership and baselines before scaling generation. |
| Review capacity | Users describe excessive correction. [P23] Embedded maintainers independently document scarce review capacity. [P26] | Small changes and explicit task boundaries have positive user reports. Do not remove approval gates merely to increase generation throughput. |
| Qualification / assessor uncertainty | An assurance-service provider discusses intended use and error detection. [R10] | Prepare a specific workflow and error-detection argument for the customer’s review. No opened source documents an accepted production AI workflow under ASPICE, ISO 26262 or ISO/SAE 21434. |
| Tool/process ownership | ALM frustrations persist without consistent processes. [P11][P12] | Existing API integrations and tool administrators help. The organizational owner matters as much as the connector. |
| Regional service access | One mainland-China user asks for configurable backends. [P22] | Backend choice is a plausible mitigation; no successful rollout is verified here. |
| Stress and competence concerns | General developers report pressure and skill-loss fears. [P17] | Preserve task choice, training and the ability to work manually. Effects on automotive retention are unknown. |

**TISAX and export control:** no opened firsthand automotive account establishes either as the specific cause of a ban or describes a successful exception. Do not claim “TISAX forbids AI,” equate private hosting with compliance, or infer export permission from deployment location. These are customer-specific approval questions for discovery, not findings established by this study.

**Accountability:** users retain review and ownership in the reported useful workflows. The rail discussion reinforces the tension between review capacity and sign-off, but it is adjacent and date-uncertain. Forum comments about criminal liability or what an assessor legally requires are not reliable legal conclusions. [P10][P24]

### Tools actually mentioned in use

- **Embedded work:** Claude Code, GitHub Copilot, Gemini, ChatGPT, DeepSeek, and documentation-oriented NotebookLM use appear in firsthand discussions. Tasks span helper scripts, code understanding, review, build troubleshooting and limited generation. This is a mention list, not a market-share ranking. [P02][P03][P25]
- **General QA:** reviewed case drafts, Gemini CLI, Copilot-driven draft PRs, GitLab Duo pipeline analysis and Playwright assistance appear. These do not establish automotive HIL or CAPL performance. [P08][P09][P10]
- **Systems engineering:** Cameo/MCP/Claude and repeated model/context upload are described. This is early experimentation, not enterprise-scale deployment evidence. [P04][P05]
- **Official versus shadow use:** some users describe employer-provided access. Others describe personal subscriptions, without establishing what data was used or whether it violated policy. No automotive shadow-use rate can be estimated. [P15][P18][P25]

**Reported positive results also have concrete limits:** one embedded user says Claude Code found a CMake problem in five minutes after two hours of unsuccessful manual investigation; that is a single self-reported incident. A general web tester describes about 80% of generated journey-test work as satisfactory and spends effort guiding or fixing the rest; this is not an automotive effort-saving measurement. [P03][P10]

**What appears to stick:** narrow tasks, known examples, reusable context, small review units and access to actual test/debug feedback. **What makes users stop or reduce use:** interrupting suggestions, incorrect specialized answers, long correction loops and disappointing real behavior. These are individual/team anecdotes; there is no longitudinal automotive retention study here. [P02][P03][P21][P22][P23]

### Buyer versus user

| Group | Evidence-supported concern | Evaluation implication |
|---|---|---|
| Hands-on engineer | Correct intent, understandable changes, fewer tedious steps, manageable review. | Demonstrate a useful result on a real task and include all validation time. |
| Engineering manager | Throughput and staff capacity can motivate AI pressure; the clearest direct tension is general software/QA. [P08][P17] | Show quality-adjusted throughput and reviewer load, not just generation speed. |
| Tool owner / ALM administrator | Schema fit, workflow, deployment, training and integration burden. [P11][P13][P15] | Use the customer’s configuration and access model in the pilot. |
| Safety/security/process owner | Evidence, controlled decisions and demonstrable error detection. Automotive TARA interviews are primarily manager/consultant evidence. [R09][R10] | Define the permitted use and review evidence with the organization before scaling it. |

**What buyers actually ask for in this corpus:** private deployment, compatibility across existing tools, licensing/integration cost and process fit. A representative automotive AI procurement checklist, acceptable price range and preferred pricing model were **not found**. A builder proposing a low price is not a buyer accepting it. [P06][P15]

**Recommended POC design — our proposal, not observed consensus:** compare matched real tasks with and without the tool; keep the quality bar constant; include familiar and unfamiliar subsystems and deliberately incomplete inputs. Record context preparation, generation, review, correction, execution and later maintenance time. Measure accepted artifacts, important errors missed, false suggestions and reviewer effort. Have engineers and process owners independently assess the evidence. Use customer-agreed success thresholds; do not invent an industry benchmark.

## 7. Segment differences and limits

### By role

| Role | Supported direction | Confidence / limitation |
|---|---|---|
| Requirements / systems engineer | Formatting, clarity and consistency help; retain stakeholder interpretation, model coherence and analytical derivation. [P04][P05][P06] | Medium; mostly general systems engineering. |
| Embedded software developer | Scripts, code understanding, bounded changes and supplementary review; hardware/toolchain context matters. [P18][P23][P25] | High mixed embedded; medium automotive transfer. |
| Test / validation engineer | Editable tests, useful oracles, maintainable scripts and real execution; template validation deserves a pilot. [P01][P08][P09] | Medium automotive; general QA evidence is richer. |
| Functional safety engineer | Evidence and scope control; willingness to use AI differs. [P24][R10] | Low direct automotive user evidence; rail and commercial commentary are supplementary. |
| Cybersecurity engineer | Applicability and evidence are more promising than raw alert volume. [P16][R08] | Low current automotive deployment evidence. |
| Quality / ASPICE staff | Process ownership, controlled baselines and review evidence are plausible product needs. [P11][P13] | Low role-specific AI evidence; no authenticated ASPICE assessor interview. |

### By region

| Region | Evidence available | What you can conclude |
|---|---|---|
| Germany / EU | German-language embedded discussion; European automotive research; historical GitHub regional survey. [P20][R03][R09] | Mixed enthusiasm and caution exist. Language does not establish employer/location; no German OEM preference estimate. |
| US | English-language forums generally lack reliable location; the historical enterprise survey includes US respondents. [R03] | Insufficient current automotive-specific comparison. Do not assume English Reddit is a US sample. |
| Japan | A Japanese competition account by an automotive-experienced author, plus commercial safety commentary. [P21][R10] | Useful Japanese-language examples; insufficient production-team adoption evidence. |
| India | The historical enterprise survey includes India; an automotive reply mentions outsourced testing there. [R03][P01] | Neither establishes Indian engineers’ own wants. Direct automotive user evidence is missing. |
| China | One MATLAB Central reply reports a service-access obstacle and requests alternative backends. [P22] | A concrete access hypothesis to validate; insufficient Chinese automotive preference data. |

**Language needs are unvalidated beyond the usefulness of local-language access and preserved technical terminology.** The corpus does not rank English, German, Japanese, Chinese or Indian-language requirements for this product. Proposed multilingual support should preserve source wording, identifiers, units and review diffs; interview actual cross-language teams before prioritizing.

### By company type

- **OEM:** no reliable direct comparison of OEM buyers and users. Proposed needs such as supplier-package boundaries and system-level impact remain hypotheses.
- **Tier-1:** no adequate independent AI-evaluation sample. Automotive statements do not reliably identify supplier tier.
- **Engineering service provider:** customer restrictions and customer-specific workflows are plausible constraints, but no sufficient independent sample establishes their purchasing or pricing preferences.
- **Adjacent regulated companies:** aerospace, defense and medical accounts help explain traceability and workflow friction. They do not demonstrate automotive assessor acceptance. [P11][P12]

Do not turn these gaps into regional or organizational stereotypes.

## 8. Short practitioner examples for the major findings

These are paraphrases, never reconstructed quotes. Full source dates and caveats follow in section 10.

| Finding | Short example | Platform / date / source |
|---|---|---|
| Repeatability over mass output | A former automotive tester would check the generator rather than inspect every generated case. | Reddit, 2026-05-11 — [P01] |
| Review cost can reverse gains | Factory scripts took longer after repeated AI corrections. | Reddit, 2025-09-01 — [P02] |
| Preserve engineering derivation | A requirements user still checks end-to-end coherence against a functional model. | Reddit, 2026-05-15 — [P04] |
| Workflow can veto adoption | A systems respondent rejects exporting to another tool for checks already available. | Reddit, exact day unavailable; indexed about 1.8 years old — [P06] |
| Test intent can be wrong | QA users describe cases that interpret a reported defect as intended behavior. | Reddit, thread 2025-03-24 — [P08] |
| IP can block use outright | Embedded commenters cannot upload NDA-protected material. | Hacker News, 2025-08-15–16 — [P14] |
| Data/context failure is expensive | An automation engineer rechecks sensor code after invented calibration data. | Reddit, exact day unavailable; approximately 2026-01/02 — [P18] |
| Grounded transformation still needs validation | A competition participant constrained a code port, tested it, then abandoned that approach. | Qiita, 2025-08-30 — [P21] |
| Integration alone does not ensure quality | A Simulink user switches assistant after incorrect configuration help. | MATLAB Central, 2026-10-27 — [P22] |
| Adoption affects work experience | Developers describe pressure and fear of losing competence. | Reddit, 2026-03-07 — [P17] |

## 9. Evidence gaps and what to validate next

| Gap | What is missing | Best next research |
|---|---|---|
| Automotive savings and retention | Controlled measurements and sustained team usage, separated by task. | Observe several real tasks through review and later maintenance; follow usage after a pilot. |
| Requirements extraction / RFQ | Independent production evaluation on real OEM/customer packs; handling of tables, diagrams, ambiguous obligations and contract changes. | Watch a requirements engineer and bid owner process an actual authorized pack, including rejected or clarified clauses. |
| HIL/SIL/CAPL generation | Independent compile/run/maintain results on configured CANoe/dSPACE benches. | Compare generated candidates with the team’s existing generator and manual process. |
| MISRA advice quality | Specific firsthand evaluations of LLM explanations, edition accuracy and deviation handling. | Evaluate explanations against actual analyzer findings and approved guideline material. |
| Automotive CVE triage | Production evidence on affected versions, reachability, false dispositions and SBOM quality. | Blind-review proposed dispositions against security engineers’ decisions and unresolved cases. |
| TARA | Recent hands-on adoption, complex attack-path quality, sustained updates and actual assessment acceptance. | Interview practitioners and assessors separately; test candidate suggestions without delegating risk acceptance. |
| Standards and qualification | Accepted AI use cases with documented intended use, error detection and assessment outcome. | Obtain permissioned case records; generic certificate claims are insufficient. |
| Deployment restrictions | Firsthand TISAX/export-control cases, air-gap operation details and evidence that an exception succeeded. | Interview security, customer-contract and deployment owners alongside the user. |
| Local versus hosted quality | Matched automotive tasks under the same input and evaluation protocol. | Benchmark actual permitted models and infrastructure; measure latency and operator cost. |
| Buyer economics | Real POC criteria, budgets, pricing acceptance and total integration/support cost. | Interview budget holders after showing concrete task results; test commercial terms directly. |
| Regional/company differences | Current users from OEMs, Tier-1s and service firms in Germany/EU, US, Japan, India and China. | Recruit by named role and company type, with source-language interviews. |
| Job/skill effects | Automotive-specific pressure, competence and review fatigue over time. | Observe training and review work; do not infer attitudes from general developer forums. |

### Search coverage and access limitations

Every requested community family received a direct domain/subreddit search. This was a bounded public-web search, not an exhaustive crawl.

| Requested source family | Outcome |
|---|---|
| r/embedded, r/AutomotiveEngineering, r/systems_engineering | Opened and used; strongest directly relevant discussion evidence. |
| r/softwaretesting, r/QualityAssurance, r/ExperiencedDevs, r/LocalLLaMA, r/cybersecurity | Opened and used with general-software/enterprise labels. Date-uncertain security thread supplementary. |
| r/ECE, r/cpp, r/C_Programming | Searched directly; results were predominantly student, moderation, general-language or unrelated material. No source qualified for a major finding. |
| Automotive/functional-safety subreddits | Searched for relevant specialized discussions; the useful safety example was in r/embedded and concerns rail. No dedicated-community sample established. |
| Hacker News | Opened a relevant embedded vendor-launch discussion; independent replies used, founder claims excluded. |
| Stack Overflow; Electrical Engineering, Software Engineering and SQA Stack Exchange | Searched each directly; no sufficiently relevant current professional automotive account qualified. Older testing answers and beginner questions were not generalized. |
| EEVblog; EmbeddedRelated; Mikrocontroller.net | Opened all three. EmbeddedRelated evidence was old and excluded from counts; hobby/professional ambiguity preserved. |
| Qiita; Zenn | Opened the Qiita experiment. A potentially relevant Zenn book could not be fetched; no claims based on its search excerpt. |
| PTC Codebeamer; IBM DOORS; Siemens Polarion; Jama communities | PTC user request and IBM vendor demo opened. Siemens page returned only a shell; Jama search mainly returned vendor material. No invented independent adoption testimony. |
| Vector; dSPACE; MathWorks | Searched directly. Vector opening timed out; dSPACE results were vendor material, not counted. A MathWorks user thread was opened and used. |
| Blind; Glassdoor; kununu | Searched directly; no relevant accessible engineering-tool testimony qualified. General employer reviews and job advertisements excluded. |
| LinkedIn | Searched practitioner posts; relevant-looking automotive post could not be fetched. Vendor pilots and influential general posts were not treated as user evidence. No comment-thread conclusions claimed. |
| YouTube comments / conference Q&A | Direct searches did not produce an accessible qualifying comment/Q&A corpus. No claimed sentiment from video titles, descriptions or unseen comments. |
| GitHub issues/discussions | Opened Zephyr issue and comments through the GitHub connector; included as process context only. |
| Surveys/studies | Opened Stack Overflow, JetBrains, GitHub, Perforce, METR and practitioner RE/TARA research. Commercial provenance and denominators retained. |
| Embedded World, ASPICE/functional safety, ELIV, SAE WCX, Automotive IQ | Searched these event families; opened ELIV programme. Agendas and promotional abstracts did not establish practitioner opinion or delivered results. |

**What this study can decide:** a strong starting product hypothesis and specific failure conditions to design and test. **What it cannot decide:** automotive market prevalence, purchasing preference, accepted safety assurance, or a trustworthy productivity percentage.

## 10. Full dated source registry

All sources accessed **2026-11-13**. “Exact day unavailable” is deliberate: no dates were invented from relative ages. Some rendered ages conflict with indexed dates. P16/P24 are excluded from frequency counts; P06 retains the discrepancy but both age displays are consistent with approximately early 2025. Unopened results and failed pages are not research evidence.

### Community and issue records

<a id="p01"></a>

**P01. [Embedded/Automotive testers — how manual is your test case generation process today?](https://www.reddit.com/r/embedded/comments/1t9plap/embeddedautomotive_testers_how_manual_is_your/)**  
Platform: Reddit / r/embedded. Date: 2026-05-11.  
Scope/provenance: Automotive; former hands-on tester, current testing work unclear; mixed commercial replies. **Counted once per applicable theme.**  
A practitioner preferred validating a Python/DBC generator or template to reviewing hundreds of newly generated cases. A separate HIL-tool promoter's reply is excluded from counts.

<a id="p02"></a>

**P02. [AI and productivity](https://www.reddit.com/r/embedded/comments/1n5y1yu/ai_and_productivity/)**  
Platform: Reddit / r/embedded. Date: 2025-09-01.  
Scope/provenance: Embedded / industrial automation; anonymous firsthand account. **Counted once per applicable theme.**  
An engineer reports seven hours on factory automation scripts versus an estimated three manually, after outdated syntax and repeated correction. Replies report useful scaffolding and supplementary review.

<a id="p03"></a>

**P03. [Do you actually use AI for embedded development? What's your experience?](https://www.reddit.com/r/embedded/comments/1odxmka/do_you_actually_use_ai_for_embedded_development/)**  
Platform: Reddit / r/embedded. Date: 2025-10-23; replies include 2025-10-25–27.  
Scope/provenance: Embedded, with one explicitly automotive respondent. **Counted once per applicable theme.**  
Uses include Gemini snippet review, Claude Code build debugging and Copilot unit tests. Failures include wrong registers and fabricated datasheet references. One automotive respondent prototypes then rewrites product code.

<a id="p04"></a>

**P04. [AI can generate requirements. Can it make them decision-ready?](https://www.reddit.com/r/systems_engineering/comments/1tdqn6p/ai_can_generate_requirements_can_it_make_them/)**  
Platform: Reddit / r/systems_engineering. Date: 2026-05-15.  
Scope/provenance: Systems engineering; mixed practitioner, researcher and builder replies. **Counted once per applicable theme.**  
A work user still builds the functional model and manually checks traces, but finds cross-topic consistency checking useful. Builder promotions and a researcher's repeated-generation experiment are excluded from practitioner counts.

<a id="p05"></a>

**P05. [Anyone else experimenting with LLMs for requirements derivation? Curious how you're handling traceability.](https://www.reddit.com/r/systems_engineering/comments/1uvpqq5/anyone_else_experimenting_with_llms_for/)**  
Platform: Reddit / r/systems_engineering. Date: Exact day unavailable; rendered 4 months old at access.  
Scope/provenance: Systems engineering; builder opener, independent user replies. **Counted once per applicable theme.**  
Replies support note-to-requirement formatting and report Cameo/MCP/Claude state-machine-to-EARS work. Others reject outsourcing derivation and question nondeterminism. The builder's proposed features are not counted as demand.

<a id="p06"></a>

**P06. [AI Enhanced Requirements Management Tool](https://www.reddit.com/r/systems_engineering/comments/1igdo0x/ai_enhanced_requirements_management_tool/)**  
Platform: Reddit / r/systems_engineering. Date: Exact day unavailable; search indexes about 1.8 years old; page rounds to 2 years.  
Scope/provenance: Systems engineering; builder opener and independent replies. **Counted once per applicable theme.**  
A respondent wants clarity/verifiability checking but rejects export-first workflows and AI budget allocation. Replies distinguish semantic discovery from link checks already possible with a filter. The proposed $30–50 price is not willingness-to-pay evidence.

<a id="p07"></a>

**P07. [Test management tools in the modern era](https://www.reddit.com/r/softwaretesting/comments/1tsuwhl/test_management_tools_in_the_modern_era/)**  
Platform: Reddit / r/softwaretesting. Date: 2026-05-31; later replies separately undated.  
Scope/provenance: General software; opener specifies web and API. **Counted once per applicable theme.**  
A tester finds ticket-based generated cases unusable without application context. Replies report better results with narrow component context, test maintenance and coverage-gap suggestions. Product recommendations are treated cautiously.

<a id="p08"></a>

**P08. [Have You Used AI-Generated Test Cases? How Was Your Experience?](https://www.reddit.com/r/QualityAssurance/comments/1jil8pw/have_you_used_aigenerated_test_cases_how_was_your/)**  
Platform: Reddit / r/QualityAssurance. Date: 2025-03-24; some later replies in 2025–26.  
Scope/provenance: General QA; anonymous hands-on users; promotional replies excluded. **Counted once per applicable theme.**  
Users report draft generation, reusable prompts and occasional missed-scenario discovery. Other accounts describe poor documentation, brittle cases or bug reports being mistaken for intended behavior. Results vary within the thread.

<a id="p09"></a>

**P09. [AI for Test Case creation](https://www.reddit.com/r/QualityAssurance/comments/1o65t38/ai_for_test_case_creation/)**  
Platform: Reddit / r/QualityAssurance. Date: 2025-10-14.  
Scope/provenance: General QA; anonymous practitioner accounts. **Counted once per applicable theme.**  
A lone tester wants editable assistance. Gemini CLI users describe useful output alongside weak assertions, missing boundaries and deleted tests; another reports excessive assumed or redundant BrowserStack cases.

<a id="p10"></a>

**P10. [What tasks are software testers successfully using AI for?](https://www.reddit.com/r/softwaretesting/comments/1uw31ve/what_tasks_are_software_testers_successfully/)**  
Platform: Reddit / r/softwaretesting. Date: 2026-07-14.  
Scope/provenance: General QA / web; practitioner and builder replies. **Counted once per applicable theme.**  
Users describe reviewed test plans and draft PRs, script boilerplate, documentation, broken-pipeline analysis and Playwright assistance. The extension creator's pitch is excluded.

<a id="p11"></a>

**P11. [DOORS is making my team miserable, what did you migrate to and do you regret it](https://www.reddit.com/r/embedded/comments/1szvgk3/doors_is_making_my_team_miserable_what_did_you/)**  
Platform: Reddit / r/embedded. Date: 2026-04-30.  
Scope/provenance: Regulated embedded; automotive, defense, medical and aerospace-adjacent replies. **Counted once per applicable theme.**  
Practitioners describe click-heavy reviews, difficult V&V navigation, custom configuration and migration effort. One aerospace-adjacent migration took roughly five months versus three planned. An automotive reply describes a docs/code correlation workflow; vendors are excluded.

<a id="p12"></a>

**P12. [DOORS alternatives that don't feel ancient?](https://www.reddit.com/r/embedded/comments/1s48jja/doors_alternatives_that_dont_feel_ancient/)**  
Platform: Reddit / r/embedded. Date: Exact day unavailable; rendered 7 months old at access.  
Scope/provenance: Regulated embedded; explicit automotive respondent; promotional replies excluded. **Counted once per applicable theme.**  
An automotive user says a DOORS-to-Codebeamer move preserved the process. Other users report Jama pricing/workflow friction and small-project TRLC/Git usage with Polarion for larger projects. These are user reports, not verified current product comparisons.

<a id="p13"></a>

**P13. [our requirements process is just vibes at this point, what are you actually using](https://www.reddit.com/r/systems_engineering/comments/1t68sro/our_requirements_process_is_just_vibes_at_this/)**  
Platform: Reddit / r/systems_engineering. Date: 2026-05-07.  
Scope/provenance: Safety-adjacent team; automotive/defense R&D and aerospace replies. **Counted once per applicable theme.**  
The opener reports about three days tracing stakeholder changes through fragmented documents. Replies emphasize configuration control and ownership; an automotive/defense user objects to paying extra for ReqIF functionality.

<a id="p14"></a>

**P14. [Launch HN: Embedder — Claude code for embedded software](https://news.ycombinator.com/item?id=44915206)**  
Platform: Hacker News. Date: 2025-08-15–16.  
Scope/provenance: Embedded practitioners responding to a vendor launch. **Counted once per applicable theme.**  
Independent commenters reject sending NDA-protected schematics/source to outside services, question hallucination-removal claims, and suggest structured register descriptions. Founder promises and results are marketing and excluded from counts.

<a id="p15"></a>

**P15. [AI for software development team in enterprise](https://www.reddit.com/r/LocalLLaMA/comments/1qj4m3p/ai_for_software_development_team_in_enterprise/)**  
Platform: Reddit / r/LocalLLaMA. Date: 2026-01-21.  
Scope/provenance: General enterprise tooling; requester represents about 300 developers; exact role unverified. **Counted once per applicable theme.**  
The requester wants self-hosted tools across IntelliJ, VS Code and Eclipse, plus CLI support. Infrastructure, serving capacity and pricing arise in discussion; suggested vendor privacy guarantees are not verified.

<a id="p16"></a>

**P16. [How are you triaging an AI-sized vulnerability backlog?](https://www.reddit.com/r/cybersecurity/comments/1xsgfpx/how_are_you_triaging_an_aisized_vulnerability/)**  
Platform: Reddit / r/cybersecurity. Date: Indexed absolute date 2026-11-10; rendered relative age inconsistent.  
Scope/provenance: General enterprise security; anonymous firsthand account; date discrepancy. **Supplementary; excluded from frequency counts.**  
A security team reports more than 4,000 findings, repetitive reopened tickets and an approval bottleneck. Suggestions favor reachability, grouping and remembered dispositions. Its sample of 100 is an anecdote, not a false-positive-rate estimate.

<a id="p17"></a>

**P17. [Purposely limiting AI usage](https://www.reddit.com/r/ExperiencedDevs/comments/1rnie42/purposely_limiting_ai_usage/)**  
Platform: Reddit / r/ExperiencedDevs. Date: 2026-03-07.  
Scope/provenance: General software; practitioners and one self-described leader. **Counted once per applicable theme.**  
Users describe stress, skill atrophy and higher output expectations. A leader reports benefits partly consumed by review and conflicting agents. This community cannot establish automotive workforce sentiment.

<a id="p18"></a>

**P18. [AI hallucinations in embedded](https://www.reddit.com/r/embedded/comments/1qhyyom/ai_hallucinations_in_embedded/)**  
Platform: Reddit / r/embedded. Date: Exact day unavailable; search says 9 months old, page 10 months.  
Scope/provenance: Industrial automation engineer; firsthand account. **Counted once per applicable theme.**  
An automation engineer using Claude Sonnet 4.5 reports invented calibration values and incorrect sensor-identification logic, leading to line-by-line checking. The report's register claims are the engineer's account, not an independently reproduced hardware test.

<a id="p19"></a>

**P19. [AI in low level embedded systems](https://www.eevblog.com/forum/chatgptai/ai-in-low-level-embedded-systems/)**  
Platform: EEVblog. Date: 2025-05-18; reviewed replies dated 2025-05-29.  
Scope/provenance: Electronics practitioners/hobbyists; course promoter distinguished. **Counted once per applicable theme.**  
The opener questions convincing but wrong low-level code; one reply shows successive incorrect pin-routing constants before correction. A course-promoting reply also reports a successful bug find; its commercial affiliation is explicit.

<a id="p20"></a>

**P20. [Claude Code meets AVR assembler: from chip to browser with one prompt](https://www.mikrocontroller.net/news/claude-code-trifft-avr-assembler-vom-chip-in-den-browser-mit-einem-prompt)**  
Platform: Mikrocontroller.net, German. Date: Reviewed comments 2026-08-20–23; article edited 2026-10-26.  
Scope/provenance: Mixed hobby/embedded; industry employment not verified. **Counted once per applicable theme.**  
A commenter reports Claude-assisted ESP-IDF work and uses Wireshark exports while independently checking interfaces. Other comments debate lost knowledge and correction limits. This is German-language evidence, not a German OEM sample.

<a id="p21"></a>

**P21. [Using ChatGPT to create C++ MPC code for the Autonomous Driving AI Challenge 2025](https://qiita.com/Massy0127/items/57bde16c9c02929a17bf)**  
Platform: Qiita, Japanese. Date: 2025-08-30.  
Scope/provenance: Author reports automotive experience; competition experiment, not production. **Counted once per applicable theme.**  
Initial generated MPC code failed to build or follow curves. Constraining a port of existing Python code helped, but vehicle behavior still disappointed and the author switched back to a different control approach.

<a id="p22"></a>

**P22. [Copilot is absolutely horrid and actually wastes much more time than it helps](https://www.mathworks.com/matlabcentral/discussions/ai/891041-copilot-is-absolutely-horrid-and-actually-wastes-much-more-time-than-it-helps)**  
Platform: MathWorks MATLAB Central. Date: 2026-10-27; relevant reply 2026-10-29.  
Scope/provenance: Simulink user, role/employer unverified; independent community posts. **Counted once per applicable theme.**  
The opener reports incorrect block-configuration advice and switches to ChatGPT. A reply reports mainland China availability limitations and asks for configurable LLM backends. The exact assistant used by the opener is ambiguous.

<a id="p23"></a>

**P23. [Are you satisfied with LLMs code quality in embedded software domain?](https://www.reddit.com/r/embedded/comments/1w7frel/are_you_satisfied_with_llms_code_quality_in/)**  
Platform: Reddit / r/embedded. Date: 2026-09, approximate; exact opener day unavailable; dated reply 2026-09-05.  
Scope/provenance: Embedded practitioners; opener says not senior; anonymous. **Counted once per applicable theme.**  
The opener reports hours checking each feature despite an agent workflow. Replies describe successful atomic changes and logic-analyzer feedback; another reports a stack-usage regression. Product-code bans are reported without enough detail to identify their cause.

<a id="p24"></a>

**P24. [AI in Safety-Critical application](https://www.reddit.com/r/embedded/comments/1x3wek3/ai_in_safetycritical_application/)**  
Platform: Reddit / r/embedded. Date: Date unresolved: index says last month; rendered page says 9 hours old.  
Scope/provenance: Adjacent rail SIL4; conflicting practitioner views; supplementary only. **Supplementary; excluded from frequency counts.**  
A rail engineer doubts large generated code reviews; replies support human-owned commits and supplementary checks, while some refuse generated product code. Forum statements about legal liability, EASA and DO-330 are not treated as authoritative.

<a id="p25"></a>

**P25. [Embedded in the Age of AI](https://www.reddit.com/r/embedded/comments/1skjuze/embedded_in_the_age_of_ai/)**  
Platform: Reddit / r/embedded. Date: 2026-04-13.  
Scope/provenance: Embedded practitioners and hobbyists; some employer-funded use. **Counted once per applicable theme.**  
Users report small helper scripts, first-pass log analysis, better Jira tickets and build-output summaries. They keep core engineering responsibility and note undocumented constraints. Employer-paid Gemini, Copilot and Claude Code are mentioned.

<a id="p26"></a>

**P26. [PR review backlog: data, examples, and proposed mechanisms — issue 109444](https://github.com/zephyrproject-rtos/zephyr/issues/109444)**  
Platform: GitHub / Zephyr. Date: Created 2026-05-19; updated 2026-06-16.  
Scope/provenance: Embedded open-source maintainers; supplementary only. **Supplementary; excluded from frequency counts.**  
The issue documents reviewer scarcity; comments debate AI review. A posted Gemini-assisted meeting summary says automatic merging after inactivity was rejected. That summary is not independently verified meeting minutes; no automotive adoption inference is made.

<a id="p27"></a>

**P27. [Codebeamer AI 1.0 release — local-model request](https://community.ptc.com/codebeamer-445/codebeamer-ai-1-0-has-released-171154?fid=445&tid=171154)**  
Platform: PTC Community. Date: Vendor announcement 2025-12-19; user question 2026-01-19.  
Scope/provenance: Vendor marketing opener; unaffiliated user role unverified; supplementary only. **Supplementary; excluded from frequency counts.**  
A community user asks for locally hosted LLM configuration/API support. Only this request is treated as user feedback; all performance and capability claims in the announcement are marketing.

### Research, surveys, history, conference and vendor records

<a id="r01"></a>

**R01. [2025 Stack Overflow Developer Survey — AI](https://survey.stackoverflow.co/2025/ai)**  
Date: 2025; exact page publication day unavailable. Provenance: Stack Overflow survey; platform-published, self-selected general developer sample.  
46% distrust accuracy versus 33% trust; 84% use or plan to use. This is general software sentiment, not an automotive adoption estimate.

<a id="r02"></a>

**R02. [State of Developer Ecosystem 2025](https://blog.jetbrains.com/research/2025/10/state-of-developer-ecosystem-2025/)**  
Date: 2025-10; exact day unavailable. Provenance: JetBrains; tool-vendor survey/marketing.  
24,534 respondents in 194 countries; reports 85% regular AI use and preference for delegating repetitive tasks. Self-reported gains and the vendor's framing require caution.

<a id="r03"></a>

**R03. [Survey: The AI wave continues to grow on software development teams](https://github.blog/news-insights/research/survey-ai-wave-grows/?trk=public_post_comment-text)**  
Date: 2024-08-20; updated 2025-04-15; underlying fieldwork 2024-02-26–03-18 — OLDER. Provenance: GitHub; tool-vendor sponsored survey/marketing.  
2,000 enterprise non-manager respondents in four countries. Reported organizational permission/encouragement differs between US and Germany. Historical regional context only; not automotive or a measured shadow-use rate.

<a id="r04"></a>

**R04. [Perforce's 2025 State of Automotive Software report announcement](https://www.perforce.com/press-releases/perforces-2025-state-automotive-software-report)**  
Date: 2025-03-11. Provenance: Perforce; automotive tool-vendor survey/marketing.  
53% report static analysis use and 86% use at least one coding standard. Much AI coverage concerns AI inside vehicles, so it must not be read as adoption of LLM engineering assistants. Only the announcement was inspected.

<a id="r05"></a>

**R05. [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity](https://arxiv.org/abs/2507.09089)**  
Date: Study blog 2025-07-10; opened arXiv version dated 2025-07-12. Provenance: METR; independent randomized study, general open-source software.  
16 developers, 246 tasks, experienced in their repositories; early-2025 tools increased completion time 19%. Participants perceived a gain. A narrow historical result, not a current embedded benchmark.

<a id="r06"></a>

**R06. [We are Changing our Developer Productivity Experiment Design](https://metr.org/blog/2026-02-24-uplift-update/)**  
Date: 2026-02-24. Provenance: METR; independent follow-up and methodological limitations.  
Later observations suggest improvement, but participant/task selection and concurrent-agent time measurement undermine a reliable current effect estimate. This prevents treating the 2025 slowdown as timeless.

<a id="r07"></a>

**R07. [AI for Requirements Engineering: Industry Adoption and Practitioner Perspectives](https://research.chalmers.se/publication/551468)**  
Date: 2025 proceedings; repository updated 2026-04-13. Provenance: Academic practitioner survey; general RE, not established automotive subsample.  
55 practitioners; 58.2% report AI use in RE; human-AI collaboration accounts for 54.4% of mapped RE techniques, full automation 5.4%. These denominators are not all developers or automotive teams.

<a id="r08"></a>

**R08. [Cybersecurity requirements identification using LLMs — A design science study](https://odr.chalmers.se/items/dae0ade7-85c2-4f86-b243-b9cd235f1918)**  
Date: 2024; exact month/day unavailable — potentially outside 24 months; historical only. Provenance: Academic master's thesis with automotive expert evaluation; prototype, not deployment.  
Grounding in CVE and Automotive-ISAC material produced useful initial security requirements; attack-path outputs were less consistent. It does not establish production TARA acceptance or reduced review effort.

<a id="r09"></a>

**R09. [Elevating TARA: A Maturity Model for Automotive Threat Analysis and Risk Assessment](https://epub.uni-regensburg.de/58666/6/Vielberth_D2TARA_TrustBus2024.pdf)**  
Date: 2024-07-30 — OLDER. Provenance: Academic industrial interviews; five cybersecurity managers and two senior consultants; not a hands-on AI adoption survey.  
Seven experts valued maintained source pools, current information and integration with TARA platforms. Rating mappings needed explicit treatment. The authors say the model had not yet been used in real projects.

<a id="r10"></a>

**R10. [Is Tool Qualification Required When Creating FMEA or Test Cases with Generative AI?](https://note.com/sakuraiautosafe/n/n4fc46e751469?hl=en)**  
Date: 2026-09-14. Provenance: Commercial safety-assurance provider/consultant commentary; machine-translated page; not a standard or acceptance record.  
Frames qualification around intended tool use and how errors are detected, rather than a universal AI certificate. Used only as professional interpretation; it is not proof of assessor approval.

<a id="r11"></a>

**R11. [ChatGPT for Embedded Systems Development — Share your Stories Here!](https://www.embeddedrelated.com/thread/16049/chatgpt-for-embedded-systems-development-share-your-stories-here)**  
Date: Reviewed replies 2023-03-02 — OLDER. Provenance: EmbeddedRelated forum; mixed hobby/practitioner/editor roles.  
Reports include plausible but broken LED and circuit examples and fixes that introduced other faults. Historical context only; no current-model frequency counts.

<a id="r12"></a>

**R12. [ELIV 2025 congress programme](https://www.vdi-wissensforum.de/fileadmin/VDI_Wissensforum/Veranstaltungen/Highlights/ELIV/Programm/ELIV_2025.pdf)**  
Date: Event 2025-10-15–16; publication day unavailable. Provenance: Conference organizer programme; corporate presentations; not practitioner feedback.  
Lists sovereign generative AI for requirements-to-tests and agentic engineering sessions. An agenda proves topic interest, not delivered outcomes, audience reactions or adoption.

<a id="r13"></a>

**R13. [Looking for someone to talk to about the RFQ process](https://www.reddit.com/r/AutomotiveEngineering/comments/1n5jr3p/looking_for_someone_to_talk_to_about_the_rfq/)**  
Date: 2025-09-01. Provenance: Reddit; former supplier/product-research opener and one role-unverified process reply; supplementary.  
The reply describes iterative requirements–RFI–RFQ–negotiation loops and supplier feedback. It provides no firsthand AI tool evaluation, task timing or willingness to pay.

<a id="r14"></a>

**R14. [Try it yourself: Requirements AI assistant for DOORS Next](https://community.ibm.com/community/user/blogs/daniel-moul/2025/02/13/requirements-ai-assistant-for-doors-next?hlmlt=QT)**  
Date: 2025-02-13. Provenance: IBM staff demonstration; tool-vendor marketing.  
An in-module demonstrator sends module text to cloud services; it is explicitly not a product and omits some attribute data. No adoption or productivity inference is drawn.

### Direct source-link definitions

[P01]: https://www.reddit.com/r/embedded/comments/1t9plap/embeddedautomotive_testers_how_manual_is_your/
[P02]: https://www.reddit.com/r/embedded/comments/1n5y1yu/ai_and_productivity/
[P03]: https://www.reddit.com/r/embedded/comments/1odxmka/do_you_actually_use_ai_for_embedded_development/
[P04]: https://www.reddit.com/r/systems_engineering/comments/1tdqn6p/ai_can_generate_requirements_can_it_make_them/
[P05]: https://www.reddit.com/r/systems_engineering/comments/1uvpqq5/anyone_else_experimenting_with_llms_for/
[P06]: https://www.reddit.com/r/systems_engineering/comments/1igdo0x/ai_enhanced_requirements_management_tool/
[P07]: https://www.reddit.com/r/softwaretesting/comments/1tsuwhl/test_management_tools_in_the_modern_era/
[P08]: https://www.reddit.com/r/QualityAssurance/comments/1jil8pw/have_you_used_aigenerated_test_cases_how_was_your/
[P09]: https://www.reddit.com/r/QualityAssurance/comments/1o65t38/ai_for_test_case_creation/
[P10]: https://www.reddit.com/r/softwaretesting/comments/1uw31ve/what_tasks_are_software_testers_successfully/
[P11]: https://www.reddit.com/r/embedded/comments/1szvgk3/doors_is_making_my_team_miserable_what_did_you/
[P12]: https://www.reddit.com/r/embedded/comments/1s48jja/doors_alternatives_that_dont_feel_ancient/
[P13]: https://www.reddit.com/r/systems_engineering/comments/1t68sro/our_requirements_process_is_just_vibes_at_this/
[P14]: https://news.ycombinator.com/item?id=44915206
[P15]: https://www.reddit.com/r/LocalLLaMA/comments/1qj4m3p/ai_for_software_development_team_in_enterprise/
[P16]: https://www.reddit.com/r/cybersecurity/comments/1xsgfpx/how_are_you_triaging_an_aisized_vulnerability/
[P17]: https://www.reddit.com/r/ExperiencedDevs/comments/1rnie42/purposely_limiting_ai_usage/
[P18]: https://www.reddit.com/r/embedded/comments/1qhyyom/ai_hallucinations_in_embedded/
[P19]: https://www.eevblog.com/forum/chatgptai/ai-in-low-level-embedded-systems/
[P20]: https://www.mikrocontroller.net/news/claude-code-trifft-avr-assembler-vom-chip-in-den-browser-mit-einem-prompt
[P21]: https://qiita.com/Massy0127/items/57bde16c9c02929a17bf
[P22]: https://www.mathworks.com/matlabcentral/discussions/ai/891041-copilot-is-absolutely-horrid-and-actually-wastes-much-more-time-than-it-helps
[P23]: https://www.reddit.com/r/embedded/comments/1w7frel/are_you_satisfied_with_llms_code_quality_in/
[P24]: https://www.reddit.com/r/embedded/comments/1x3wek3/ai_in_safetycritical_application/
[P25]: https://www.reddit.com/r/embedded/comments/1skjuze/embedded_in_the_age_of_ai/
[P26]: https://github.com/zephyrproject-rtos/zephyr/issues/109444
[P27]: https://community.ptc.com/codebeamer-445/codebeamer-ai-1-0-has-released-171154?fid=445&tid=171154
[R01]: https://survey.stackoverflow.co/2025/ai
[R02]: https://blog.jetbrains.com/research/2025/10/state-of-developer-ecosystem-2025/
[R03]: https://github.blog/news-insights/research/survey-ai-wave-grows/?trk=public_post_comment-text
[R04]: https://www.perforce.com/press-releases/perforces-2025-state-automotive-software-report
[R05]: https://arxiv.org/abs/2507.09089
[R06]: https://metr.org/blog/2026-02-24-uplift-update/
[R07]: https://research.chalmers.se/publication/551468
[R08]: https://odr.chalmers.se/items/dae0ade7-85c2-4f86-b243-b9cd235f1918
[R09]: https://epub.uni-regensburg.de/58666/6/Vielberth_D2TARA_TrustBus2024.pdf
[R10]: https://note.com/sakuraiautosafe/n/n4fc46e751469?hl=en
[R11]: https://www.embeddedrelated.com/thread/16049/chatgpt-for-embedded-systems-development-share-your-stories-here
[R12]: https://www.vdi-wissensforum.de/fileadmin/VDI_Wissensforum/Veranstaltungen/Highlights/ELIV/Programm/ELIV_2025.pdf
[R13]: https://www.reddit.com/r/AutomotiveEngineering/comments/1n5jr3p/looking_for_someone_to_talk_to_about_the_rfq/
[R14]: https://community.ibm.com/community/user/blogs/daniel-moul/2025/02/13/requirements-ai-assistant-for-doors-next?hlmlt=QT

