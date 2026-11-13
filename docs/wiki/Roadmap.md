# Roadmap

## Next

- **Local model comparison.** The research found no published comparison of local and hosted models on automotive tasks. The pack is ready to run on Ollama models; it needs a machine with them installed.
- **Engineer-reviewed answer key.** Every ICX-100 score carries the "author-made, AI-reviewed" caveat until an engineer reviews the key.
- **AI reviewer for tests.** Error and edge-case coverage (TC021 in the check catalogue) needs a reviewer that quotes the test; code cannot decide it.
- **Swapped terms.** A status code or signal swapped for another valid one passes every code check. A term-level comparison against the matched source sentence is the next code check to try.
- **Diagnostics.** A UDS and DTC catalogue checked against its ODX or CDD description follows the Anvil Review pattern: a machine-readable reference to check against.

## Later

- ALM connectors chosen by actual use (DOORS Next, Polarion, Codebeamer, Jama)
- Multi-user review with roles
- Coverage measurement on real code
- Scribe (documents)

## Not building

The research found no firsthand demand or successful deployment for these, and each would ask a model to make a decision that belongs to an engineer:

- autonomous TARA or safety analysis
- MISRA compliance verdicts from a model
- automatic baselining or approval of safety requirements
- RFQ-to-quotation automation (Source is parked)
- productivity percentages
