# Zyn direction: checker and benchmark

> Forge was renamed **Anvil** on 13 November 2026 (it clashed with AskUI's Forge). Older text below keeps the name it had when written.

Decided 13 November 2026 by Tom, after reading `research/automotive-embedded-ai-practitioner-research-2026-11-13/`.

## The decision

Zyn checks and measures engineering work. It does not compete on generating it.

Requirement and test generators are a crowded field, and generated volume is the thing engineers trust least. The research's strongest signals point elsewhere:
- Reviewing existing work is the most requested use (10 of 23 eligible discussions).
- Inspecting and correcting AI output is the most reported cost (14 of 23).
- Engineers want results they can verify against the source, concrete support states instead of confidence scores, decisions that persist, and tools that fit their existing requirements tools.
- Sending protected material to a cloud service is a hard veto where it applies.
- Nobody has published a local-versus-hosted comparison on automotive tasks, or trustworthy effort numbers.

The research is qualitative: 23 public discussions, 4 from self-identified automotive practitioners. It shows which problems occur, not how often. Validate with real engineers before committing months.

## What Zyn becomes

1. **Sift Review.** Import an existing requirement set (ReqIF, Excel, CSV), keep its IDs, and check it: deterministic code checks plus an AI reviewer whose findings must quote the words they are about. Findings are confirmed or dismissed by a named person, and dismissals carry over to later runs of the same text.
2. **Sift Delta.** Compare two revisions of a spec or requirement set and mark approved requirements whose source changed or disappeared. Mostly deterministic.
3. **Benchmark.** Run any model (hosted or local) against the same answer keys. Report accuracy, run-to-run stability, cost, and reviewer effort from the audit log. Offline mode refuses cloud models.
4. **Forge, generator first.** For signal-based tests the model maps requirements to signals and template parameters; code generates the cases from the DBC. Expected results trace to a requirement clause.

Sift extraction from prose specs stays as one way to get requirements in. Zyn Scribe is undecided. Zyn Source (procurement and RFQ) is parked: no evidence supports it.

## Not building

Autonomous TARA, MISRA compliance verdicts, safety sign-off, automatic baselining, productivity claims.

## Order

1. Sift Review (with findings export and scoring against the ICX-100 answer key).
2. Sift Delta.
3. Benchmark and offline mode (needs Ollama installed).
4. Forge, generator first.

## First Sift Review result (13 November 2026)

Run 20261113-173817-bae71f on the 46 ICX-100 gold requirements as a CSV (`data/synthetic/icx100_reqset.csv`), Claude Opus as reviewer, 4 calls, about USD 0.15.

- Code checks alone: 4 of 17 expected flags (all 4 weak words), none outside the key.
- Code plus AI: 11 of 17 expected flags, 15 flags not in the key (mostly "unclear reference" and "ambiguous"; some are defensible because the set is read without the spec around it). 22 of 46 requirements have findings.
- Every AI finding quoted words that are in the requirement.
- Conflicts: found 1 of the 4 known spec issues (two signal-loss timeouts). The startup-timing conflict spans batches of 15, which the reviewer does not compare across. Needs a set-level pass.
- Misses: where a vague word is the problem, the reviewer reports the vague word but not the "not testable" and "missing value" the key also expects.

The key is author-made and AI-reviewed, and only 9 of 46 requirements carry flags. Treat these as a smoke test of the method, not a measure of quality.

## Built on 13 November 2026 (after the first Sift Review)

- **Support states**: requirement cards show concrete checks instead of model confidence; mapping confidence is labelled as the model's self-rating.
- **Offline mode** and a **full call record** (prompt, input and response kept for replay).
- **Sift Review**: set-wide conflict pass and merging of duplicate reports (code and AI flagging the same problem become one finding with "also reported by").
- **Effort and cost** panel and `metrics` command, from the audit log only.
- **Sift Delta**: spec revision against an approved run, or two set exports by ID. Deterministic. On the synthetic ICX-100 revision 2 it finds 8 of 8 expected changes with no spurious entries.
- **Benchmark** (`bench`): mapping and Sift Review on several models, repeated, with stability.

Still open: Scribe, a local model run (needs Ollama installed), rewording three old commit messages, and the old tool names in the Hyperpilot note.

### First benchmark (13 November 2026, report in [bench/2026-11-13-icx100.md](bench/2026-11-13-icx100.md))

Opus 5.5, Sonnet 5.5 and Haiku 5.5, two runs each, about USD 0.64 in total. Local models not run (Ollama not installed).
- **Section mapping**: all three 16 of 16, identical on repeat. Haiku did it for USD 0.001 a run against 0.034 for Opus. On this spec the cheapest model is enough for mapping.
- **Sift Review**: Sonnet found the most expected flags (11.5 of 17) at under half Opus's cost; Opus 10, Haiku 8. Every AI quote was located in its requirement for all three models.
- **Stability is the weak point**: repeats agree on only 39 to 58 percent of AI findings. A single run's findings are not reproducible, which supports keeping human decisions persistent and showing disagreement between runs as a signal.
- Haiku raises fewer flags outside the key (7.5 against 13), but also finds fewer of the expected ones.

Same caveats as above: small synthetic key, AI-reviewed, 17 expected flags. A comparison of models on this material, not a quality claim.

## Forge, first live run (13 November 2026)

Run 20261113-182131-30ee1c on the 39 approved requirements of Sift run 20261113-165443-9c129b, with the synthetic ICX-100 DBC. Claude Opus 5.5, about USD 0.57 (two sections failed on API errors and were retried with `forge resume`).

- 39 specs: 23 not automatable with this DBC (no bus signal shows the needle, the chime volume, diagnostics or updates), 12 event response, 2 threshold, 1 timeout, 1 periodic transmission.
- Code checks rejected 3 specs: the speedometer accuracy requirements need a template the library does not have (output tracks input within a tolerance band). The model forced them into the wrong template; validation caught it. Next template to add: tracking.
- Dry run of generation (not stored; specs await a person's approval): 54 cases, all passing on the correct simulation, catching 42 of 42 injected faults after adding a "value never appears" check for outputs that are not on/off. 25 cases carry an assumed value, mostly reaction times the requirements do not state. The generated pytest module lints clean.

These figures describe the generated tests against simulated faults, not the cluster.

Tracking template added the same day. Re-proposing the three rejected speedometer specs (one call, prompt forge_spec_v2): REQ-GAUGE-003 becomes a lower bound of the actual speed and REQ-GAUGE-004 an upper bound of actual x 1.1 + 4 km/h (traced to "10 percent" and "plus 4 km/h"); each gives 6 cases catching 3 of 3 injected faults in a dry run. REQ-GAUGE-001 still fails the checks because the requirement gives no tolerance at all, a defect in the requirement. The first attempt hit an API limit (at most 16 optional fields in a structured-output schema); the band is now a list of bounds, and a test guards the limit.

## Stability check, first live result (13 November 2026)

Two extra AI passes (Claude Opus 5.5, about USD 0.39) on Sift Review run 20261113-173817-bae71f, so three passes in all. Of 38 AI findings, 25 were reported in all three passes, 7 in two, 6 in one.

| AI findings counted | Expected flags found (of 17) | Flags not in the key | Conflicts listed |
|---|---|---|---|
| seen in any pass | 11 | 20 | 5 |
| seen in at least 2 passes | 11 | 17 | 2 |
| seen in all 3 passes | 11 | 12 | 2 |

Keeping only findings seen in every pass removed 40 percent of the flags outside the key without losing any expected flag. Both conflicts kept (G14/G17 low-fuel trigger, G30 vs G21/G22 signal-loss timeout) are known spec issues. The cost: the startup-timing conflict (G01 vs G44), also a known issue, appeared in only one pass and is filtered out. Recurrence is a useful signal for ordering a review, not a reason to hide single-pass findings; the screen shows them all by default with the count.

## Public data and the smaller items (13 November 2026)

- First scores on data Zyn did not author: [04-public-evals.md](04-public-evals.md). QuRE (automotive, human quality labels): the AI reviewer reaches F1 0.58 on defect flags against 0.51 for flagging every weak word, with high recall and modest precision. PROMISE (type classification): F1 0.93 for functional vs non-functional, macro F1 0.86 on coarse classes. RTEMS extraction (E3): 110 of 110 statements, all quotes verbatim, no modal changes; with whole components in view, 1 (Opus) or 3 (Sonnet) conditions wrongly extracted. RTEMS test coverage (E4) does not fit Forge's bus-signal design.
- Exported Forge tests now run on a simulated bench (pytest + generated conftest.py); faults switched on make the right tests fail.
- Requirements carry source page (PDF) and exact quote position; edited requirements show a word diff; earlier override reasons are offered for identical wording; Sift Review has an optional EARS check; bulk approval exists only for requirements whose every check passed, after ticking that they were read.
- Not done, with reasons: requirements from legacy code (needs the RTEMS code slice and an eval; after E3), live connectors to DOORS, Polarion or Codebeamer (needs access to those tools; ReqIF and Excel exchange covers it meanwhile), access control between projects (single-user local prototype), a with-and-without pilot measurement (needs engineers doing real work; the effort panel is ready to record it).

## Replay and project knowledge (13 November 2026)

From the competitive research ([05-competitive-landscape.md](05-competitive-landscape.md)), the two small items that were not built yet:
- **Replay**: a stored, schema-valid answer is reused when profile, model, prompt (including the knowledge file) and input all match. Logged as "replayed", zero tokens, shown as "Answers reused". Anything that must sample again (stability passes, benchmark, re-proposal, smoke test) uses `cfg.fresh()`.
- **Project knowledge file**: `knowledge.md` appended to every system prompt; its hash and line count are stored with each answer. The benchmark runs without it.
- Change impact on tests (stale Forge cases from a Delta) was already built.
- Not yet measured: whether a knowledge file improves Sift Review on ICX-100. Needs a benchmark run with and without it.
