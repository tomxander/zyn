# Roadmap

## Next

- **Model connectors.** Built, not tried against live endpoints. An admin points Zyn at AWS Bedrock, Google Vertex, Azure or an OpenAI-style endpoint such as vLLM by configuration, and can forbid anything else.
- **Daily-workflow fit.** A requirement set and its review state go round trip with a requirement tool; a new spec revision lands in Sift Delta; test reviews cover CANoe CAPL and vTESTstudio. J1939 checks for commercial vehicles and vTESTstudio reviews are first checks built, tried on synthetic files only (no public J1939 DBC or real vTESTstudio file was available), not done.
- **Trust pack.** An engineer-reviewed answer key, a tool-qualification kit (intended use, limits, evidence) and a security pack (architecture, data flows, questionnaire answers, software bill of materials).
- **Local model comparison.** The research found no published comparison of local and hosted models on automotive tasks. The pack is ready to run on Ollama models; it needs a machine with them installed.
- **Engineer-reviewed answer key.** Every ICX-100 score carries the "author-made, AI-reviewed" caveat until an engineer reviews the key.
- **AI reviewer for tests.** Error and edge-case coverage (TC021 in the check catalogue) needs a reviewer that quotes the test; code cannot decide it.
- **Swapped terms.** A status code or signal swapped for another valid one passes every code check. A term-level comparison against the matched source sentence is the next code check to try.
- **Diagnostics.** A UDS and DTC catalogue checked against its ODX or CDD description follows the Anvil Review pattern: a machine-readable reference to check against.

## Done

- **Team server.** Company sign-in (OpenID Connect), roles per project, walls between projects, the four-eyes rule, a shared append-only PostgreSQL audit log, access tokens for CI and test benches (`zyn remote`), and a container package ([Team server](Team-server.md)). The container runs end to end with a trial Keycloak sign-in on every change; not yet run at a company.
- **Light install.** One wheel, the `zyn` command and `zyn demo`; no Node.js needed.

## Later

- ALM connectors chosen by actual use (DOORS Next, Polarion, Codebeamer, Jama)
- Coverage measurement on real code
- Scribe (documents)

## Not building

The research found no firsthand demand or successful deployment for these, and each would ask a model to make a decision that belongs to an engineer:

- autonomous TARA or safety analysis
- MISRA compliance verdicts from a model
- automatic baselining or approval of safety requirements
- RFQ-to-quotation automation (Source is parked)
- productivity percentages
