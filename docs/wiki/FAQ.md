# FAQ

**Does Zyn generate requirements and tests?**
Yes, but that is not the point. Sift extracts requirements and Anvil builds tests from checked templates. The core of Zyn is checking: the same checks run on work from any tool.

**Can the AI reviewer approve anything?**
No. The audit store refuses an approval from any actor that is not a named person. The reviewer's verdict is shown as advice.

**Why no confidence scores?**
The research found no evidence that a model's self-reported confidence predicts correctness, and engineers asked for evidence they can check. Zyn shows concrete support states instead: quote located, values from the source only, modal verb kept.

**Does anything leave my machine?**
Only model calls to a cloud profile. With `offline: true`, every cloud call fails before it is sent and only local models run. The checkers (Anvil Review, the DBC checks, the MCP server) never call a model. Zyn sends nothing to its makers: no telemetry, no update checks.

**Can a whole team use it?**
Yes. Team mode runs on a server in your network or cloud account, with company sign-in, roles per project, a shared PostgreSQL audit log and the four-eyes rule on by default. See [Team server](Team-server.md).

**Will the same input give the same answer?**
Code checks: always. Models: not always, and Zyn measures it (see item agreement on the [Benchmarks](Benchmarks.md) page). Accepted answers are stored and can be replayed exactly; decisions persist across runs of the same text.

**How good are the scores?**
They describe named datasets, with the method beside every number. QuRE, PROMISE, RTEMS and opendbc are public. ICX-100 is synthetic with an AI-reviewed answer key. None of it is a productivity measure.

**Which models are supported?**
Claude through the Anthropic SDK, and local models that Ollama serves. Swap them by changing a role in `config.yaml`.

**Is this a qualified tool under ISO 26262?**
No. [docs/06-tool-confidence.md](../06-tool-confidence.md) is a draft tool confidence argument, not reviewed by a functional safety engineer.
