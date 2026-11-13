# Zyn: research summary and build plan (Sift into Forge)

Status: proposal. No code written. Waiting for Tom's go-ahead.
Date: 13 November 2026.
Label for everything built from this plan: "Zyn prototype."

---

## Part 1. What the research settles and what it leaves open

**What was read:** `research/automotive-harness-data-report.md` (41 sources, ranked by need, licence assessed), the CSV and JSON inventories (same 41 entries in machine-readable form, no extra content), and the evidence folder (commit SHAs for 31 GitHub repos, RTEMS submodule pins, Zenodo and GitLab licence records).

**Scope of the research:** it is a data and licence inventory. It says nothing about harness architecture, model choice, orchestration, review UI or schemas. Those decisions are in Part 2 and are mine, not the research's.

### Settled

1. **Usable data for Sift evaluation exists, but none of it is an automotive spec with known-correct output.**
   - QuRE (CC BY 4.0): 2,111 real automotive requirements with human quality-review labels (weak words, ok/defect). Good for the quality-flag part of classification. No type, subsystem or test labels.
   - PROMISE NFR, original 625 (CC BY-SA 3.0 in the data header): functional/non-functional type labels. Not automotive. The expanded 969 set has unresolved source rights; use the original only.
   - RTEMS event send/receive slice (BSD-2-Clause option): structured requirements with pre/postconditions and explicit links to validation tests. Embedded RTOS, not automotive. Pinned to rtems-central `82230386` and RTEMS submodule `824c485a`.
2. **Usable data for Forge evaluation:** RTEMS is the only cleared source with real requirement-to-test links. LibEST has a requirement-to-test answer file but no licence (hold).
3. **CAN tooling is clear:** cantools (MIT) parses DBC/ARXML and encodes/decodes frames, so signal mapping can be checked by code, not by the model. python-can (LGPL) gives a virtual bus. opendbc (MIT) has real reverse-engineered vehicle DBCs if realism is wanted.
4. **ReqIF export is solved:** strictdoc-project/reqif (Apache-2.0). ReqIF is what DOORS and Codebeamer import.
5. **Exclusion list is explicit:** PURE, ReqEval, CoEST (EasyClinic, CM1, eTOUR), COMET/LibEST, AUTOSAR RS CAN, Loghub, MISRA wording inside FreeRTOS, OSV restricted feeds. I add one the report did not flag: Zenodo record 7867846 is CC BY, but its requirement text comes from CoEST and COMET, so it inherits their hold.
6. **No public end-to-end automotive chain exists** (requirements to tests to results to defects). The research states this as a gap.

### Left open

1. **Ground truth for the actual demo use case** (an OEM-style spec in, requirements and tests out). Must be authored synthetically. Synthetic gold written by me is only as good as whoever reviews it.
2. **Subsystem taxonomy and requirement attribute schema.** Not in the research. Placeholder needed.
3. **Native German or Japanese specs.** None cleared. English only for now.
4. **Safety/ASIL and interface labels.** No public gold set. The harness can propose them; nothing can score them.
5. **Executable test validation.** RTEMS tests are C on an RTOS simulator. Forge first half generates Python scripts that will not be run against a real or simulated ECU. Out of scope for now.
6. **Nothing was downloaded or run by the researcher.** Licence calls are document-based. I have not re-verified them.

---

## Part 2. Build plan

### 2.1 Design principles

- Every model output is validated against a schema. Failure after retries is recorded as a failure, never accepted as free text.
- Every claim a model makes about the source is checked by code where code can check it (quotes exist in the source, signal names exist in the DBC, every test traces to an approved requirement).
- Nothing moves to the next step until a human approves it. Each step reads only approved records.
- The model is a config value. Same workflow, same prompts, same schemas on every model.
- Plain Python pipeline, not an agent framework. Fewer moving parts, easier to audit, easier to explain in a demo.

### 2.2 Components and named tools

