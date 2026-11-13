# Zyn benchmark pack zyn-bench-1.0, 2026-11-13T21:42:23

Zyn prototype. 3 repeats per model and task. every repeat asks the model again (no replay); published prompts only (no project knowledge file); cost from the prices in config.yaml; scores describe these datasets, not general quality.

| Model | Task | Score (mean) | Lowest | Highest | Item agreement | Cost per correct item (USD) | Errors |
|---|---|---|---|---|---|---|---|
| claude-sonnet | ICX-100 section mapping | 1.0 | 1.0 | 1.0 | 1.0 | 0.00107 | 0 |
| claude-sonnet | ICX-100 requirement review | 0.647 | 0.647 | 0.647 | 0.6 | 0.00728 | 0 |
| claude-sonnet | QuRE defect flags | 0.547 | 0.54 | 0.553 | - | 0.00691 | 0 |
| claude-sonnet | PROMISE requirement type | 0.886 | 0.885 | 0.888 | - | 0.00034 | 0 |
| claude-sonnet | RTEMS requirement extraction | 1.0 | 1.0 | 1.0 | - | 0.00179 | 0 |
| claude-haiku | ICX-100 section mapping | 1.0 | 1.0 | 1.0 | 1.0 | 6e-05 | 0 |
| claude-haiku | ICX-100 requirement review | 0.49 | 0.412 | 0.588 | 0.44 | 0.00063 | 0 |
| claude-haiku | QuRE defect flags | 0.557 | 0.542 | 0.571 | - | 0.00044 | 0 |
| claude-haiku | PROMISE requirement type | 0.881 | 0.878 | 0.883 | - | 3e-05 | 0 |
| claude-haiku | RTEMS requirement extraction | 1.0 | 1.0 | 1.0 | - | 0.00012 | 0 |

## Tasks

- **ICX-100 section mapping** (icx-map): Map each section of a synthetic cluster spec to a subsystem. Score: accuracy: sections mapped to an accepted subsystem / sections. Author-made, AI-reviewed, not engineer-reviewed.
- **ICX-100 requirement review** (icx-review): Flag quality problems in 46 requirements (Sift Review, code and AI). Score: recall: expected flags found / expected flags; flags not in the key reported. Author-made, AI-reviewed, not engineer-reviewed.
- **QuRE defect flags** (qure-flags): 200 industrial automotive requirements: find weak words humans labelled as defects. Score: F1 on defect-labelled weak words. QuRE 1.0.1 (Zenodo 16049822, CC BY 4.0); human labels.
- **PROMISE requirement type** (promise-type): 625 requirements: functional or non-functional, and the coarse class. Score: binary accuracy (functional vs non-functional). PROMISE NFR dataset; human labels.
- **RTEMS requirement extraction** (rtems-extract): Extract 'shall' statements from RTEMS behaviour sections with verbatim quotes. Score: recall: gold statements matched / gold statements. Rendered from RTEMS rtems-central spec files (BSD-2-Clause / CC BY-SA).

## Data files (sha256)

- `synthetic/icx100_srs.md`: 60aa2e28f611e91c3426cc89b26aebb3ad97dbdf397e99f1bf7562712f808cf5
- `synthetic/icx100_answer_key.json`: ff91ca215eab48a0bf090ecccd1fae8e53ac4132b6769672b461abf2d1e1688d
- `synthetic/icx100_reqset.csv`: 6833c2acdb16d11b036a7575494b545a29a4505c93af8edc7ffaa24d4ace692f
- `synthetic/icx100_answer_key.json`: ff91ca215eab48a0bf090ecccd1fae8e53ac4132b6769672b461abf2d1e1688d
- `public/qure/sample_200_42.csv`: 91259b8f1439808d862c1b5cc057ba437783b29e01dc1c0f20ec3d17c8129573
- `public/qure/sample_200_42.gold.json`: 7d825ae165bae13038dbe6d553107c9034e37de1f879aad6bd26dd3edfdf6749
- `public/promise/nfr.arff`: 3d93f83641b76553ddce828c3f80e8c2b70269e51044046ec08b931383dc6c15
- `public/rtems/rendered.md`: 1002fd18313322c3cf8740f5ad1bb743d2dd79b2f291b2579237fae26dfed23f

## Reading the results (13 November 2026)

Total cost USD 3.01 (Sonnet 2.84, Haiku 0.18) for 30 task runs.

- **Haiku matches Sonnet where the task is narrow.** QuRE defect F1 (0.557 vs 0.547), PROMISE type accuracy (0.881 vs 0.886), section mapping and RTEMS extraction (both perfect) are within noise, at about one fifteenth of the cost per correct item.
- **Review is where the bigger model earns its cost.** On the ICX-100 review Sonnet found 11 of 17 expected flags in every repeat (0.647); Haiku found 7 to 10 (0.412 to 0.588).
- **The same score is not the same answer.** Sonnet's ICX-100 review score was identical in all three repeats, yet only 60 percent of its individual findings recurred between repeats (Haiku 44 percent). This is why Zyn keeps human decisions persistent and shows how many passes reported each finding.
- **RTEMS extraction is saturated** for both models (every gold statement found); it no longer separates models and needs harder material, such as whole components where conditions must not be extracted.

Caveats: the ICX-100 tasks use an author-made, AI-reviewed answer key; QuRE, PROMISE and RTEMS carry human labels. Three repeats per task; the spread is indicative, not a confidence interval. Opus and local models were not run.
