# Sift Review

Checks an existing requirement set, from Zyn or any other tool, and keeps its IDs.

**Input:** a requirement set as ReqIF, Excel or CSV. Optionally, the source specification it was drawn from.
**Output:** findings, each confirmed or dismissed by a named person, as JSON, Excel and ReqIF.

## Checks

**Code checks** (always run, configurable through [rule profiles](../../rules/)):

- vague words (weak words), with a per-profile allow list
- placeholders such as TBD
- missing modal verb
- several obligations in one requirement
- duplicate IDs and duplicate text
- optional EARS pattern check

**With a source document**, each requirement is matched to the source sentence it came from (a quote column from the other tool is used if present), and code flags:

- `ungrounded`: no source sentence matches
- `invented_value`: a number the matching sentence or its section never gives, or a number taken from a neighbouring sentence
- `modal_changed`: "should" became "shall", or the reverse

**The AI reviewer** reviews in batches. Every finding must quote words that code confirms are in the requirement. It asks the author a question instead of rewriting.

## Decisions that last

- A named person confirms or dismisses each finding, with a reason.
- Decisions on unchanged text carry over to later runs with one click.
- Each finding card shows how people decided earlier findings of the same kind, from the audit log, never from model confidence.

## Exports

- JSON and Excel with every finding, its status and who decided
- `reviewed.reqif`: if the set came in as ReqIF, it is the original file with two attributes added per requirement, "Zyn review" and "Zyn findings". Identifiers, types and hierarchy are kept, so DOORS Next, Polarion or Codebeamer can import it as an update. Every export is read back to confirm nothing was lost.

## Scoring

`check score <run>` scores the findings against an answer key keyed by requirement ID. A key that names no requirement in the run is refused, never scored as zero.

## Commands

```powershell
.\.venv\Scripts\python -m harness check start set.csv --source spec.md --rules default
.\.venv\Scripts\python -m harness check ai <run>
.\.venv\Scripts\python -m harness check export <run> --as NAME
.\.venv\Scripts\python -m harness check score <run>
```

Code: [harness/sift/check.py](../../harness/sift/check.py), [harness/outside.py](../../harness/outside.py)