| # | Component | What it does | Tool (licence) |
|---|---|---|---|
| 1 | Model switch | One call interface for hosted and local models. Switching = editing one line in `config.yaml`. | LiteLLM (MIT) |
| 2 | Hosted models | Cloud tier. | Claude via Anthropic API; optionally OpenAI |
| 3 | Local open-weight models | On-premise tier. Runs on this PC's GPU. | Ollama (MIT) with Qwen3 14B, Mistral Small, gpt-oss-20b, Llama 3.x. Fallback: LM Studio |
| 4 | Structured output | Defines schemas, forces the model to fill them, retries on validation failure. | Pydantic v2 (MIT) + Instructor (MIT) |
| 5 | Document ingestion | PDF/DOCX into text with section hierarchy and tables kept. | Docling (MIT) |
| 6 | ReqIF in/out | Reads ReqIF input, writes ALM-ready ReqIF export. | reqif (Apache-2.0) |
| 7 | Excel/CSV export | Reviewer-friendly export. | openpyxl (MIT) |
| 8 | CAN matrix | Loads DBC, validates signal names and value ranges, encodes frames to IDs and bytes. | cantools (MIT) |
| 9 | Test script target | Generated scripts use pytest and a virtual CAN bus. | pytest (MIT), python-can (LGPL, used as a library, not modified) |
| 10 | Script static checks | Generated Python must parse and pass lint. Not executed against hardware. | Python `ast`, Ruff (MIT) |
| 11 | Review UI | Table per step: approve, edit, reject, comment. Prototype banner on every page. | Streamlit (Apache-2.0) |
| 12 | Audit store | Append-only log of every generation, edit, approval, rejection. | SQLite (public domain), via Python stdlib |
| 13 | Evaluation runner | Runs a dataset through a workflow on a chosen model, scores against gold, writes a report. | Own code + pytest |

Not used, with reason: LangChain/LangGraph (extra abstraction, harder to audit), PyMuPDF (AGPL), Qodo Cover (AGPL, unmaintained), MCP/A2A (not needed for a single-machine demo; can wrap the pipeline as an MCP server later).

### 2.3 Workflow

**Sift**

1. Ingest. Docling turns the spec into sections (id, heading, level, text, tables). Stored with a SHA-256 hash of the source file.
2. Map sections to subsystems. Model picks from the placeholder taxonomy (enum in schema, so it cannot invent a subsystem) plus confidence and rationale. Human reviews.
3. Extract requirements per approved section. Each requirement carries a verbatim source quote. Code checks the quote exists in the section text. Failing quotes are flagged "ungrounded" in the review table.
4. Classify each requirement: type, verification method, quality flags. A deterministic weak-word list runs alongside the model and both results are shown.
5. Human review of requirements.
6. Export approved set: ReqIF, XLSX, JSON.

**Forge, first half**

7. Generate test cases per approved requirement, one or more per test design technique that applies.
8. Traceability check (code): every test points to an approved requirement; every requirement shows its test count; zero-test requirements are highlighted.
9. CAN mapping: model links signal names in test inputs and expected outputs to DBC signals. Code checks the signal exists and values sit inside DBC min/max, then cantools produces frame ID and payload bytes.
10. Human review of test cases and mappings. Export test cases (XLSX, JSON).
11. Generate one pytest script per approved test case. Code checks it parses and lints. Scripts are marked "UNTESTED: not executed on bench or simulator".

### 2.4 Data schemas (draft)

Field names are our own placeholders.

**SourceDocument:** doc_id, filename, sha256, ingested_at, page_count, sections[].

**Section:** section_id, doc_id, number (e.g. "4.2.1"), heading, level, text, page_start, page_end.

**SubsystemMapping:** section_id, subsystem_id (enum from `taxonomy_placeholder.yaml`), confidence (0 to 1), rationale.

**Requirement:**
- req_id (e.g. `REQ-CLU-0042`, generated by code, not the model)
- section_id, subsystem_id
- text (normalised "shall" statement)
- source_quote (verbatim), grounded (bool, set by code)
- req_type: enum [functional, performance, interface, safety, security, usability, reliability, constraint, other]
- verification_method: enum [test, analysis, inspection, demonstration]
- quality_flags: list of enum [weak_word, ambiguous, not_atomic, not_testable, missing_condition, missing_value]
- asil_hint: enum [none, QM, A, B, C, D, unknown], labelled "model suggestion, not a safety assessment"
- status: enum [proposed, approved, edited, rejected]

