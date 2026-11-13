# Assay

Benchmarks: models scored on public and synthetic answer keys, with run-to-run stability and cost. Results are on the [Benchmarks](Benchmarks.md) page.

## The benchmark pack

Version `zyn-bench-1.1`. Six tasks, every data file pinned by sha256.

| Task | Data | Score |
|---|---|---|
| ICX-100 section mapping | Synthetic cluster spec | Accuracy |
| ICX-100 requirement review | 46 synthetic requirements | Recall of expected flags |
| QuRE defect flags | 200 industrial automotive requirements, human labels | F1 on defect-labelled weak words |
| PROMISE requirement type | 625 requirements, human labels | Functional vs non-functional accuracy |
| RTEMS extraction | Public RTOS behaviour sections | Recall of "shall" statements |
| RTEMS whole components (1.1) | Same, with conditions that must not be extracted | F1 |

For each model and task the pack reports, over N repeats, the mean, lowest and highest score, item-level agreement between repeats, and cost per correct item. Every repeat asks the model again with the published prompts; no stored answer is reused.

```powershell
.\.venv\Scripts\python -m harness pack run --profiles claude-sonnet,claude-haiku --repeat 3
.\.venv\Scripts\python -m harness pack manifest
.\.venv\Scripts\python -m harness pack export
```

`pack export` writes the tasks as Inspect AI JSONL and promptfoo CSV, so other harnesses can run them. `--knowledge FILE` adds a knowledge file to every call, to measure what it changes.

## Showcase benchmarks

Built from the practitioner research, to answer the questions engineers ask before they trust a tool:

```powershell
.\.venv\Scripts\python -m evals.showcase planted
.\.venv\Scripts\python -m evals.showcase freetests --profiles claude-haiku,claude-sonnet,claude-opus --repeat 2
```

## Public evaluations

```powershell
.\.venv\Scripts\python -m evals.qure run
.\.venv\Scripts\python -m evals.promise
.\.venv\Scripts\python -m evals.rtems fetch
.\.venv\Scripts\python -m evals.rtems run
.\.venv\Scripts\python -m evals.opendbc fetch
.\.venv\Scripts\python -m evals.opendbc run
```

Each module's docstring says where to download its data and under which licence.

Code: [harness/pack.py](../../harness/pack.py), [evals/](../../evals/)
