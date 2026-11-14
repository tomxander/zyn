# Integrations

Zyn fits around existing tools rather than replacing them.

## Requirements tools: ReqIF round-trip

A Sift Review export writes `reviewed.reqif`. If the set came in as ReqIF and the original file is unchanged, the export is that file with two attributes added to each requirement:

- **Zyn review**: pass, fail, warn or broken
- **Zyn findings**: each finding, its state and who decided

Identifiers, types, hierarchy and other attributes are kept, so DOORS Next, Polarion or Codebeamer can import it as an update. Reviewing a reviewed file replaces the two attributes instead of adding more. Every export is read back to confirm no requirement or text was lost.

## Test benches

Anvil writes:

- a linted pytest module, with a simulated bench so the tests can run here
- a Robot Framework suite, with a keyword file that fails until you map it to your bench
- a CANoe CAPL test module (stopping a message and measuring a period call functions you implement)
- a flat step table (CSV) for tools that import tabular steps

Native ecu.test packages are not written: the format is proprietary and could not be checked.

## Agents: MCP server

`zyn mcp` serves Zyn's code checks as tools, so an agent that writes requirements or tests can have Zyn check them inside its own loop.

| Tool | What it checks |
|---|---|
| `check_requirements` | Quality checks, and grounding against an optional source document |
| `check_tests` | Anvil Review on test code, including the DBC checks |
| `check_quote` | Whether a quote is really in a document |
| `validate_test_spec` | An Anvil spec against its requirement and the DBC |
| `check_specs` | The formal set check |
| `list_rule_profiles` | Available rule profiles |
| `fault_score` | The fault-kill score |

Code only: no model calls, no runs started, nothing written to the audit log.

```bash
claude mcp add zyn -- zyn mcp
```

## CI and assessors: evidence report

`zyn evidence report <run> --as NAME` writes:

- `evidence.html`: one verdict per item with its source quote, checks, AI advice and the decision. Prints to PDF.
- JUnit XML, for CI dashboards
- the run's audit log as a hash chain; `zyn evidence verify <audit_chain.json>` checks it

The report lists the ASPICE processes the record may support, as a pointer for an assessor, not an assessment.

## Checklists

Anvil Review exports a confirmation checklist in the layout of the public Automotive Engineering Suite (FC, LC, PC, NO, NA), so people using that suite can put Zyn in as the reviewer. See [Anvil Review](Anvil-Review.md).
