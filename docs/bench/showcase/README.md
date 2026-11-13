# Showcase results

Machine-readable results of the five showcase benchmarks, for a website or any other display. The method, caveats and reading of every number are in the wiki: [Benchmarks](../../wiki/Benchmarks.md).

| File | What it holds | Rebuilt by |
|---|---|---|
| `showcase.json` | Everything below in one file | `python -m evals.showcase report` |
| `s1-planted.json` | S1 planted mistakes: per kind, planted, caught by the intended check, flagged by any check, an example, and false alarms on the clean originals | `python -m evals.showcase planted` |
| `s2-freetests.json` | S2 free-written tests vs the template path: per model run and per requirement, tests, tests that run, tests passing the correct simulation, faults caught, Zyn findings, cost; `fully_modelled` holds the seven-requirement comparison | `python -m evals.showcase freetests`, then `rescore` |

`showcase.json` keys:

| Key | Content |
|---|---|
| `s1_planted` | As `s1-planted.json` |
| `s2_freetests` | As `s2-freetests.json` |
| `s3_models` | The benchmark pack: task definitions and, per model and task, score mean, lowest, highest, item agreement and cost per correct item |
| `s4_real_dbc` | DBC checks on 58 opendbc files: files read, refused with reasons, findings by kind |
| `s5_qure` | QuRE quality flags: precision, recall and F1 per model and source (code, AI, both) |
| `label` | The caveat to show next to any number: scores describe the named datasets |

Rules for displaying these numbers:
- Show the dataset and method next to every number.
- ICX-100 results (S1 requirements and tests, S2, parts of S3) come from a synthetic example whose answer key was written by Claude and checked by an AI reviewer, not an engineer. Say so.
- No number here is a measure of time or effort saved.