**TestCase** (fields):
- tc_id, req_ids[] (traceability)
- test_type: enum [requirement_based, fault_injection, equivalence_class, operational_use_case, functional_dependency]
- test_method: enum [black_box, white_box, hil, sil, manual]
- objective, preconditions[], input_conditions[], expected_outputs[]
- each input/output: signal_name, value, unit, timing_ms (optional)
- status

**CanMapping:** tc_id, step_index, signal_name, dbc_message, frame_id, value, encoded_bytes, in_range (bool, code), resolved (bool, code).

**TestScript:** tc_id, filename, code, parses (bool), lint_clean (bool), executed: always false in this phase.

**AuditEvent:** event_id, timestamp, actor (human name or "model"), action [generated, edited, approved, rejected, exported], object_type, object_id, before_json, after_json, model_id, provider, prompt_version, prompt_sha256, input_sha256, tokens_in, tokens_out, latency_ms. Append-only.

### 2.5 Evaluation using public data

All runs are repeated per model with identical prompts and schemas. Outputs: one comparison table per run, plus the raw records. These are benchmark numbers for the prototype on these datasets. They are not productivity or accuracy claims.

| Eval | Dataset | Task | Scored by |
|---|---|---|---|
| E1 Quality flags | QuRE, split by unique requirement | Flag weak words and defects | Precision, recall, F1 against human review labels |
| E2 Type classification | PROMISE NFR original 625 | Functional vs non-functional, plus NFR subclass | Macro F1 |
| E3 Extraction and grounding | RTEMS event send/receive spec, rendered into a document (rendering is our own construction) | Extract requirements and conditions | Recall of the spec's items; share of quotes found verbatim |
| E4 Test coverage | Same RTEMS slice; validation files withheld from the model | Generate test cases | Share of pre/postcondition combinations and transitions covered; trace correctness |
| E5 CAN mapping | Synthetic cluster DBC (authored by us), optionally cantools project-authored fixtures | Map signals, encode | Share resolved correctly; out-of-range catches |
| E6 Schema discipline | All of the above | Valid output | First-pass validation rate, retries, hard failures |
| E7 End-to-end demo | Synthetic instrument cluster spec, 30 to 50 requirements, with answer key | Full Sift into Forge | Same metrics as E3 to E5, plus reviewer edit rate from the audit log |

E7 is the only automotive end-to-end test, and its answer key is author-made. It needs an engineer's review before any number from it is quoted anywhere.

Data handling: pinned versions, input hashes, licence notices and attribution stored with each run. Gold files kept out of the model's context. Nothing redistributed.

### 2.6 Build phases

| Phase | Output | Done when |
|---|---|---|
| P0 Skeleton | Model switch, schema validation, audit store, empty review UI with prototype banner | Same test prompt returns validated output from Claude and from a local model |
| P1 Sift | Steps 1 to 6 | Synthetic spec goes in, reviewed requirements come out as ReqIF and XLSX |
| P2 Evals E1 to E3, E6 | Evaluation runner and first comparison table | Report generated for at least one hosted and one local model |
| P3 Forge first half | Steps 7 to 11, synthetic DBC | Approved requirements produce reviewed test cases, CAN mappings and linted scripts |
| P4 Evals E4, E5, E7 | Full benchmark report | Side-by-side model table across all evals |

### 2.7 Folder layout

```
E:\Claude\Zyn\
  research\                 (existing, read-only)
  docs\                     plans, decisions, eval reports
  harness\
    models\                 model switch config
    schemas\                Pydantic schemas
    sift\                   ingest, map, extract, classify, export
    forge\                  generate, trace, can_map, scripts
    review\                 Streamlit app
    audit\                  SQLite store
  taxonomy_placeholder.yaml clearly labelled PLACEHOLDER
  data\
    synthetic\              our cluster spec, answer key, DBC
    public\                 downloaded datasets, pinned, with LICENCE files
  evals\                    runners and gold files
  runs\                     outputs per run (git-ignored)
  config.yaml               model choice and settings
  .env                      API keys (never committed)
```

### 2.8 What Tom has to install

