# Sift Delta

What changed between two revisions, and which approved requirements it affects. Code only, no model calls.

## Two modes

**A specification against its new revision.** For each approved requirement from a Sift run, its source quote is looked up in the new revision:

- unchanged
- moved
- changed, with a word diff and the values or modal verb that changed
- removed

New sentences with a modal verb are listed for extraction.

**Two exports of a requirement set,** matched by ID.

A named person marks each entry "needs action" or "no action". Export to JSON and Excel.

## Commands

```powershell
.\.venv\Scripts\python -m harness delta spec <sift run> data\synthetic\icx100_srs_rev2.md
.\.venv\Scripts\python -m harness delta set old.csv new.csv
```

Code: [harness/sift/delta.py](../../harness/sift/delta.py)
