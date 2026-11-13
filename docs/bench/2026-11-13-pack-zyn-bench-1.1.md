# Zyn benchmark pack zyn-bench-1.1: Opus, whole RTEMS components, knowledge file A/B

Date: 13 November 2026. Three repeats per model and task, every repeat asks the model again (no replay). Raw tables: `runs/pack/20261113-232031` (Opus, all tasks), `runs/pack/20261113-233035` (whole RTEMS components, Sonnet and Haiku), `runs/pack/20261113-235858` (knowledge file A/B). The Sonnet and Haiku baseline comes from the 1.0 run ([2026-11-13-pack-zyn-bench-1.0.md](2026-11-13-pack-zyn-bench-1.0.md)); the five 1.0 tasks and their data files are unchanged in 1.1 (same sha256).

Cost of these three runs: USD 10.95 (Opus 8.23, whole RTEMS 0.74, knowledge A/B 1.98).

## 1. Three models side by side

Score is the mean of three repeats; the range is lowest to highest.

| Task | Opus | Sonnet | Haiku |
|---|---|---|---|
| ICX-100 section mapping (accuracy) | 1.0 | 1.0 | 1.0 |
| ICX-100 requirement review (recall) | 0.608 (0.529 to 0.706) | 0.647 (0.647 to 0.647) | 0.49 (0.412 to 0.588) |
| ICX-100 review, item agreement | 0.6 | 0.6 | 0.44 |
| QuRE defect flags (F1) | 0.543 | 0.547 | 0.557 |
| PROMISE requirement type (accuracy) | **0.914** | 0.886 | 0.881 |
| RTEMS extraction, behaviour sections (recall) | 1.0 | 1.0 | 1.0 |
| RTEMS extraction, whole components (F1, new in 1.1) | 0.994 | 0.988 | 0.985 |

Cost per correct item (USD):

| Task | Opus | Sonnet | Haiku |
|---|---|---|---|
| ICX-100 review | 0.01667 | 0.00728 | 0.00063 |
| QuRE defect flags | 0.01744 | 0.00691 | 0.00044 |
| PROMISE requirement type | 0.00082 | 0.00034 | 0.00003 |
| RTEMS whole components | 0.00437 | 0.0021 | 0.00013 |

What this shows:

- **Opus does not buy better review here.** On the ICX-100 review Opus scored below Sonnet on average and varied more between repeats (0.529 to 0.706 against a flat 0.647). Item agreement was the same (0.6).
- **The one clear Opus gain is PROMISE classification**, about 3 points above the other two. That is a small task where the cheap models are already close.
- **QuRE weak-word flags do not separate the models at all.** All three sit between 0.54 and 0.56. The limit is the task, or the prompt, not model size.
- **Haiku stays the value choice for narrow tasks**: same score band at roughly one fortieth of Opus's cost per correct item on QuRE.
- **What to use:** Sonnet for review, Haiku for mapping, classification and extraction. Opus is not worth its cost on any task in this pack. `config.yaml` still sets Opus for both roles: the pack does not cover Anvil test-spec writing, so the generator role was left alone until that is measured.

## 2. The harder RTEMS task

`rtems-whole` gives the model whole RTEMS components, including the introduction text and "While ..." condition lines that must not be extracted, and scores F1 (so extracting too much now costs points).

All three models still score 0.985 to 0.994. The task is harder than the 1.0 one (no model is perfect in every repeat) but it still does not separate the models. A future task needs material where requirements are implied rather than written as "shall" statements, or where one sentence holds several requirements.

## 3. Knowledge file A/B

Same tasks, same models, with `knowledge.example.md` appended to every call (`pack run --knowledge`).

| Model | Task | Without file (1.0) | With file | Item agreement without / with |
|---|---|---|---|---|
| Sonnet | ICX-100 review | 0.647 | 0.608 | 0.6 / 0.5 |
| Sonnet | QuRE defect flags | 0.547 | 0.551 | - |
| Haiku | ICX-100 review | 0.49 | 0.51 | 0.44 / 0.48 |
| Haiku | QuRE defect flags | 0.557 | 0.564 | - |

**No measurable effect.** Every difference is inside the run-to-run spread already seen without the file. Sonnet's review got slightly worse and less repeatable; Haiku's got slightly better. The file also raises the cost of every call (Sonnet review cost per correct item 0.00728 to 0.00883).

Important caveat: `knowledge.example.md` is a generic template written before these runs (house terms, units, a few writing rules). It was **not** tuned to the answer keys, and it would be wrong to tune it to them. So this result says "a generic file does not help", not "a knowledge file cannot help". The file is meant for a real project's own terms, signal names and rules, which these public datasets do not have. The A/B option stays in the pack so a real project can measure its own file before relying on it.

## 4. Limits of these results

- Three repeats per task; ranges are indicative, not confidence intervals.
- The ICX-100 answer key is author-made and AI-reviewed, not engineer-reviewed. QuRE, PROMISE and RTEMS carry human labels.
- Local models (Ollama) were not run: Ollama is not installed on this machine, and installing it plus a model is a download of several GB that needs the owner's go-ahead.
- Scores describe these datasets, not general quality.