Checked on this PC: Ryzen 7 5800X, 32 GB RAM, AMD Radeon RX 9070 XT (16 GB class card; Windows reports VRAM wrongly as 4 GB), 126 GB free on E:. Git is installed. Python 3.15 is installed, which is too new for some of these libraries.

1. **uv** (Python project manager). Installs a pinned Python 3.12 for this project only and every library in one step. Your existing Python stays untouched. One PowerShell command from astral.sh, then `uv sync` inside the project.
2. **Ollama for Windows**, for local models. Then one pull per model (about 9 to 14 GB each). AMD RX 9070 support on Windows: not verified by me. If Ollama does not use the GPU, LM Studio (Vulkan backend) is the fallback.
3. **Anthropic API key**, entered by you into `.env`. I do not handle keys. Optional OpenAI key for a third comparison point.
4. **Docling model download**, automatic on first run, about 1 to 2 GB.

Total disk: roughly 30 to 45 GB with two or three local models.

---

## Decisions after Tom's review (13 November 2026)

Tom's answers:
- **Ownership:** personal project, built to test how far the approach can be pushed.
- **Review:** no engineer will review gold data. Gold data and answer keys are authored by Claude and checked by an independent AI reviewer pass. Every reported number must state this.
- **Taxonomy size:** left to me. Decision: 12 placeholder subsystems for the cluster and adjacent domains, extendable. Small enough to review.
- **Version control:** local git repository, no remote.

Changes to the plan made during P0:
- **LiteLLM and Instructor dropped.** Replaced by two thin adapters: the official Anthropic SDK (Claude) and the Ollama client (local models). Both constrain output to the schema natively; Pydantic re-validates everything. Fewer dependencies, same one-line model switch.
- **AI reviewer role added.** A second model call reviews generated items against the source (faithful, atomic, testable, type, quote) and lists missed requirements. Advisory only: the audit store refuses approvals from any actor that is not a named human. Can run on a different model from the generator for an independent check.
- **Refusal fallback on Claude profiles.** If Claude declines a request on safety grounds, the API reruns it on a fallback model. The served model is logged on every call and flagged when it differs from the requested one, so benchmark tables stay honest. Can be switched off per profile.
- **Python 3.11 venv instead of uv.** Python 3.11 was already installed; no extra tool needed. Versions pinned in `requirements.lock`.

Changes after the first live Sift review (13 November 2026):
- **The override-reason rule biased review toward rejection.** On run 20261113-165443-9c129b, all 9 items whose AI objection had no one-click fix were rejected, although their text was correct; the objections were about flags, ASIL hints or quote length. A review step should not make rejecting a correct item the easy path.
- **Reviewer prompt v3** (`review_requirements_v3`) says whether each objection is about the text or only about labels, returns flag corrections in their own field, and no longer objects to ASIL hints merely for not being stated in the source (the extraction prompt asks for a hint). v1 and v2 stay unchanged for reproducibility.
- **Standard reasons for approving over an objection.** A short list, none preselected, plus free text. Every approval still records a reason in the audit trail.
- **Code check on AI suggestions.** A suggestion is not offered as a one-click fix if it contains notes or flag names, changes the modal verb, adds numbers not in the section, or uses wording largely absent from it. Any edited version is checked the same way. This came from REQ-GAUGE-010, where the reviewer's flag note was applied into the requirement text and exported.
- **An unchanged "AI fix" no longer clears the reason rule**, enforced in the audit store.
- **Concurrent extraction blocked.** Each section is claimed atomically before extraction; a second extraction of the same run (another tab, the CLI) skips claimed sections. Run 20261113-153325-e3d211 holds 48 duplicates from before this fix.

## Open questions for Tom (answered 13 November, kept for the record)

1. **Taxonomy placeholder.** Draft a short placeholder (about 12 subsystems for an instrument cluster and adjacent domains), or attempt a much larger one? I recommend 12: smaller is easier to review.
2. **Synthetic spec and answer key.** I can draft a fictional instrument cluster spec, DBC and answer key. Can an engineer review the answer key, or does it stay labelled "author-made, unreviewed"?
3. **Version control.** Initialise a git repository in `E:\Claude\Zyn`? Recommended, local only, no remote.