# Research basis

Zyn's direction comes from a qualitative study of what automotive and embedded engineers say about AI engineering tools, plus a survey of public datasets. Both are in [research/](../../research/).

## The practitioner study

Public sources from November 2024 to November 2026, every one opened and read: 41 sources in total, of which 23 community discussions are counted. Counts are threads that mention a theme, not percentages of engineers. Only four counted sources come from self-identified automotive practitioners, so the study shows which problems occur, not how often.

### What engineers ask for

| Rank | Capability | Sources of 23 |
|---|---|---|
| 1 | Review of existing work, and gap suggestions | 10 |
| 2 | Small, editable drafts of scripts, tests and documents | 9 |
| 3 | Grounded discovery of documents and code | 7 |
| 4 | Help with builds, failures and logs | 7 |
| 5 | Working inside existing ALM, model, IDE and CLI tools | 6 |
| 6 | Change impact and traceability upkeep | 4 |

### What makes them reject a tool

| Rank | Objection | Sources of 23 |
|---|---|---|
| 1 | Unreviewed output, loss of engineering control | 12 |
| 2 | Plausible false facts, requirements or logic | 9 |
| 3 | Correction and review cost eats the saving | 8 |
| 4 | Missing hardware or architecture context | 7 |
| 5 | Bloated, brittle or weak tests | 5 |
| 11 | Different output on repeated runs | 2 |

Sending protected material outside approved boundaries appears in only two sources, but where it applies it is a hard veto.

### Where the time goes

Inspecting and correcting candidate artifacts is the most reported cost (14 of 23). There is no defensible hours-by-task breakdown for automotive work in the public record.

## How Zyn answers it

| Finding | Zyn's response |
|---|---|
| Review existing work first | Sift Review and Anvil Review check work from any tool, not only Zyn's |
| Plausible false facts | Quotes are located by code; invented values, changed modal verbs and unknown signals are flagged |
| Review cost | One key per decision; decisions carry over; the decision record shows how often people agreed with each kind of finding |
| Weak tests | Anvil generates from checked templates and scores tests against injected faults |
| Repeatability | Benchmarks report agreement between repeats; accepted answers are stored and replayed, not regenerated |
| Private operation | Offline mode refuses cloud calls; local models through Ollama |
| No confidence badges | Concrete support states instead of model confidence |
| No borrowed productivity percentages | Zyn makes no productivity claim; it reports measured results with the method |

## What is deliberately not built

The study found no firsthand demand or successful deployment for: autonomous TARA, automatic CVE disposition, AI as a MISRA compliance authority, RFQ-to-quotation automation, or autonomous approval of safety requirements. Zyn does none of these.

## The data survey

41 public datasets and repositories were checked for licence, ground truth and fit. Zyn uses the ones whose licences allow it: see [Data and licences](Data-and-licences.md). There is no public end-to-end automotive chain from requirements to tests to results to defects; that gap is why the ICX-100 example is synthetic.
