# Anvil Review

Checks tests from any tool against a CAN database and a requirement set. Code only: no model calls, same result every time.

**Input:** test files (pytest, CAPL, Robot Framework, or plain text), a CAN database (DBC, KCD, SYM or ARXML), and optionally the requirement set the tests refer to.
**Output:** findings to confirm or dismiss, coverage, and a confirmation checklist.

## Step 1: the CAN database is checked first

Every finding about a signal name or a range rests on the database, so a faulty database would make those findings wrong. The file is read leniently, so one fault does not stop the run:

| Check | What it catches |
|---|---|
| `duplicate_frame_id` | Two messages share a frame ID |
| `signal_overlap` | Signals in one message use the same bits (multiplexed signals that never appear together are allowed) |
| `outside_frame` | A signal's bits reach past the message length |
| `range_unreachable` | A minimum or maximum the signal's bits cannot carry |
| `range_inverted` | Minimum above maximum |
| `range_missing` | No range given (`[0|0]`); Zyn checks against the range the bits allow |
| `unknown_node` | A sender or receiver that is not a declared node |
| `invalid_length` | A length CAN or CAN FD does not allow |
| `bad_encoding` | A byte-order or sign code the common parser silently reads as Intel unsigned |
| `mux_undefined` | A multiplexed signal with no multiplexer; the parser silently drops the multiplexing |

An unreadable database, or one with no signals, is refused with the reason.

## Step 2: each test is checked

| Check | What it catches |
|---|---|
| `unknown_signal` | A name close to, but not, a DBC signal: a typo or an invented signal |
| `out_of_range` | A value outside the signal's DBC range |
| `value_not_traced` | An expected value that is not in the referenced requirement, nor a boundary next to one |
| `no_requirement` | The test cites no requirement ID |
| `unknown_requirement` | The test cites an ID the set does not have |
| `no_tolerance` | An exact equality on a scaled signal with no tolerance |
| `no_setup` | The test checks a signal but sets no input first |
| `no_check` | The test sets signals but checks none, so it can never fail |
| `duplicate_test` | The same code as an earlier test, apart from name, docstring and comments |
| `duplicate_name` | Two tests share a name |

Steps and checks are read from code only: a docstring line such as "Expected: TT_LowFuel = 1" is not a check.

## Step 3: coverage

Listed, not decided:

- requirements no test refers to
- input signals never set at their DBC minimum, maximum or a value inside
- tests that name no DBC signal, reported as **skipped, never passed**

Empty test files are refused.

## Checklist export

Exporting a run also writes `checklist.xlsx` in the layout of the public Automotive Engineering Suite (Title, Checklist, Findings, Dashboard, Signoff), rated FC, LC, PC or NO on the ISO/IEC 33020 scale. A check Zyn cannot decide is marked NA with the reason, never rated. A rating that rests on undecided findings is marked provisional. The mapping of their checks to Zyn's is in [docs/07-check-catalogue.md](../07-check-catalogue.md).

## Commands

```powershell
.\.venv\Scripts\zyn testcheck tests.py --dbc cluster.dbc --reqs requirements.csv
```

Code: [harness/outside.py](../../harness/outside.py), [harness/anvil/dbc_check.py](../../harness/anvil/dbc_check.py), [harness/checklist.py](../../harness/checklist.py)
