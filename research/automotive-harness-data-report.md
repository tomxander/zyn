# Public data and repositories for an automotive AI engineering harness

Checked **13 November 2026**. This report contains **41 individually described entries**; several serve more than one need. Rankings are recommendations based on task fit, ground truth, realism and published reuse terms, not download popularity.

The strongest practical starting point is a **pinned RTEMS specification/validation slice plus its matching RTEMS implementation**, with **QuRE** added for real automotive quality classification. Add **cantools** for network-format tests and **ROAD** for recorded vehicle traffic. There is no verified public substitute here for a complete OEM requirements→tests→results→defects/TARA evidence chain.

## 1. Ranked shortlist: best three to five per need

“Candidate” means a relevant published licence was found, subject to its conditions. “Conditional” limits the usable scope or requires per-file/source checks. “Hold” means no sufficient commercial grant was established for the relevant data. A hold item can still be a useful benchmark to pursue permission for.

| Need | Ranked shortlist (most useful first) | Why these |
|---|---|---|
| **1. Requirements extraction and classification** | 1. [R1 QuRE — Quality in Requirements](https://zenodo.org/records/16049822) — Candidate<br>2. [R2 PROMISE NFR and PROMISE_exp (verified mirror)](https://github.com/AleksandarMitrevski/se-requirements-classification) — Conditional<br>3. [R5 strictdoc-project/reqif](https://github.com/strictdoc-project/reqif) — Conditional<br>4. [T1 RTEMS requirements, validation and implementation](https://github.com/RTEMS/rtems-central) — Conditional<br>5. [R6 TOPPERS ASP3 Core and TTSP3](https://github.com/toppers/asp3_core) — Conditional | QuRE supplies real automotive quality labels. PROMISE supplies type labels; ReqIF supplies format oracles. RTEMS and TOPPERS add embedded contracts. |
| **2. Requirement-to-test traceability and test generation** | 1. [T1 RTEMS requirements, validation and implementation](https://github.com/RTEMS/rtems-central) — Conditional<br>2. [T2 StrictDoc — self specifications and traceability](https://github.com/strictdoc-project/strictdoc) — Conditional<br>3. [H1 NASA FRET](https://github.com/NASA-SW-VnV/fret) — Candidate<br>4. [T6 COMET replication datasets — iTrust and LibEST](https://gitlab.com/SEMERU-Code-Public/Data/icse20-comet-data-replication-package) — Hold<br>5. [T3 EasyClinic, English TraceLab distribution](https://github.com/CoEST/TraceLab/tree/master/Main/Benchmarks/Datasets/EasyClinic_ENG) — Hold for data | RTEMS has explicit executable validation links; LibEST and EasyClinic have actual requirement/use-case-to-test data. CM1/eTOUR are useful different trace tasks. |
| **3. CAN and vehicle network data** | 1. [N1 opendbc](https://github.com/commaai/opendbc) — Candidate<br>2. [N5 ROAD — Real ORNL Automotive Dynamometer CAN dataset](https://zenodo.org/records/10462796) — Candidate<br>3. [N2 cantools](https://github.com/cantools/cantools) — Conditional<br>4. [N3 python-can](https://github.com/hardbyte/python-can) — Candidate<br>5. [N4 ICSim — Instrument Cluster Simulator](https://github.com/zombieCraig/ICSim) — Candidate with copyleft | Real vehicle definitions and recorded traffic, parser gold values, transport/replay and a scriptable simplified cluster. |
| **4. Embedded C/C++ verification** | 1. [V1 FreeRTOS-Kernel](https://github.com/FreeRTOS/FreeRTOS-Kernel) — Conditional<br>2. [V2 Zephyr](https://github.com/zephyrproject-rtos/zephyr) — Conditional<br>3. [T1 RTEMS requirements, validation and implementation](https://github.com/RTEMS/rtems-central) — Conditional<br>4. [V4 Cppcheck regression and MISRA-addon tests](https://github.com/cppcheck-opensource/cppcheck) — Candidate with copyleft<br>5. [V5 NIST SARD Juliet C/C++ 1.3](https://samate.nist.gov/SARD/test-suites/112) — Candidate | Real C and tests first; analyzer regression and synthetic weakness suites provide deterministic positive/negative oracles. |
| **5. Cybersecurity, TARA, SBOM, VEX and licence scanning** | 1. [S2 V2X PKI formal verification and TARA artifact](https://github.com/bhamsec/v2x-pki-formal-verification) — Candidate<br>2. [S4 CycloneDX BOM examples](https://github.com/CycloneDX/bom-examples) — Candidate<br>3. [S3 SPDX usage examples](https://github.com/spdx/spdx-examples) — Candidate with file distinctions<br>4. [S6 OSV code and offline vulnerability dumps](https://github.com/google/osv.dev) — Conditional; restricted sources on hold<br>5. [S1 OpenASC catalogs](https://github.com/steflokos/openasc-catalogs) — Candidate | Worked V2X assets/threats/requirements, low-friction BOM documents, source-filtered vulnerability data and an AI-assisted automotive catalog. |
| **6. Defect and log analysis** | 1. [D1 COVESA dlt-daemon and DLT fixtures](https://github.com/COVESA/dlt-daemon) — Candidate with file copyleft<br>2. [D2 BMW Car IT python-dlt](https://github.com/bmwcarit/python-dlt) — Candidate with file copyleft<br>3. [D4 Eclipse issue report dataset (Issuex)](https://zenodo.org/records/15348468) — Conditional<br>4. [D3 GitBugs](https://github.com/av9ash/gitbugs) — Conditional<br>5. [D5 Loghub](https://github.com/logpai/loghub) — Hold | DLT fixtures are domain-close; bug datasets provide duplicates; Loghub is a domain-transfer comparator with commercial permission unresolved. |
| **7. Reusable harness components and agent benchmarks** | 1. [H1 NASA FRET](https://github.com/NASA-SW-VnV/fret) — Candidate<br>2. [T2 StrictDoc — self specifications and traceability](https://github.com/strictdoc-project/strictdoc) — Conditional<br>3. [H5 OSV-Scanner](https://github.com/google/osv-scanner) — Code candidate; feeds conditional<br>4. [H4 SWE-bench harness and SWE-bench Verified](https://github.com/SWE-bench/SWE-bench) — Conditional<br>5. [V4 Cppcheck regression and MISRA-addon tests](https://github.com/cppcheck-opensource/cppcheck) — Candidate with copyleft | Formal requirement/test generation, traceability plumbing, deterministic triage, reproducible agent evaluation and static checks. |

## Verification and interpretation

GitHub was searched first. Follow-up discovery covered Hugging Face, Zenodo, Kaggle, Papers with Code, GitLab and standards-body sources. Repository/dataset pages were opened; files, licence notices and default-branch commit metadata were inspected through GitHub or public APIs. Zenodo's rendered pages sometimes hid licence values, so the corresponding public record JSON was checked and saved. Unopenable candidates were not admitted as recommendations. No star counts are used.

The research also rejected a Kaggle requirements mirror whose card says **“Unknown”** for its licence: [Software Requirements Dataset](https://www.kaggle.com/datasets/iamsouvik/software-requirements-dataset/data). No additional suitable item was established through the Papers with Code searches. Neither result proves that a better source cannot exist there.

Counts are maintainer/record/paper statements, not estimates from repository storage or generated LOC counts. Where no defensible count was published, the entry explicitly says so. Published benchmark configurations can differ from repository snapshots; this is flagged instead of merging incompatible counts. “Last observed commit” is the most recent default-branch commit returned when checked, not the GitHub “updated” or “pushed” timestamp. Static data need not receive frequent commits to remain useful.

**Licence columns:** commercial internal use, redistribution and model input are assessed separately. Model input means copying/processing material for an internal evaluation or inference workflow. The same copyright scope applies when copying for fine-tuning; these older licences generally do not expressly discuss training. No entry should be read as a definitive ruling that trained weights or copied generated code avoid attribution/share-alike/copyleft obligations. Sending material to a third-party model service adds a disclosure/copying boundary and requires rights for that activity.

The licence quote is deliberately short. The assessment relies on the linked full notice, not on the quote alone. Repository-wide software licences do not automatically settle rights to imported documents, standards text, issue comments, attachments or third-party fixtures. A record-level CC licence is evidence of the depositor's grant, not proof that every underlying contributor granted those rights. No dataset was downloaded in bulk, no benchmark was executed and no proof/compliance result was independently reproduced.

## 2. Full inventory, grouped by need

### Need 1: Requirements extraction and classification

#### R1 — QuRE — Quality in Requirements

[Repository / dataset](https://zenodo.org/records/16049822) · Serves needs **1** · **Candidate**

Requirement text, weak-word categories and human quality-defect judgments. Strongest automotive quality-classification candidate; not a requirement-to-test dataset.

- **Size:** 2,111 industrial requirements; QuRE.csv 332.4 kB; replication ZIP 7.2 MB (record). Do not equate CSV rows with unique requirements.
- **Format / language:** CSV; Python notebooks/ZIP. English
- **Origin:** Real automotive industrial review data; author-released, anonymized requirements.
- **Labels / ground truth:** Human review labels for weak-word occurrence and ok/defect judgments.
- **Licence quoted:** “cc-by-4.0” — [licence evidence](https://zenodo.org/api/records/16049822).
- **Commercial internal use:** Yes under CC BY 4.0.
- **Redistribution:** Yes with attribution, licence reference and change indication.
- **Model input:** Yes with applicable attribution; not a waiver of other rights.
- **Freshness:** Release 1.0.1: 2025-07-17; record modified 2025-10-27. Static benchmark with a corrected replication package; no expectation of frequent commits.
- **Known problems:** Narrow industrial context; quality judgments depend on context. Split by unique requirement, not annotation row; no safety/interface class gold set or test oracle.

#### R2 — PROMISE NFR and PROMISE_exp (verified mirror)

[Repository / dataset](https://github.com/AleksandarMitrevski/se-requirements-classification) · Serves needs **1,7** · **Conditional**

Original and expanded functional/NFR corpora with categories such as security, usability and performance, plus classical classification baselines.

- **Size:** Original: 625 requirements (255 functional, 370 NFR); expanded: 969 (444 functional, 525 NFR), as stated by README.
- **Format / language:** ARFF; accompanying analysis notebooks/scripts. English
- **Origin:** Requirements from academic/public project specifications, manually classified; expanded material was collected using web searches.
- **Labels / ground truth:** FR/NFR plus NFR subclasses; expert-consensus labels described for expansion.
- **Licence quoted:** “Creative Commons Attribution-Share Alike 3.0 License” — [licence evidence](https://github.com/AleksandarMitrevski/se-requirements-classification/blob/master/0-datasets/PROMISE_exp/PROMISE_exp.arff).
- **Commercial internal use:** Original data header permits commercial use; expanded-source scope needs review; analysis code not cleared.
- **Redistribution:** Data under CC BY-SA 3.0, attribution/share-alike; code grant not verified.
- **Model input:** Conditional on source rights; do not assume a model/checkpoint's SA status is settled.
- **Freshness:** Last observed default-branch commit: [2021-05-31](https://github.com/AleksandarMitrevski/se-requirements-classification/commit/1f5dc4501a1956f21011083594d925bac49f198c). Last observed commit in 2021; static mirror, not maintained application software.
- **Known problems:** No repository-wide software licence file stated; data-file header supplies CC BY-SA 3.0. Do not assume analysis code is licensed by the data header. Web-source rights for expanded requirements need checking; imbalance and duplicate leakage across versions; not automotive or ASIL-labelled.

#### R3 — PURE — Public Requirements Documents

[Repository / dataset](https://zenodo.org/records/7118517) · Serves needs **1** · **Hold**

Full-document extraction material and a manually ported XML subset. Useful for layout and sentence extraction, but not inherently an ambiguity or FR/NFR gold set.

- **Size:** 79 documents; 34,268 sentences; record states 19 XML documents; 34.0 MB total.
- **Format / language:** PDF; XML; XSD; ZIP. English
- **Origin:** Real public specifications gathered from the web, across mixed domains.
- **Labels / ground truth:** Document structure/XML conversion and descriptive document metadata; no comprehensive requirement-type or quality-defect labels.
- **Licence quoted:** “cc-by-4.0” — [licence evidence](https://zenodo.org/api/records/7118517).
- **Commercial internal use:** Underlying document rights unestablished despite curator CC BY declaration.
- **Redistribution:** Not cleared for full underlying corpus.
- **Model input:** Not cleared for commercial input/training until source documents are cleared.
- **Freshness:** Version 2.0 record created 2022-09-28; publication field 2018-09-12; modified 2024-12-19. Static archive.
- **Known problems:** Curators explicitly say they are unaware of source-document licence agreements/IP rights and offer takedown. Record-level CC BY does not settle underlying rights. Hold the full corpus from commercial prompts/training or redistribution until individual documents are cleared; not evidence of an OEM leak by itself.

#### R4 — ReqEval — anaphora ambiguity

[Repository / dataset](https://github.com/frieden84/nlp4re-reqeval) · Serves needs **1** · **Hold**

Pronoun-level ambiguity labels and antecedent disambiguations, with training/test files.

- **Size:** 200 requirement statements from seven domains; 103 ambiguous requirements, stated by README.
- **Format / language:** TSV. English
- **Origin:** Real statements selected from PURE; human annotations.
- **Labels / ground truth:** Two annotators per requirement; nocuous/innocuous pronouns and disambiguation targets.
- **Licence quoted:** “Creative Commons Attribution 4.0 International License” — [licence evidence](https://github.com/frieden84/nlp4re-reqeval/blob/master/README.md).
- **Commercial internal use:** Underlying document rights unestablished despite curator CC BY declaration.
- **Redistribution:** Not cleared for full underlying corpus.
- **Model input:** Not cleared for commercial input/training until source documents are cleared.
- **Freshness:** Last observed default-branch commit: [2022-12-29](https://github.com/frieden84/nlp4re-reqeval/commit/05f42f83cca53c1d46e433e54b21e7f852cef7a5). Static shared-task corpus; last observed commit 2022.
- **Known problems:** Tiny and focused on anaphora, not all ambiguity/incompleteness. README assumes online old/completed project data does not infringe copyright; that assumption does not resolve PURE's underlying rights. No standalone licence file was verified; licence appears in README.

#### R5 — strictdoc-project/reqif

[Repository / dataset](https://github.com/strictdoc-project/reqif) · Serves needs **1,7** · **Conditional**

ReqIF parser/unparser, validation, formatting and anonymization; integration examples and malformed-format cases.

- **Size:** Sample/test-suite cardinality not stated by maintainer.
- **Format / language:** ReqIF/XML; Python; expected-output fixtures. English tooling/docs; fixture text varies and is not a validated multilingual corpus.
- **Origin:** Project-authored format tests plus samples obtained from the internet.
- **Labels / ground truth:** Round-trip/passthrough and formatting assertions; parser ground truth rather than requirement semantics.
- **Licence quoted:** “Apache License, Version 2.0” — [licence evidence](https://github.com/strictdoc-project/reqif/blob/main/LICENSE).
- **Commercial internal use:** Tool and own specifications yes; imported documents per file.
- **Redistribution:** Yes for licensed project files; do not assume imported examples cleared.
- **Model input:** Own material yes; imported samples need rights review.
- **Freshness:** Last observed default-branch commit: [2026-11-12](https://github.com/strictdoc-project/reqif/commit/6021dda83805c83e770efc464c35edd3a687e569). Active; observed commit 2026-11-12.
- **Known problems:** README explicitly says some samples were found online. Apache licence is clear for the tool; clear individual imported fixture provenance before commercial model ingestion. Anonymization does not itself create copyright permission.

#### R6 — TOPPERS ASP3 Core and TTSP3

[Repository / dataset](https://github.com/toppers/asp3_core) · Serves needs **1,2,4,7** · **Conditional**

A Japanese-language embedded source for API contract and test-scenario extraction. Companion TTSP3 publishes API/SIL tests and expected return codes.

- **Size:** ASP3 3.7.2 base; no published requirement/test count. README lists POSIX simulation and QEMU targets.
- **Format / language:** C/C headers; Japanese Markdown and TXT; test programs/configuration. Japanese engineering descriptions and test scenarios; English identifiers/mixed docs.
- **Origin:** Real embedded RTOS implementation plus adapted conformance tests; current fork supports AI-assisted development, without a per-file AI-authorship inventory.
- **Labels / ground truth:** API return-code assertions, checkpoints, conformance scenarios; no labelled Japanese natural-language requirement corpus.
- **Licence quoted:** “TOPPERSライセンス（TOPPERS License）” — [licence evidence](https://github.com/toppers/asp3_core/blob/main/LICENSE).
- **Commercial internal use:** ASP3 code permitted under TOPPERS conditions; TTSP3 per-file/document scope.
- **Redistribution:** Retain source/document notices, modification statements and applicable binary distribution conditions.
- **Model input:** Conditional on the specific file's grant; separate standards manuals excluded.
- **Freshness:** Last observed default-branch commit: [2026-09-01](https://github.com/toppers/asp3_core/commit/bcf9a04ff9d1970b1f25967c8caf4e7388f18aad). ASP3 Core observed commit 2026-09-01; TTSP3 observed commit 2026-07-06; active derivatives.
- **Known problems:** Core is an explicitly modified upstream kernel. TTSP3 has no root licence file stated: README and user.txt set document/per-source conditions. New test files need individual header checks; code licence is not a blanket licence for separate standards manuals. Not automotive OEM requirements.

Additional evidence: [TTSP3 repository](https://github.com/toppers/TTSP3); [TTSP3 document terms](https://github.com/toppers/TTSP3/blob/main/user.txt); [Official TOPPERS licence](https://www.toppers.jp/license.html).

#### R7 — Official AUTOSAR Requirements on CAN, R24-11

[Repository / dataset](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_RS_CAN.pdf) · Serves needs **1,2,3** · **Hold**

CAN requirement IDs, descriptions and traceability information. Excellent domain language and interface requirements, subject to separate rights.

- **Size:** 85 pages; requirement count not stated.
- **Format / language:** PDF. English
- **Origin:** Official automotive standards-body requirements.
- **Labels / ground truth:** Official requirement IDs and stated relations; no independent test-case/outcome gold set.
- **Licence quoted:** “commercial exploitation” — [licence evidence](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_RS_CAN.pdf).
- **Commercial internal use:** Not cleared by free download; requires applicable IP agreement.
- **Redistribution:** Not cleared by public posting.
- **Model input:** Not cleared for commercial prompts/training absent applicable permission.
- **Freshness:** Selected release: 2024-11-27 (R24-11); not represented as latest AUTOSAR release. AUTOSAR standard series maintained; this is a pinned older release.
- **Known problems:** Copyright/IP notice requires a licence for commercial exploitation. Public download does not authorize commercial internal AI use or redistribution. Use only after confirming your AUTOSAR agreement covers the activity. Exclude unofficial copies of ISO/MISRA/AUTOSAR manuals with unclear permissions.

### Need 2: Requirement-to-test traceability and test generation

#### T1 — RTEMS requirements, validation and implementation

[Repository / dataset](https://github.com/RTEMS/rtems-central) · Serves needs **1,2,4,7** · **Conditional**

Structured natural-language requirements, pre/postconditions, refinement/validation links and C test code. RTEMS/rtems provides the implementation and generated validation tests.

- **Size:** Partial RTOS specification and validation suite; maintainer does not state total requirement/test count.
- **Format / language:** YAML; C; Python; generated documentation and test/coverage artifacts. English
- **Origin:** Real safety-oriented embedded RTOS development and qualification artifacts.
- **Labels / ground truth:** Explicit validation links, transition/precondition/postcondition tables, expected status and event-set assertions, generated test target paths.
- **Licence quoted:** “CC-BY-SA-4.0 OR BSD-2-Clause” — [licence evidence](https://github.com/RTEMS/rtems-central/blob/master/spec/rtems/event/req/send-receive.yml).
- **Commercial internal use:** Yes for verified BSD-option specification/test slice; implementation per file.
- **Redistribution:** BSD conditions for chosen dual-licensed specs/tests; other RTEMS files per header.
- **Model input:** Yes for BSD slice; inspect implementation inputs individually.
- **Freshness:** Last observed default-branch commit: [2023-12-19](https://github.com/RTEMS/rtems-central/commit/82230386f0691791cbf0ea1ffac69337190d3ff5). GitHub specification snapshot commit 2023-12-19; GitLab successor marked 'Moved to Unmaintained 2026-06-12' (API verified). RTEMS implementation mirror observed commit 2026-11-12. Good frozen benchmark, not an actively maintained generator recommendation.
- **Known problems:** Partial specification, not an automotive product or certification claim. Keep generator, spec and RTEMS version aligned. Do not apply the dual licence to every RTEMS file; choose BSD for verified dual-licensed specs and BSD test files, and check implementation headers. Generate fresh results under your pinned simulator rather than treating historical logs as universal truth.

Additional evidence: [RTEMS implementation](https://github.com/RTEMS/rtems); [Validation link and target](https://github.com/RTEMS/rtems-central/blob/master/spec/rtems/event/val/send-receive.yml); [BSD-licensed generated test](https://github.com/RTEMS/rtems/blob/main/testsuites/validation/tc-event-send-receive.c).

#### T2 — StrictDoc — self specifications and traceability

[Repository / dataset](https://github.com/strictdoc-project/strictdoc) · Serves needs **1,2,7** · **Conditional**

Versioned specifications, source relations, tests and traceability reporting; useful both as target project and harness plumbing.

- **Size:** Specification/docs and test-suite counts not stated.
- **Format / language:** SDoc; Python; HTML; ReqIF; JUnit/Robot/GCov integration. English
- **Origin:** Real requirements-management tool specifying and testing its own behavior, plus synthetic format fixtures.
- **Labels / ground truth:** Requirement/refinement/source links, regression expected output and traceability validation. Not every requirement has a complete requirement-to-test-to-result chain.
- **Licence quoted:** “Apache License, Version 2.0” — [licence evidence](https://github.com/strictdoc-project/strictdoc/blob/main/LICENSE).
- **Commercial internal use:** Tool and own specifications yes; imported documents per file.
- **Redistribution:** Yes for licensed project files; do not assume imported examples cleared.
- **Model input:** Own material yes; imported samples need rights review.
- **Freshness:** Last observed default-branch commit: [2026-11-12](https://github.com/strictdoc-project/strictdoc/commit/1c9bacc03e2e10e6df6d8be9de45b42cde214791). Active; observed commit 2026-11-12.
- **Known problems:** Tool domain rather than automotive. Separate genuine project specifications from illustrative fixtures and imported documents. Do not treat document examples of standards templates as a licence to the underlying standard.

#### T3 — EasyClinic, English TraceLab distribution

[Repository / dataset](https://github.com/CoEST/TraceLab/tree/master/Main/Benchmarks/Datasets/EasyClinic_ENG) · Serves needs **2** · **Hold for data**

Use cases, test-case descriptions, code-class descriptions, interaction diagrams and explicit UC–TC answer links.

- **Size:** Published benchmark configurations include 30 use cases and 63 test cases; do not transfer link counts across versions. The opened XML files identify collection version 1.1.
- **Format / language:** XML artifact collections and answer matrices. English distribution translated from Italian; translation quality is visibly uneven.
- **Origin:** Real student healthcare project artifacts, not industrial automotive data.
- **Labels / ground truth:** Explicit positive trace links, including use-case-to-test-case relations. Descriptive tests, not a ready-to-run ECU test suite.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/CoEST/TraceLab/blob/master/LICENSE).
- **Commercial internal use:** TraceLab tool GPL permits internal commercial use; imported benchmark grant not established.
- **Redistribution:** Tool GPL obligations apply; original benchmark provenance unresolved.
- **Model input:** Hold original data until scope confirmed; tool GPL is not a substitute for document rights.
- **Freshness:** Last observed default-branch commit: [2016-10-17](https://github.com/CoEST/TraceLab/commit/a9c74bd4dadbc091c8f5e5efd9f6fd5d96d5b5f1). TraceLab repository observed commit 2016-10-17; archival benchmark.
- **Known problems:** GPL-3.0 repository licence was verified, but separate rights/provenance for the imported benchmark data were not established. Hold data commercially until scope is confirmed. Absence of a link is not necessarily proven semantic impossibility. Counts differ between published distributions.

Additional evidence: [UC–TC matrix](https://github.com/CoEST/TraceLab/blob/master/Main/Benchmarks/Datasets/EasyClinic_ENG/trace%20matrices/UC_TC.xml); [Published UC–TC configuration](https://www.researchgate.net/publication/400371120_TraceLLM_Leveraging_Large_Language_Models_with_Prompt_Engineering_for_Enhanced_Requirements_Traceability).

#### T4 — CM1, TraceLab embedded/NASA subset

[Repository / dataset](https://github.com/CoEST/TraceLab) · Serves needs **1,2** · **Hold for data**

Verified repository path Main/Data/ANC-Data/CM1-Subset1 contains high/, low/ and a traceability matrix.

- **Size:** A published small benchmark configuration has 22 high-level and 53 low-level/design artifacts and 45 links. Other CM1 releases are larger; select a specific subset.
- **Format / language:** TXT requirements/design; traceability_matrix.txt. English
- **Origin:** Real NASA spacecraft-instrument embedded software requirements/design.
- **Labels / ground truth:** Requirement-to-design/refinement links, not requirement-to-test pairs.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/CoEST/TraceLab/blob/master/LICENSE).
- **Commercial internal use:** TraceLab tool GPL permits internal commercial use; imported benchmark grant not established.
- **Redistribution:** Tool GPL obligations apply; original benchmark provenance unresolved.
- **Model input:** Hold original data until scope confirmed; tool GPL is not a substitute for document rights.
- **Freshness:** Last observed default-branch commit: [2016-10-17](https://github.com/CoEST/TraceLab/commit/a9c74bd4dadbc091c8f5e5efd9f6fd5d96d5b5f1). Shared TraceLab snapshot commit 2016-10-17; static legacy data.
- **Known problems:** Repository GPL does not independently establish a grant for the original NASA document excerpts; do not infer public domain merely from NASA origin. Do not confuse this CM1 traceability corpus with NASA CM1 defect-prediction metrics.

Additional evidence: [Verified matrix resource](https://api.github.com/repos/CoEST/TraceLab/contents/Main/Data/ANC-Data/CM1-Subset1/traceability_matrix.txt); [Published small configuration](https://yuleisui.github.io/publications/issre22.pdf).

#### T5 — eTOUR / eTour

[Repository / dataset](https://github.com/CoEST/TraceLab/tree/master/Main/Benchmarks/Datasets/eTour) · Serves needs **2** · **Hold for data**

Requirement/use-case-to-code traceability benchmark; useful for link recovery and impact analysis.

- **Size:** Published commonly used configuration: 58 use cases, 116 code artifacts, 308 links. Confirm exact variant before comparing scores.
- **Format / language:** TXT; source/code-class artifacts; answer files. Italian-origin artifacts; English-translated variants also circulate. Do not label all versions native English.
- **Origin:** Real student tourism application project.
- **Labels / ground truth:** Curated requirement-to-code links.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/CoEST/TraceLab/blob/master/LICENSE).
- **Commercial internal use:** TraceLab tool GPL permits internal commercial use; imported benchmark grant not established.
- **Redistribution:** Tool GPL obligations apply; original benchmark provenance unresolved.
- **Model input:** Hold original data until scope confirmed; tool GPL is not a substitute for document rights.
- **Freshness:** Last observed default-branch commit: [2016-10-17](https://github.com/CoEST/TraceLab/commit/a9c74bd4dadbc091c8f5e5efd9f6fd5d96d5b5f1). Shared TraceLab snapshot commit 2016-10-17; static.
- **Known problems:** Not requirement-to-test ground truth. Translation, tokenization and link-count variants circulate. Data-level rights not separately established by the TraceLab tool's GPL licence.

Additional evidence: [Published configuration](https://yuleisui.github.io/publications/issre22.pdf).

#### T6 — COMET replication datasets — iTrust and LibEST

[Repository / dataset](https://gitlab.com/SEMERU-Code-Public/Data/icse20-comet-data-replication-package) · Serves needs **1,2** · **Hold**

ICSE 2020 traceability replication package with iTrust and embedded-oriented LibEST. LibEST explicitly includes requirements/, source_code/, test/, req_to_code_ground.txt, req_to_test_ground.txt and execution_traces.txt.

- **Size:** No cardinalities stated on the opened repository page; iTrust and LibEST directories verified through GitLab API.
- **Format / language:** TXT requirements, answer links and execution traces; C/Java/web source; Python preprocessing. English requirements; code identifiers vary.
- **Origin:** Real open-source systems, including educational iTrust and embedded-oriented C EST/TLS library LibEST.
- **Labels / ground truth:** LibEST explicitly supplies requirement-to-code and requirement-to-test ground files plus execution traces; iTrust relationships must be read separately.
- **Licence quoted:** “no licence stated” — [licence evidence](https://gitlab.com/api/v4/projects/19822550/repository/tree?ref=main&per_page=100).
- **Commercial internal use:** No licence grant established.
- **Redistribution:** No licence grant established.
- **Model input:** No commercial input/training grant established.
- **Freshness:** Last observed commit: 2020-07-08 (98aaf5440396d33cb8f40151e9721d3239bfbed4). Static replication package.
- **Known problems:** No root licence in verified top-level listing, and original-project licences do not automatically license the complete assembled dataset. No commercial internal use/model input/redistribution grant established. Item counts from other iTrust versions should not be reused.

### Need 3: CAN and vehicle network data

#### N1 — opendbc

[Repository / dataset](https://github.com/commaai/opendbc) · Serves needs **3,4,7** · **Candidate**

CAN signal databases, parsing/packing, per-car interfaces and safety firmware/tests. More than a static DBC collection.

- **Size:** DBC/car/safety-suite cardinality not stated in opened README.
- **Format / language:** DBC; Python; C safety code; tests. English code/docs; signal names/vendor identifiers vary.
- **Origin:** Real community reverse-engineered vehicle interfaces, plus authored tests.
- **Labels / ground truth:** Expected decoded/encoded signals and safety-policy regression assertions; no independently certified OEM signal dictionary.
- **Licence quoted:** “Permission is hereby granted, free of charge” — [licence evidence](https://github.com/commaai/opendbc/blob/master/LICENSE).
- **Commercial internal use:** Yes, for project-owned material.
- **Redistribution:** Yes; retain copyright/licence notices.
- **Model input:** Yes under the same scope; copied outputs retain applicable terms.
- **Freshness:** Last observed default-branch commit: [2026-11-08](https://github.com/commaai/opendbc/commit/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2). Active; observed commit 2026-11-08.
- **Known problems:** Reverse-engineered definitions can be incomplete or version-specific; not proof of AUTOSAR compliance. No accompanying comprehensive raw-drive-log corpus. No evidence of a leak found in reviewed pages; that does not validate every contribution's provenance.

#### N2 — cantools

[Repository / dataset](https://github.com/cantools/cantools) · Serves needs **3,7** · **Conditional**

CAN database parsing, encoding/decoding and C generation, with regression tests and expected values. Best compact parser/ARXML interoperability corpus.

- **Size:** Fixture/file counts not stated.
- **Format / language:** DBC; ARXML; KCD; SYM; CDD; Python; generated C; test fixtures. English tooling/docs; fixture identifiers and content vary.
- **Origin:** Production-used CAN tooling with deliberately constructed format cases and imported examples.
- **Labels / ground truth:** Exact message/frame/signal encode–decode assertions, malformed-input behavior and generation expectations.
- **Licence quoted:** “The MIT License (MIT)” — [licence evidence](https://github.com/cantools/cantools/blob/master/LICENSE).
- **Commercial internal use:** Tool yes; imported fixtures require provenance checks.
- **Redistribution:** Yes for licensed project files; imported examples per file.
- **Model input:** Project-authored fixtures yes; unverified third-party samples on hold.
- **Freshness:** Last observed default-branch commit: [2026-11-10](https://github.com/cantools/cantools/commit/2e4bbb8dc4cdc1fbe244f1eb3262a7ad317830e8). Active; observed commit 2026-11-10.
- **Known problems:** Most fixtures are edge-case examples, not complete vehicle architecture exports. Audit third-party fixture headers rather than assuming all ARXML/DBC examples are original MIT work. Avoid importing proprietary OEM ARXML from unrelated mirrors.

#### N3 — python-can

[Repository / dataset](https://github.com/hardbyte/python-can) · Serves needs **3,7** · **Candidate**

Virtual CAN buses, readers/writers, replay and example suites; practical adapter layer between generated tests and CAN simulators.

- **Size:** Example/test/log counts not stated.
- **Format / language:** Python; ASC/BLF/candump and other supported log formats. English
- **Origin:** Real open-source CAN I/O library plus constructed virtual-bus/logging fixtures.
- **Labels / ground truth:** Reader/writer round-trip and virtual-bus expected-message assertions.
- **Licence quoted:** “GNU LESSER GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/hardbyte/python-can/blob/main/LICENSE.txt).
- **Commercial internal use:** Yes; internal operation allowed.
- **Redistribution:** Yes subject to LGPL notices, library source/relinking and applicable conditions.
- **Model input:** Yes within licensed material's scope; outputs/derivatives require separate assessment.
- **Freshness:** Last observed default-branch commit: [2026-11-11](https://github.com/hardbyte/python-can/commit/86e85794f6c3505c988a4acd5d34f5b08f508b17). Active; observed commit 2026-11-11.
- **Known problems:** Library examples are not a real driving dataset. A Python virtual bus and Linux SocketCAN vcan are different transports; use the appropriate interface for ICSim. Retain library notices and meet LGPL obligations when distributing.

#### N4 — ICSim — Instrument Cluster Simulator

[Repository / dataset](https://github.com/zombieCraig/ICSim) · Serves needs **3,7** · **Candidate with copyleft**

Instrument cluster and controls operating on a Linux CAN interface. Script external CAN injection/replay through vcan using python-can/can-utils.

- **Size:** Small simulator/control application; source/record count not stated.
- **Format / language:** C; SDL assets; SocketCAN traffic. English
- **Origin:** Deliberately simplified vehicle/cluster simulator; synthetic behavior.
- **Labels / ground truth:** Known simulator behavior from source; no production ECU fault oracle or labelled recording corpus.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/zombieCraig/ICSim/blob/master/LICENSE).
- **Commercial internal use:** Yes; GPL is not a non-commercial licence.
- **Redistribution:** Yes subject to GPL-3.0 source/licence and covered-work obligations.
- **Model input:** Internal evaluation/input yes; do not assume copied code outputs or model derivatives are exempt.
- **Freshness:** Last observed default-branch commit: [2025-09-18](https://github.com/zombieCraig/ICSim/commit/2b3333ef866987d8adc9c15ff15b9b9189edf85b). Observed commit 2025-09-18; sparse maintenance.
- **Known problems:** Training/demo-scale model, GUI/SDL and Linux dependencies; not a full virtual AUTOSAR ECU, physical bus model or automotive timing qualification. GPL permits commercial internal operation with distribution obligations.

#### N5 — ROAD — Real ORNL Automotive Dynamometer CAN dataset

[Repository / dataset](https://zenodo.org/records/10462796) · Serves needs **3,5,6** · **Candidate**

Documented ambient and attack CAN recordings; translated signals for 17 attack captures and all ambient captures.

- **Size:** Over 3.5 hours from one vehicle; 33 attack captures (~30 minutes), 12 ambient captures (~3 hours); road.zip 556,718,276 bytes.
- **Format / language:** Raw CAN log captures; translated signal time-series; metadata/ZIP. English documentation; CAN IDs/payloads numeric.
- **Origin:** Real vehicle on dynamometer, controlled real attacks plus explicitly simulated masquerade attacks.
- **Labels / ground truth:** Capture/attack metadata and attack timing/type information; physical effects of real attacks documented.
- **Licence quoted:** “cc-by-4.0” — [licence evidence](https://zenodo.org/api/records/10462796).
- **Commercial internal use:** Yes under CC BY 4.0.
- **Redistribution:** Yes with attribution, licence reference and change indication.
- **Model input:** Yes with applicable attribution; not a waiver of other rights.
- **Freshness:** Record publication field 2020-12-28; archive created 2024-01-05 and last modified 2024-01-05. Static benchmark; paper published 2024.
- **Known problems:** Single anonymized vehicle; CAN identifiers/data obfuscated. Many attacks are laboratory injections; simulated masquerade files are not physical captures of that attack. Do not combine an unrelated opendbc DBC with these obfuscated frames.

### Need 4: Embedded C/C++ verification

#### V1 — FreeRTOS-Kernel

[Repository / dataset](https://github.com/FreeRTOS/FreeRTOS-Kernel) · Serves needs **4,7** · **Conditional**

Meaningful embedded C target for unit-test generation and review; MISRA.md explains deviations and the Coverity version used for checks.

- **Size:** RTOS kernel and ports; LOC/test count not stated. README links CMock tests and Codecov.
- **Format / language:** C; headers; CMock tests; MISRA deviation/configuration files; coverage outputs. English
- **Origin:** Real embedded production software with authored tests and compliance deviations.
- **Labels / ground truth:** Unit-test assertions, regression behavior, documented deviation references. Coverage report is linked; no current coverage percentage asserted.
- **Licence quoted:** “MIT License” — [licence evidence](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/main/LICENSE.md).
- **Commercial internal use:** Kernel code yes under MIT; separately owned MISRA wording excluded pending rights review.
- **Redistribution:** MIT code with notices; no blanket grant for normative standard excerpts.
- **Model input:** Code/project-authored material yes; MISRA rule-text excerpts on hold.
- **Freshness:** Last observed default-branch commit: [2026-10-29](https://github.com/FreeRTOS/FreeRTOS-Kernel/commit/ca759444e9ca59cfa3a9faa6cb8b49e0772ca520). Active; observed commit 2026-10-29.
- **Known problems:** Kernel-only repo is not a complete application or fully labelled violation corpus. MISRA.md reproduces selected MISRA rule wording: the software's MIT licence does not establish permission to reuse the standard's wording as a commercial corpus. Use code, project-authored justifications and rule IDs; exclude normative excerpts pending rights confirmation.

Additional evidence: [MISRA evidence and deviations](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/main/MISRA.md).

#### V2 — Zephyr

[Repository / dataset](https://github.com/zephyrproject-rtos/zephyr) · Serves needs **3,4,7** · **Conditional**

Kernel, drivers and CAN-related code with a substantial test ecosystem and scriptable native/QEMU runs. Useful for larger C engineering tasks.

- **Size:** Large RTOS/platform repository; total LOC/test count not stated on reviewed page.
- **Format / language:** C/C++; Devicetree; YAML; Python; ztest/Twister tests and coverage outputs. English
- **Origin:** Real embedded RTOS across hardware platforms plus simulator/test fixtures.
- **Labels / ground truth:** ztest assertions, Twister test metadata and reproducible pass/fail/coverage generation.
- **Licence quoted:** “Apache-2.0” — [licence evidence](https://github.com/zephyrproject-rtos/zephyr).
- **Commercial internal use:** Yes for Apache/per-file licensed subset.
- **Redistribution:** Follow each file's SPDX terms and required notices.
- **Model input:** Yes within each selected file's licence; no blanket relicensing of dependencies.
- **Freshness:** Last observed default-branch commit: [2026-11-12](https://github.com/zephyrproject-rtos/zephyr/commit/f8da8ea370508f274685a25ff19dbe5a9ff54790). Active; observed commit 2026-11-12.
- **Known problems:** Mixed per-file licensing; check SPDX headers and NOTICE. Board dependencies and hardware-only tests complicate automation. It is not an ISO 26262 certification dataset, and tests do not constitute complete requirement labels.

#### V3 — openAUTOSAR classic-platform

[Repository / dataset](https://github.com/openAUTOSAR/classic-platform) · Serves needs **3,4** · **Candidate with copyleft**

Automotive BSW-style code and integration material for module analysis and verification tasks.

- **Size:** AUTOSAR-style platform with drivers, communication, diagnostics, memory and safety/security modules; LOC count not stated.
- **Format / language:** C; headers; configuration/build files; documentation. English
- **Origin:** Real open-source Arctic Core-derived AUTOSAR-style stack.
- **Labels / ground truth:** Existing test/integration material, not a comprehensive labelled compliance/coverage benchmark.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/openAUTOSAR/classic-platform/blob/master/LICENSE.md).
- **Commercial internal use:** Yes; GPL is not a non-commercial licence.
- **Redistribution:** Yes subject to GPL-2.0 and component-specific conditions.
- **Model input:** Internal evaluation/input yes within scope; derived/copied outputs need review.
- **Freshness:** Last observed default-branch commit: [2020-04-02](https://github.com/openAUTOSAR/classic-platform/commit/09433770bebb8f27a7b480d7c96d814c68ffed3e). Default-branch last observed commit 2020-04-02. Later push timestamps are not proof of maintained source.
- **Known problems:** Legacy stack and toolchains; not certified or established as conforming to the latest AUTOSAR release. Inspect component headers/third-party files. GPL code licence does not grant rights to any separately copyrighted standards text in documentation.

#### V4 — Cppcheck regression and MISRA-addon tests

[Repository / dataset](https://github.com/cppcheck-opensource/cppcheck) · Serves needs **4,7** · **Candidate with copyleft**

Static-analysis positives/negatives, expected findings and MISRA-addon tests. Strong deterministic baseline for reviewing generated C.

- **Size:** Regression/addon suite count not stated. Verified addons/test/misra/ and addons/misra.py.
- **Format / language:** C/C++ snippets; Python; expected diagnostic assertions; configuration. English
- **Origin:** Constructed analyzer regressions and bug-reproducer cases; mixed synthetic and real-derived snippets.
- **Labels / ground truth:** Expected tool diagnostics/rule IDs and regression assertions; analyzer-specific, not universal correctness.
- **Licence quoted:** “GNU GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/cppcheck-opensource/cppcheck/blob/main/COPYING).
- **Commercial internal use:** Yes; GPL is not a non-commercial licence.
- **Redistribution:** Yes subject to GPL-3.0 source/licence and covered-work obligations.
- **Model input:** Internal evaluation/input yes; do not assume copied code outputs or model derivatives are exempt.
- **Freshness:** Last observed default-branch commit: [2026-11-13](https://github.com/cppcheck-opensource/cppcheck/commit/6943b20272bb1c48030379bebb0221d20fbd4a8b). Active; observed commit 2026-11-13; repository moved from danmar/cppcheck.
- **Known problems:** Not the official MISRA test suite and not proof of full MISRA coverage. Obtain any required MISRA rule text through a valid licence; dummy rule-text fixtures are not the standard. Pin checker version/options and retain individual snippet notices.

#### V5 — NIST SARD Juliet C/C++ 1.3

[Repository / dataset](https://samate.nist.gov/SARD/test-suites/112) · Serves needs **4,5** · **Candidate**

Large labelled good/bad code suite for static analysis and vulnerability-finding evaluation.

- **Size:** 64,099 test cases; 118 CWE categories; 146 MB, as stated by SARD.
- **Format / language:** C/C++ source; test support and manifests. English identifiers/comments
- **Origin:** Synthetic deliberately vulnerable/non-vulnerable programs.
- **Labels / ground truth:** CWE identity, good/bad variants and test-case metadata.
- **Licence quoted:** “CC0 1.0 Public Domain License” — [licence evidence](https://samate.nist.gov/SARD/test-suites/112).
- **Commercial internal use:** Yes under the stated public-domain/CC0 dedication.
- **Redistribution:** Yes under CC0, subject to rights outside the dedication.
- **Model input:** Yes; no copyright restriction claimed within the dedication's scope.
- **Freshness:** Selected suite release/submission: 2017-10-01. Frozen benchmark; SARD remains available.
- **Known problems:** Synthetic, repetitive and highly susceptible to leakage from near-identical variants. Not MISRA labels, automotive functionality or natural bug prevalence. Split by generation family/CWE pattern, not random files.

### Need 5: Cybersecurity, TARA, SBOM, VEX and licence scanning

#### S1 — OpenASC catalogs

[Repository / dataset](https://github.com/steflokos/openasc-catalogs) · Serves needs **5,7** · **Candidate**

Automotive assets, threats, controls, capabilities, attack-feasibility attributes and UN R155 Annex 5 mappings.

- **Size:** Asset/threat/control catalogs and schemas; entry count not stated. README states an 88-tag metadata dictionary.
- **Format / language:** JSON; JSON Schema; JavaScript tooling. English
- **Origin:** AI-assisted authored reference catalog; expert-reviewed according to README. Not a dataset of recorded attacks.
- **Labels / ground truth:** Schema validation, taxonomy/mapping fields and author-selected ratings; not independent validated TARA ground truth.
- **Licence quoted:** “MIT License” — [licence evidence](https://github.com/steflokos/openasc-catalogs/blob/main/LICENSE.md).
- **Commercial internal use:** Yes, for project-owned material.
- **Redistribution:** Yes; retain copyright/licence notices.
- **Model input:** Yes under the same scope; copied outputs retain applicable terms.
- **Freshness:** Last observed default-branch commit: [2026-11-01](https://github.com/steflokos/openasc-catalogs/commit/9e1ed7db20ccf813966e48190e0fc2dd5fb2dd9a). Active; observed commit 2026-11-01.
- **Known problems:** README explicitly discloses LLM assistance and possible errors/missing entries. Treat as a retrieval seed/schema test, not authoritative ISO/SAE 21434 scoring, official UN text, Auto-ISAC ATM or observed-attack ground truth.

#### S2 — V2X PKI formal verification and TARA artifact

[Repository / dataset](https://github.com/bhamsec/v2x-pki-formal-verification) · Serves needs **1,2,5,7** · **Candidate**

Asset inventory, damage scenarios with safety/operations/financial/privacy impact scores, STRIDE threat scenarios, requirements and reproducible formal verification outcomes.

- **Size:** 106 security/privacy requirements; five formal models; stated 34-property × 5-model result matrix.
- **Format / language:** PDF; XLSX; Markdown; ProVerif .pv. English
- **Origin:** Author-released research worked case for real V2X PKI protocol; formal models/scenarios, not an OEM vehicle assessment.
- **Labels / ground truth:** Explicit assets/threat/requirement references and expected ProVerif pass/fail outcomes; author-assessed impact ratings.
- **Licence quoted:** “MIT License” — [licence evidence](https://github.com/bhamsec/v2x-pki-formal-verification/blob/main/LICENSE).
- **Commercial internal use:** Yes, for project-owned material.
- **Redistribution:** Yes; retain copyright/licence notices.
- **Model input:** Yes under the same scope; copied outputs retain applicable terms.
- **Freshness:** Last observed default-branch commit: [2026-04-21](https://github.com/bhamsec/v2x-pki-formal-verification/commit/ef038b135ed91d66ca9402ac7324a73c2b35bb17). Observed commit 2026-04-21; static 2026 research artifact. README says submitted to ESORICS 2026, not confirmed accepted.
- **Known problems:** Impact scores are not the same as a complete independently adjudicated final TARA risk rating. No demonstrated OEM-approved risk ground truth. Formal proof scope depends on model assumptions; no independent reproduction was run for this research report.

#### S3 — SPDX usage examples

[Repository / dataset](https://github.com/spdx/spdx-examples) · Serves needs **5** · **Candidate with file distinctions**

Official SPDX project examples for parsing and licence/security relationship tests.

- **Size:** Examples grouped by software, hardware, AI, dataset and conformance profiles; total document count not stated.
- **Format / language:** SPDX documents; JSON/JSON-LD and version-specific serializations; Markdown; helper source. English
- **Origin:** Constructed interoperability examples and software BOM examples.
- **Labels / ground truth:** Reference representations and encoded relationships, not exhaustive ground truth of actual shipped firmware.
- **Licence quoted:** “SPDX documents in this repository are provided under CC0 1.0 Universal” — [licence evidence](https://github.com/spdx/spdx-examples/blob/master/README.md).
- **Commercial internal use:** SPDX documents CC0; docs CC BY 4.0; helper code GPL-3.0-or-later.
- **Redistribution:** Apply the stated licence to each class of file.
- **Model input:** BOM documents yes; helper code/docs under their respective terms.
- **Freshness:** Last observed default-branch commit: [2026-09-29](https://github.com/spdx/spdx-examples/commit/08a3552c7a5348f79ae996196a5c4f99e068607e). Observed commit 2026-09-29; maintained example collection.
- **Known problems:** GitHub's root GPL badge does not describe every file: SPDX documents CC0, documentation CC BY 4.0, helper source GPL-3.0-or-later unless otherwise stated. Preserve per-file distinctions. Examples omit some fields/serializations and are not an automotive firmware inventory.

#### S4 — CycloneDX BOM examples

[Repository / dataset](https://github.com/CycloneDX/bom-examples) · Serves needs **5** · **Candidate**

CycloneDX documents and VEX scenario examples suitable for schema, dependency graph and vulnerability-status tests.

- **Size:** SBOM, HBOM, CBOM, VEX and other example families; total BOM count not stated.
- **Format / language:** JSON; XML; Markdown. English
- **Origin:** Constructed standard use cases plus BOMs derived from real software.
- **Labels / ground truth:** Declared component relationships and illustrative VEX status cases; not externally audited firmware composition.
- **Licence quoted:** “CC0 1.0 Universal” — [licence evidence](https://github.com/CycloneDX/bom-examples/blob/master/LICENSE).
- **Commercial internal use:** Yes under the stated public-domain/CC0 dedication.
- **Redistribution:** Yes under CC0, subject to rights outside the dedication.
- **Model input:** Yes; no copyright restriction claimed within the dedication's scope.
- **Freshness:** Last observed default-branch commit: [2025-10-21](https://github.com/CycloneDX/bom-examples/commit/7d9172d00c88c05a8f1ccb90589d111870fc9d86). Observed commit 2025-10-21; stable example corpus, recent maintenance not demonstrated.
- **Known problems:** Non-automotive examples dominate. A licence string inside a BOM describes the referenced component; it is not necessarily the licence of the BOM document. Independently generate an SBOM from a pinned embedded build for real ground truth.

#### S5 — OpenVEX vexctl examples and filtering

[Repository / dataset](https://github.com/openvex/vexctl) · Serves needs **5,7** · **Candidate**

Create/merge/validate VEX documents and apply statements to scanner results; includes example status timelines and filtering inputs.

- **Size:** Example/test-document count not stated.
- **Format / language:** OpenVEX JSON; CSAF input/examples; SARIF; Go. English
- **Origin:** Constructed VEX examples and tool tests.
- **Labels / ground truth:** Expected merged statuses, schema/semantic validation and alert filtering outcomes.
- **Licence quoted:** “Apache-2.0” — [licence evidence](https://github.com/openvex/vexctl).
- **Commercial internal use:** Yes under Apache-2.0.
- **Redistribution:** Yes; preserve licence/NOTICE and modification notices as applicable.
- **Model input:** Yes under the same scope; no ML-specific restriction established.
- **Freshness:** Last observed default-branch commit: [2026-11-12](https://github.com/openvex/vexctl/commit/d6574cfb82973faa47e9cebb659a77b185bdf2c2). Active; observed commit 2026-11-12.
- **Known problems:** Illustrative vulnerability/product IDs and assertions are not substantiated production exploitability decisions. A not_affected label must be backed by actual product evidence before use as a real triage oracle.

#### S6 — OSV code and offline vulnerability dumps

[Repository / dataset](https://github.com/google/osv.dev) · Serves needs **5,7** · **Conditional; restricted sources on hold**

Affected-package/version/range and fix information; offline data dumps support deterministic vulnerability triage.

- **Size:** Rolling multi-source advisory database; snapshot record count not verified. Full/per-ecosystem ZIP exports documented.
- **Format / language:** OSV JSON; ZIP dumps; Python/Go service code. Primarily English; upstream advisory language can vary.
- **Origin:** Real published security advisories aggregated from independent upstream providers.
- **Labels / ground truth:** Upstream advisory assertions, identifiers, affected ranges and fixes; these can be corrected and are not proof a particular embedded binary is exploitable.
- **Licence quoted:** “CC-BY-NC-ND 4.0” — [licence evidence](https://google.github.io/osv.dev/data/).
- **Commercial internal use:** Service code yes; only commercially compatible source advisories selected.
- **Redistribution:** Per-upstream licence; do not redistribute unrestricted full dump by assumption.
- **Model input:** Only cleared source feeds; exclude NC/ND feed content pending an appropriate licence.
- **Freshness:** Last observed default-branch commit: [2026-11-13](https://github.com/google/osv.dev/commit/e15de6dfb89d532a870731e9e78ca6b2db19a4ed). Service code observed commit 2026-11-13; docs describe continuously exported dumps. No full dump was downloaded/pinned.
- **Known problems:** Service code Apache-2.0 does not license all data. Sources include CC BY, CC0, MIT, Apache, Ubuntu CC BY-SA and Chainguard/Wolfi restricted feeds. Filter by source before commercial use; per-ecosystem filtering alone may retain restricted-source records. Preserve provenance, withdrawn status and alias deduplication.

Additional evidence: [Official data-source licences and dumps](https://google.github.io/osv.dev/data/); [Chainguard source terms](https://github.com/chainguard-dev/vulnerability-scanner-support/blob/main/docs/foundational_concepts.md).

#### S7 — NVD JSON 2.0 feeds

[Repository / dataset](https://nvd.nist.gov/vuln/data-feeds) · Serves needs **5** · **Conditional**

Year feeds and recent/modified feeds for offline mirroring; use official feeds rather than unlicensed third-party scraped mirrors.

- **Size:** Selected 2026 year-feed metadata: 549,473,026 bytes uncompressed; GZ 46,206,180 bytes. Record count not verified.
- **Format / language:** JSON; GZ/ZIP; .meta checksums. Primarily English; includes source/CNA/vendor material.
- **Origin:** Real CVE/CPE/CVSS/CWE and vulnerability enrichment data.
- **Labels / ground truth:** CVE IDs, descriptions, affected configurations and published scores; coverage/enrichment may be incomplete or disputed.
- **Licence quoted:** “may be distributed or copied” — [licence evidence](https://www.nist.gov/copyrights-disclaimers).
- **Commercial internal use:** NIST public information allowed except copyrighted material; third-party scope needs checking.
- **Redistribution:** NIST public information may be copied/distributed with credits; third-party terms persist.
- **Model input:** NIST-authored data yes within policy; do not ingest linked copyrighted works by assumption.
- **Freshness:** Verified 2026-feed lastModifiedDate: 2026-11-13T03:00:26-05:00. Rolling maintained feed; fetch .meta and checksum for each snapshot.
- **Known problems:** No standalone repository licence file; NIST public-information policy applies except copyrighted material. Third-party descriptions/references need their own scope check; linked vendor PDFs are not part of a blanket public-domain grant. CVSS severity is not automotive TARA risk.

Additional evidence: [Verified feed metadata](https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-2026.meta); [NIST policy](https://www.nist.gov/copyrights-disclaimers).

#### S8 — ScanCode Toolkit reference data and test corpus

[Repository / dataset](https://github.com/aboutcode-org/scancode-toolkit) · Serves needs **5,7** · **Conditional**

Licence/copyright/package scanning examples, expected detections and provenance files; strong corpus for licence-scanning evaluation.

- **Size:** Maintainer states 30,000+ automated tests; this is not a count of unique licensed projects.
- **Format / language:** Source snippets; licence text/rules; YAML/JSON expectations; Python; .ABOUT provenance. Primarily English; licence texts and samples can be multilingual.
- **Origin:** Real third-party licence/source samples plus authored test cases and detection rules.
- **Labels / ground truth:** Expected licence expressions/detections and package metadata; regression oracles, not legal adjudication.
- **Licence quoted:** “Apache-2.0 is the overall license” — [licence evidence](https://github.com/aboutcode-org/scancode-toolkit/blob/develop/README.rst).
- **Commercial internal use:** Tool yes under Apache; reference data CC BY; samples per file.
- **Redistribution:** Apache/CC BY plus each third-party sample's actual licence.
- **Model input:** Conditional on .ABOUT/NOTICE/per-file terms; not Apache-only.
- **Freshness:** Last observed default-branch commit: [2026-11-02](https://github.com/aboutcode-org/scancode-toolkit/commit/e423b48a1fdbff26219fbeafe7e9bdef293b91fc). Active; observed commit 2026-11-02.
- **Known problems:** Reference datasets CC BY 4.0; third-party components/test code/data also carry secondary permissive/copyleft terms. Evaluate selected samples with .ABOUT/NOTICE files; do not relicense or redistribute the whole test tree as Apache-only.

### Need 6: Defect and log analysis

#### D1 — COVESA dlt-daemon and DLT fixtures

[Repository / dataset](https://github.com/COVESA/dlt-daemon) · Serves needs **4,6,7** · **Candidate with file copyleft**

DLT daemon, console utilities/test applications, parsing fixtures and a published LCOV report link. Most directly relevant public log-format source.

- **Size:** No message/test count stated; repository includes tests/testfile.dlt, testfile-v2.dlt and testfile_extended.dlt.
- **Format / language:** Binary .dlt; C/C++; CTest; LCOV/HTML. English tooling/docs; sample log messages are fixture-specific.
- **Origin:** Real automotive logging implementation plus constructed/sample trace fixtures.
- **Labels / ground truth:** Protocol parsing/round-trip and regression expectations; no labelled production fault episodes.
- **Licence quoted:** “Mozilla Public License 2.0” — [licence evidence](https://github.com/COVESA/dlt-daemon).
- **Commercial internal use:** Yes under MPL-2.0.
- **Redistribution:** Yes; preserve notices and provide source for covered files as required.
- **Model input:** Yes within scope; copied covered source remains subject to relevant terms.
- **Freshness:** Last observed default-branch commit: [2026-11-05](https://github.com/COVESA/dlt-daemon/commit/144703c39f2031e8e38ee32fc3a9d2e3cb097b28). Active; observed commit 2026-11-05.
- **Known problems:** Tiny format fixtures are not representative fleet/ECU anomaly data. Check third-party cityhash/COPYING and fixture headers. The linked coverage report's current percentage was not verified; no AUTOSAR standards text grant is implied.

#### D2 — BMW Car IT python-dlt

[Repository / dataset](https://github.com/bmwcarit/python-dlt) · Serves needs **6,7** · **Candidate with file copyleft**

Scriptable DLT file/message/client/broker interfaces and tests of decoding, corruption, timing and file handling.

- **Size:** Test/fixture message count not stated; tests include corrupt-message and message-decoding cases.
- **Format / language:** Python; ctypes/libdlt; binary message buffers and test fixtures. English
- **Origin:** Real BMW-origin open-source test/logging tool with authored tests.
- **Labels / ground truth:** Expected decoded fields/payloads and error behavior in unit tests.
- **Licence quoted:** “Mozilla Public License Version 2.0” — [licence evidence](https://github.com/bmwcarit/python-dlt/blob/master/LICENCE.txt).
- **Commercial internal use:** Yes under MPL-2.0.
- **Redistribution:** Yes; preserve notices and provide source for covered files as required.
- **Model input:** Yes within scope; copied covered source remains subject to relevant terms.
- **Freshness:** Last observed default-branch commit: [2026-09-07](https://github.com/bmwcarit/python-dlt/commit/323a8f252488c82ece6191909aa697cfff948e4e). Observed commit 2026-09-07; maintained.
- **Known problems:** README says tested with libdlt 2.18.8/2.18.10 and only GENIVI-daemon traces; pin ABI/library versions. Not a large downloadable collection of production BMW logs, and BMW authorship does not make all possible imported traces redistributable.

#### D3 — GitBugs

[Repository / dataset](https://github.com/av9ash/gitbugs) · Serves needs **6** · **Conditional**

Bug summaries/descriptions, resolution/status, dates, duplicate IDs and curated benchmark splits.

- **Size:** README examples: Mozilla Core 85,673 reports/17,899 duplicates; VS Code 32,829/9,238. Paper says over 150,000 reports; exact snapshot totals differ. HF viewer shows a much smaller configured split.
- **Format / language:** CSV; predefined duplicate-detection splits; HF Parquet conversion. Primarily English; separately linked multilingual bug-report material.
- **Origin:** Real issue-tracker records from open-source projects.
- **Labels / ground truth:** Tracker-derived duplicate relationships, issue status and resolution labels.
- **Licence quoted:** “Creative Commons Attribution 4.0 International (CC BY 4.0)” — [licence evidence](https://github.com/av9ash/gitbugs/blob/main/README.md).
- **Commercial internal use:** Depositor CC BY 4.0 grant verified; contributor/legacy-source rights not fully traced.
- **Redistribution:** Attribution for curated release; verify upstream and attachment rights.
- **Model input:** Conditional on selected issue-text rights and privacy handling; do not bulk-ingest linked legacy sets.
- **Freshness:** Last observed default-branch commit: [2026-04-30](https://github.com/av9ash/gitbugs/commit/eadf2d6794990a1aaa26d0ae15391f29f8969301). Observed commit 2026-04-30; recently curated dataset, not a live tracker mirror.
- **Known problems:** Contributor text rights, personal data and copied attachments need review. README also copies/links legacy BugRepo collections; the new CC BY statement must not be assumed to relicense every linked legacy dataset. No automotive/embedded-specific duplicate gold set established.

Additional evidence: [Opened Hugging Face dataset](https://huggingface.co/datasets/av9ash/GitBugs).

#### D4 — Eclipse issue report dataset (Issuex)

[Repository / dataset](https://zenodo.org/records/15348468) · Serves needs **6** · **Conditional**

Rich issue fields including Dupe of, severity, resolution, descriptions, comments, history and attachments.

- **Size:** Record examples: Platform 122,497, JDT 63,266, CDT 23,371 issues; main ZIP 17,158,276,253 bytes; sample CSV 2,879,417 bytes.
- **Format / language:** CSV sample; ZIP; README. Primarily English issue text; no language guarantees for comments/attachments.
- **Origin:** Real Eclipse Bugzilla exports across multiple projects.
- **Labels / ground truth:** Explicit duplicate-of IDs and tracker labels; missing/incorrect duplicate decisions remain possible.
- **Licence quoted:** “cc-by-sa-4.0” — [licence evidence](https://zenodo.org/api/records/15348468).
- **Commercial internal use:** Depositor CC BY-SA 4.0 grant verified; original text/attachment scope needs review.
- **Redistribution:** Attribution and share-alike for shared adaptations; underlying third-party rights persist.
- **Model input:** Conditional on selected content rights; model derivative/share-alike questions not resolved.
- **Freshness:** Version 1.0.1 publication 2024-11-27; record modified 2025-07-23. Static export; original projects continue separately.
- **Known problems:** Large archive; use sample/schema first. CDT/Papyrus are embedded-adjacent tooling, not automotive ECU incident data. Attribution/share-alike applies to shared adaptations, while source contributor rights and PII/attachments need per-scope review.

#### D5 — Loghub

[Repository / dataset](https://github.com/logpai/loghub) · Serves needs **6** · **Hold**

System-log parsing and anomaly benchmarks across distributed systems, operating systems and mobile software.

- **Size:** Examples stated in README: BGL 4,747,963 lines; HDFS_v1 11,175,629; Linux 25,567; Android_v1 1,555,005.
- **Format / language:** Raw text logs; structured/template CSV samples; anomaly labels for selected sets. Primarily English system messages; variable contents vary.
- **Origin:** Real production and lab system logs; not an LLM-generated corpus.
- **Labels / ground truth:** Selected datasets have anomaly labels (e.g. BGL and HDFS); others lack anomaly labels. Structured 2k samples support template parsing, not blanket full-set anomaly truth.
- **Licence quoted:** “freely available for research or academic work” — [licence evidence](https://github.com/logpai/loghub/blob/master/README.md).
- **Commercial internal use:** Research/academic availability stated; general commercial permission unestablished.
- **Redistribution:** Only within the published grant, retaining licence/citation; commercial redistribution not cleared.
- **Model input:** Commercial inference/training not cleared by the published wording.
- **Freshness:** Last observed default-branch commit: [2025-06-13](https://github.com/logpai/loghub/commit/dd61d0952749ee7963bde24220d1be5ede023033). Observed commit 2025-06-13; stable curated collection.
- **Known problems:** The published wording establishes research/academic availability, not a clear general commercial grant; obtain permission before commercial internal prompts, training or redistribution. Android/Linux are closer to embedded logs than HDFS/BGL, but none is production AUTOSAR DLT/ECU fault ground truth. Unsanitized logs may contain sensitive data.

### Need 7: Reusable harness components and agent benchmarks

#### H1 — NASA FRET

[Repository / dataset](https://github.com/NASA-SW-VnV/fret) · Serves needs **1,2,7** · **Candidate**

Requirements formalization, hierarchical requirements, consistency checking, simulation and requirement-based test generation with coverage metrics.

- **Size:** Case-study and requirement totals not stated for the current checkout; verified JSON cases include LiquidMixer, LMCPS and LiftPlusCruise.
- **Format / language:** FRET JSON; restricted-English FRETISH; temporal logic; JavaScript/Electron; generated tests. English/FRETISH
- **Origin:** Authored formal-methods research case studies, including safety-oriented aerospace cases and illustrative models.
- **Labels / ground truth:** Requirement-to-formal-semantics examples and expected regression/simulation behavior; generated tests are an oracle candidate, not independent expert tests.
- **Licence quoted:** “Apache License, Version 2.0” — [licence evidence](https://github.com/NASA-SW-VnV/fret/blob/master/README.md).
- **Commercial internal use:** Yes under Apache-2.0.
- **Redistribution:** Yes; preserve licence/NOTICE and modification notices as applicable.
- **Model input:** Yes under the same scope; no ML-specific restriction established.
- **Freshness:** Last observed default-branch commit: [2026-04-10](https://github.com/NASA-SW-VnV/fret/commit/cf0f913cc15c41705e803593297e89cd6056b839). Observed commit 2026-04-10; current README identifies release 3.1. Older versions may have different licensing.
- **Known problems:** Not an LLM or an unconstrained PDF requirement extractor. Tests target formalized behavior; binding outputs to a real ECU requires adapters. Do not use tutorial UI screenshots as corpus size evidence.

Additional evidence: [Concrete LiquidMixer case](https://github.com/NASA-SW-VnV/fret/blob/master/caseStudies/LiquidMixer/LM_reqts_and_vars.json).

#### H2 — TraceLLM replication package

[Repository / dataset](https://github.com/Noufst/TraceLLM) · Serves needs **2,7** · **Code candidate; data hold**

Configurable trace-link classification/generation/explanation experiments, prompt variants, few-shot selection and evaluation/results handling.

- **Size:** Repo provides CM1 and EasyClinic UC–TC split/configuration families; sample count not stated in README.
- **Format / language:** Python; CSV; prompts; saved responses/results. English prompts; benchmark content inherits source translations.
- **Origin:** LLM research harness over real/educational benchmark artifacts; model-generated predictions are not gold labels.
- **Labels / ground truth:** Benchmark links/splits and saved model responses; distinguish labels from predictions.
- **Licence quoted:** “Apache License, Version 2.0” — [licence evidence](https://github.com/Noufst/TraceLLM/blob/main/LICENSE).
- **Commercial internal use:** Apache-2.0 harness code yes; original benchmark data rights unresolved.
- **Redistribution:** Apache code with notices; original data per-source clearance.
- **Model input:** Harness with cleared inputs yes; bundled CM1/EasyClinic text not automatically cleared.
- **Freshness:** Last observed default-branch commit: [2024-11-06](https://github.com/Noufst/TraceLLM/commit/411269e2bd8e9e0666486315eee501e6eb9be28a). Observed commit 2024-11-06; static replication code.
- **Known problems:** Code is Apache-2.0, but bundled CM1/EasyClinic text and links retain source-rights questions. Reuse harness code with cleared inputs. API models/prompts may be stale; requirement→test tracing is not executable test-case generation.

#### H3 — Qodo Cover (formerly Cover-Agent)

[Repository / dataset](https://github.com/qodo-ai/qodo-cover) · Serves needs **4,7** · **Candidate with network copyleft**

Reusable generation→execute→coverage→retry loop. Useful implementation reference for accepting/rejecting generated tests.

- **Size:** Example/suite count not stated; code and templated multi-language examples.
- **Format / language:** Python; prompts; source/test files; Cobertura XML. English prompts/docs; programming-language examples vary.
- **Origin:** LLM unit-test generator; its generated outputs are synthetic.
- **Labels / ground truth:** Build/test results and coverage changes; no independent semantic correctness ground truth.
- **Licence quoted:** “GNU AFFERO GENERAL PUBLIC LICENSE” — [licence evidence](https://github.com/qodo-ai/qodo-cover/blob/main/LICENSE).
- **Commercial internal use:** Yes under AGPL-3.0.
- **Redistribution:** AGPL source/licence obligations; applicable modified network use requires source offer.
- **Model input:** Internal input/evaluation yes; generated/copied code and covered integration require assessment.
- **Freshness:** Last observed default-branch commit: [2025-06-24](https://github.com/qodo-ai/qodo-cover/commit/adcf55baba40e8fbf8a84e68b70d08bef1e2b9c9). README explicitly says no longer maintained (notice 2025-06-15); last observed commit 2025-06-24.
- **Known problems:** AGPL-3.0 is commercially usable with obligations, including applicable source-offer duties for modified network-served software. Not a requirements-driven automotive generator. Coverage gain can coexist with weak/wrong assertions; stale dependencies require work.

#### H4 — SWE-bench harness and SWE-bench Verified

[Repository / dataset](https://github.com/SWE-bench/SWE-bench) · Serves needs **6,7** · **Conditional**

Reproducible agent-task evaluation with base revisions, gold/test patches and FAIL_TO_PASS/PASS_TO_PASS tests.

- **Size:** SWE-bench Verified: 500 tasks, 6.31 MB as displayed on HF. Do not substitute full/Lite/multilingual task counts.
- **Format / language:** Python; Docker/container environments; JSON/Parquet; patches. English issue text; original Verified targets Python projects.
- **Origin:** Real GitHub issues, fixes and human-screened tasks.
- **Labels / ground truth:** Issue-associated test transitions and reference patches; valid solutions can differ from gold patch.
- **Licence quoted:** “MIT license” — [licence evidence](https://github.com/SWE-bench/SWE-bench/blob/main/README.md).
- **Commercial internal use:** MIT harness yes; each task's repository/issue/patch rights separately apply.
- **Redistribution:** MIT harness notices; task sources/patches per original project.
- **Model input:** Cleared tasks yes; no assumption that the harness MIT relicenses issue text or gold patches.
- **Freshness:** Last observed default-branch commit: [2026-09-02](https://github.com/SWE-bench/SWE-bench/commit/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e). Harness observed commit 2026-09-02; HF Verified lastModified 2026-08-16. Maintained infrastructure.
- **Known problems:** Harness MIT does not override each benchmark repository's source/test/issue rights; HF card did not expose a separate licence field in verified API metadata. The separate project website's licence is not the harness licence. Generic Python tasks do not measure automotive requirements, C timing, MISRA or TARA; public benchmark contamination is likely.

Additional evidence: [Opened Verified dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified).

#### H5 — OSV-Scanner

[Repository / dataset](https://github.com/google/osv-scanner) · Serves needs **5,7** · **Code candidate; feeds conditional**

SBOM/dependency vulnerability triage and offline scanning; useful deterministic comparator to an LLM's package/version findings.

- **Size:** Regression/example count not stated; README says 11+ language ecosystems and 19+ lockfile types.
- **Format / language:** Go; lockfiles; SPDX/CycloneDX; JSON reports; offline advisory database. English
- **Origin:** Real maintained security tooling plus authored regression fixtures.
- **Labels / ground truth:** Expected regression matches and authoritative advisory ranges; no ground-truth firmware exploitability rating.
- **Licence quoted:** “Apache-2.0” — [licence evidence](https://github.com/google/osv-scanner).
- **Commercial internal use:** Apache-2.0 scanner yes; advisory data per-source.
- **Redistribution:** Apache scanner notices plus any data redistribution terms.
- **Model input:** Cleared advisory inputs only; offline mode does not change source licences.
- **Freshness:** Last observed default-branch commit: [2026-11-12](https://github.com/google/osv-scanner/commit/80fe50567a5d6e0ec408353e2ceacca1561b91be). Active; observed commit 2026-11-12.
- **Known problems:** Tool Apache-2.0 does not clear downloaded OSV feeds. Apply S6 source filtering before offline database ingestion; confirm the pinned scanner's offline schema/flags. C/C++ vendored-component discovery and SBOM completeness can affect results.

## 3. Needs without a suitable verified public substitute

These are **gaps in the commercially usable evidence found in this search**, not a claim that no public example exists anywhere.

| Gap | What the public material actually covers | What to create or obtain internally |
|---|---|---|
| Complete automotive requirements→tests→executions→defects chain | RTEMS is embedded and partial; LibEST is embedded-adjacent with links but unclear dataset reuse terms; EasyClinic is educational. | A rights-cleared vehicle-function slice with stable requirement IDs, reviewed tests, execution environments/results and defect/root-cause links. |
| Native German and Japanese labelled automotive specifications | TOPPERS supplies Japanese embedded engineering/test text. No native German or Japanese automotive corpus with verified type/defect/trace labels and clear commercial rights was established. Machine translations are not equivalent. | Native authored/anonymized requirements with bilingual domain review, type/quality labels and trace links. Do not present machine translations as native industrial gold data. |
| Safety/ASIL/interface labels and completeness defects | QuRE labels weak-word quality judgments; PROMISE labels FR/NFR classes. Neither supplies comprehensive automotive ASIL allocation, interface classes or missing-requirement truth. | Expert-assessed functional/safety/interface requirements, safety allocations and seeded omissions with explicit created-data labels. |
| Complete legitimate production DBC+ARXML+matching raw traffic | opendbc provides reverse-engineered DBCs; cantools supplies format fixtures; ROAD is real but anonymized/obfuscated. They are not interchangeable views of one OEM architecture. | A licensed architecture/network export and recordings from the same known configuration, including revision and signal truth. |
| Large production DLT logs with fault/root-cause labels | dlt-daemon and python-dlt supply format fixtures. Loghub is primarily IT/mobile systems and lacks a clear general commercial grant. | Sanitized, permissioned ECU/head-unit logs with independently confirmed fault windows, root causes and duplicate-event labels. |
| Automotive/embedded duplicate-bug benchmark | Eclipse and GitBugs provide general software/tooling duplicates, not a verified automotive ECU incident corpus. | Curated product issue clusters, time-based splits and withheld future duplicate decisions. |
| Independently validated complete TARA risk ratings | V2X PKI provides assets, threats, impact scores and formal results. OpenASC is AI-assisted reference content. Impact/CVSS/author feasibility fields are not an independently adjudicated final automotive risk oracle. | Item definitions, damage/threat scenarios, attack paths, feasibility, impact, calculated risk, treatments and independent cybersecurity review. |
| Official machine-readable ATM / UN R155 gold corpus with suitable reuse terms | OpenASC supplies third-party Annex 5 mappings. The opened [Auto-ISAC ATM page](https://automotiveisac.com/atm-white-paper) offers a white paper; no suitably licensed machine-readable ATM dataset was verified. | Obtain a licensed structured catalogue, or build and review permitted structured mappings while preserving official source/version references. |
| Full ISO/MISRA standard text and official compliance oracles | Public software and authored regression tests exist; they do not grant the right to bulk-reuse copyrighted standards. | Licensed standards access covering the intended processing; independently written tests and reviewed rule-ID/deviation labels. |
| LLM extraction/test generation proven on end-to-end automotive work | TraceLLM evaluates tracing; Qodo generates unit tests from code and is unmaintained; FRET formalizes requirements but is not an LLM. | A task-specific orchestration layer and held-out automotive evaluations. No recommended turnkey system here proves all seven capabilities. |

An apparently relevant [automotive_TARA_framework repository](https://github.com/kazi-sahb/automotive_TARA_framework) was opened but **excluded from the data inventory**: its current root contains README and LICENSE, while its README asks interested users to contact the team for the tool. The Apache-2.0 file does not make the referenced absent .tb7/.tm7 artifacts publicly available. This is a concrete example of why README claims alone were insufficient.

No suspected proprietary OEM/supplier dump was admitted. For subsequent ingestion, exclude confidentiality-marked files, supplier customer exports, copied paid ISO/MISRA manuals and OEM ARXML/DBC collections lacking an affirmative grant. “Found on GitHub” and anonymization are not evidence of permission.

## 4. Recommended smallest starter set

**Smallest practical executable end-to-end set: T1, comprising two linked repositories.**

1. Pin [RTEMS/rtems-central](https://github.com/RTEMS/rtems-central) at the observed snapshot recorded in [source-audit.json](evidence/source-audit.json). Use its matching `modules/rtems` submodule revision **824c485a9b970c847ab3bb4608106fdc7b0a7f45**, rather than pairing the older specification generator with arbitrary current RTEMS main.
2. Check out the corresponding [RTEMS implementation](https://github.com/RTEMS/rtems). Begin with the event send/receive requirements and validation target. The inspected requirement and validation YAML files explicitly offer **CC-BY-SA-4.0 OR BSD-2-Clause**; choose the BSD option for those files. The inspected generated C test is **BSD-2-Clause**. Check selected implementation/build dependencies separately.

Concrete source slice:

- [Natural-language pre/postconditions and transitions](https://github.com/RTEMS/rtems-central/blob/master/spec/rtems/event/req/send-receive.yml)
- [Validation links and C target path](https://github.com/RTEMS/rtems-central/blob/master/spec/rtems/event/val/send-receive.yml)
- [Existing generated C validation test](https://github.com/RTEMS/rtems/blob/main/testsuites/validation/tc-event-send-receive.c)

The linked files show the artifact relationships; use the pinned revisions for actual comparison. The GitHub snapshot is old and the successor generator is now marked unmaintained, so use this as a reproducible benchmark slice with pinned dependencies.

**Evaluation flow:** extract requirement IDs, natural-language conditions and relations from the YAML; normalize them; ask the model to produce trace-linked test cases and C test code; compile/run in a supported RTEMS simulator configuration; compare with the withheld validation mappings and assertion behavior. Hide `test-code`, gold validation files, generated reference tests and saved results from the model's context. Score extraction/trace precision and recall, compile/run success, assertion correctness and condition/transition coverage separately. Coverage alone is insufficient. Any new fault mutants or rendered format-stress documents you create are **internally constructed additions**, not new public industrial ground truth.

This two-repository set tests extraction and executable test generation, but it is structured embedded input rather than an automotive PDF/ReqIF benchmark.

**Smallest meaningful automotive extension:** add [QuRE (R1)](https://zenodo.org/records/16049822) for real automotive text and quality labels. This gives an automotive classification evaluation alongside the RTEMS executable generation evaluation; it does not create missing QuRE-to-RTEMS trace links.

Useful optional additions, in order:

1. [FRET (H1)](https://github.com/NASA-SW-VnV/fret) as a formalization/test-generation comparator. Keep its generated tests separate from independent gold tests.
2. [cantools (N2)](https://github.com/cantools/cantools) project-authored DBC/ARXML fixtures for exact CAN encode/decode assertions; audit imported examples.
3. [reqif (R5)](https://github.com/strictdoc-project/reqif) project-authored round-trip/invalid-input tests for ReqIF ingestion.
4. [ROAD (N5)](https://zenodo.org/records/10462796) for real CAN replay/anomaly tasks; it is not needed for the minimum requirements→tests loop.

Keep QuRE grouped by unique requirement, traceability artifacts grouped by project, and generated C regressions grouped by code/generation family. Freeze licence notices, versions, input hashes, tool settings and test environments with each evaluation run.

## 5. Licence risk: material to keep out of a commercial default corpus

| Item / scope | Decision and reason |
|---|---|
| **R7 AUTOSAR standards text** | Hold until an applicable agreement grants the intended commercial processing and sharing. Downloadability is not a general commercial grant. Use official releases; avoid unlicensed mirrors. |
| **R3 PURE; R4 ReqEval** | Hold underlying documents/requirement text until individually cleared. Both disclose an assumption or uncertainty about source rights; curator CC BY metadata does not cure that. |
| **T3–T5 CoEST benchmark data; T6 COMET assembly** | Hold the imported dataset texts/links for commercial use until the relevant rights scope is established. CoEST's GPL licence clearly covers a tool repository, but does not independently establish authority over every imported document; COMET has no licence stated at its verified root. |
| **D5 Loghub** | Research/academic availability is stated; a sufficient general commercial grant was not established. Obtain permission before using it in the commercial harness or training corpus. |
| **S6 OSV: Chainguard/Wolfi-origin advisories** | Do not ingest automatically. Official source terms include **CC BY-NC-ND 4.0** and a distinct Commercial Scanners licence. Determine which terms cover your precise use; unrestricted full-dump reuse cannot be assumed. Preserve source licences for all retained records. |
| **V1 FreeRTOS MISRA wording; other copied ISO/MISRA/AUTOSAR excerpts** | Exclude normative standard excerpts until permission is confirmed. The kernel's MIT grant does not establish ownership of third-party standards wording. Project-authored code, deviations and rule IDs are a different scope. |
| **R2 expanded PROMISE web-derived text and unlicensed analysis code** | Data-file CC BY-SA 3.0 is real evidence, but review added-source rights and code grants; do not relicense the expansion or accompanying code as permissive. |
| **R5/T2/N2 imported fixtures; R6 TTSP3 files; S8 ScanCode samples** | Use an allowlist based on provenance and file-specific terms. The tool's root licence is not a licence for every external sample. |
| **D3/D4 bug text and attachments** | Depositor CC licences were verified, but do not automatically clear original contributor text, copied attachments, credentials or personal information. Exclude unreviewed attachments and copied legacy collections. |
| **H2 TraceLLM bundled data; H4 SWE-bench task sources** | Reuse the licensed harness code; preserve and check the original data/repository/patch licences separately. |
| **Kaggle mirror with “Unknown” licence** | Excluded; use a version with actual licence evidence rather than relying on its public data card. |

**GPL, LGPL, MPL and AGPL are not non-commercial licences.** ICSim, Cppcheck, openAUTOSAR, python-can, DLT tools and Qodo Cover can be used commercially subject to their respective obligations. Distribution, linking, modifications and AGPL network interaction change the obligations; their inclusion in the inventory is not approval to embed them without those conditions. The report distinguishes these from missing/uncertain grants and non-commercial feed terms.

**Lowest-friction initial data scopes:** author-released QuRE under CC BY 4.0; the verified BSD-option RTEMS requirements/test slice; CC0 CycloneDX and SPDX documents; project-authored MIT/Apache parser fixtures; ROAD under CC BY 4.0; and the MIT V2X PKI research artifact. These remain subject to the specific scope/limitations described above.

## Deliverables and audit trail

- [Machine-readable CSV inventory](automotive-harness-data-inventory.csv)
- [Full JSON inventory](automotive-harness-data-inventory.json)
- [Repository commit evidence and methodological notes](evidence/source-audit.json)
- Raw public Zenodo metadata: [QuRE](evidence/zenodo-16049822.json), [PURE](evidence/zenodo-7118517.json), [ROAD](evidence/zenodo-10462796.json), [Eclipse](evidence/zenodo-15348468.json), and [additional traceability classification record inspected during discovery](evidence/zenodo-7867846.json)
- [COMET GitLab project metadata](evidence/comet-gitlab-project.json)

No implementation code or working dataset copy is included. This is a source-selection and rights-evidence inventory, ready to guide an allowlisted download/benchmark plan.

