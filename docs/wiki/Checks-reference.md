# Checks reference

Every code check in Zyn, what it catches, and where it stops. Code checks are deterministic: the same input always gives the same findings. A finding is a question for a person, not a verdict.

The catch rates below are from the planted-mistakes benchmark ([Benchmarks](Benchmarks.md), S1).

## Requirements against their source

Used by Sift and by Sift Review with a source document. Each requirement is matched to the source sentence that contains the largest share of its words.

| Check | Fires when | Where it stops |
|---|---|---|
| `ungrounded` | No source sentence contains at least half of the requirement's words | A requirement merged from several places can look ungrounded |
| `invented_value` | A number is in neither the matching sentence nor its section, or the matching sentence has its own numbers and this one is not among them | A changed number that also appears in the same source sentence is accepted |
| `modal_changed` | The modal verb differs from the source's ("should" made "shall") | A table row has no modal verb, so there is nothing to compare |

What no code check catches: a term swapped for another valid term from the same document, such as one status code for another. That needs the AI reviewer or a person.

## Requirement quality

Used by Sift Review on any set, configurable per [rule profile](../../rules/).

| Check | Fires when |
|---|---|
| `weak_word` | A vague word such as "appropriate", "fast", "user-friendly", "normal". Technical standards and defined phrases are allowed in context (e.g. "as required by ISO 26262", "Fast Ethernet", "fast charging", "CAN flexible data-rate") while vague phrasing ("as required by the driver", "normal range", "normal voltage") is flagged |
| `placeholder` | TBD, TBC, TBA, XXX, ?? or an angle-bracket placeholder |
| `no_modal` | No shall, must, will, should or may |
| `not_atomic` | More than one modal verb: possibly several obligations in one |
| `duplicate_id`, `duplicate_text` | Repeated IDs or text |
| `not_ears` | Optional: the sentence does not follow an EARS pattern |

## Tests

Used by Anvil Review. Steps and checks are read from the test's code, never from its docstring or comments. Compatible with pytest, CANoe CAPL, Robot Framework, and Vector vTESTstudio XML (`.vtt`, `.vts`, `.vxt`).

| Check | Fires when |
|---|---|
| `unknown_signal` | A name is close to a DBC signal or message but is not one |
| `out_of_range` | A value is outside the signal's DBC range |
| `value_not_traced` | An expected value is in neither the referenced requirement nor next to one of its values |
| `no_requirement`, `unknown_requirement` | No requirement ID, or one the set lacks |
| `no_tolerance` | Exact equality on a scaled signal (resolution below 1) with no tolerance |
| `no_setup` | A check on a signal with no input or message set first |
| `no_check` | Signals are set but nothing is checked |
| `duplicate_test`, `duplicate_name` | The same code under another name, or the same name twice |

What no code check catches: a flipped expectation (1 where 0 is right) that stays inside the signal's range and the requirement's values. The fault-kill score on a simulation catches that for Anvil's own tests.

## CAN databases

Run before Anvil Review trusts the file. See [Anvil Review](Anvil-Review.md) for the full table: `duplicate_frame_id`, `signal_overlap`, `outside_frame`, `range_unreachable`, `range_inverted`, `range_missing`, `unknown_node`, `invalid_length`, `bad_encoding`, `mux_undefined`, as well as commercial vehicle protocol checks for SAE J1939: `j1939_edp_reserved`, `j1939_global_source`, and `j1939_dlc_exceeded` (lengths between 9 and 1785 bytes are accepted as declared multi-packet Transport Protocol messages because standard DBC files omit single-frame markers).

## Generated test specs

Used by Anvil before a person approves a spec: every parameter must quote words from the requirement, signals must exist in the DBC with the right direction, values must fit their range, and the formal set check looks for contradictions between specs.

## No silent pass

Every checker, given empty or junk input, refuses it or says it checked nothing. It never comes back looking clean. `tests/test_no_silent_pass.py` holds Zyn to this.
