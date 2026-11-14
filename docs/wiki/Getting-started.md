# Getting started

Zyn runs on your own machine: Windows, macOS or Linux. The checks and the review screen run locally; nothing leaves the machine unless you turn on a cloud model.

## What you need

- Python 3.11 or later (tested on 3.11)
- [pipx](https://pipx.pypa.io), which installs command-line tools in their own space: `python -m pip install --user pipx`, then `python -m pipx ensurepath` and open a new terminal
- For the AI steps only: an Anthropic API key, or Ollama for local models

No Node.js and no key are needed for the code checks or the review screen.

## 1. Install

Download the `.whl` file from the latest [release](https://github.com/tomxander/zyn/releases), then from the folder it is in:

```bash
pipx install ./zyn_harness-0.2.0-py3-none-any.whl
```

About a minute and 100 MB. This is the light install: every code check, the review screen, the MCP server and both model providers.

No wheel to hand? Build from the source instead. This needs Node.js 20 or later once, to build the review screen:

```bash
git clone https://github.com/tomxander/zyn.git
cd zyn
npm --prefix web ci
npm --prefix web run build
pipx install .
```

No pipx? A virtual environment works too:

```bash
python -m venv zyn-env
zyn-env/bin/pip install ./zyn_harness-0.2.0-py3-none-any.whl      # macOS, Linux
zyn-env\Scripts\pip install .\zyn_harness-0.2.0-py3-none-any.whl  # Windows
```

## 2. See it work

```bash
zyn demo
```

Checks the sample requirement set (ICX-100, a synthetic instrument cluster) against its specification by code alone, then opens the review screen. Enter your name under Reviewer to confirm or dismiss findings; until you do, the screen is read-only. Ctrl+C stops it.

## 3. Your Zyn folder

The first run creates a folder called `zyn` in your home directory with the config, rule profiles, sample data, the audit log and exports. `zyn where` shows it. Set `ZYN_HOME` to use a different folder, for example one per project.

## 4. Check your own work, no key needed

```bash
zyn check start my_requirements.csv --source my_spec.md     # requirement set vs its specification
zyn testcheck my_tests.py --dbc my_network.dbc --reqs my_requirements.csv
zyn serve                                                   # review the findings
```

Requirement sets can be CSV, Excel or ReqIF. Specifications can be Markdown or text in the light install.

## 5. Add the AI steps (optional)

Put your key in the `.env` file in your Zyn folder (copy `.env.example`):

```
ANTHROPIC_API_KEY=your key here
```

Then check what is ready and run the smoke test (two model calls, well under USD 0.50):

```bash
zyn profiles
zyn smoke
```

## PDF and Word specifications (optional)

Reading `.pdf` and `.docx` needs the document reader, which adds a large machine-learning stack (several GB):

```bash
pipx inject zyn-harness docling
```

## Local models

1. Install [Ollama](https://ollama.com) (Windows: `winget install Ollama.Ollama`)
2. Pull a model (about 9 GB): `ollama pull qwen3:14b`
3. Generate locally and review with Claude: `zyn smoke --generator local-qwen3-14b --reviewer claude-sonnet`

Set `offline: true` in `config.yaml` (or `ZYN_OFFLINE=1`) to make every cloud call fail before it is sent. Stored answers can still be replayed offline, because nothing leaves the machine.

## Configuration

`config.yaml` in your Zyn folder holds the model switch. Two roles, `generator` and `reviewer`, point at profiles; both start on `claude-sonnet`, which matched Opus on review at under half the cost per correct finding ([Benchmarks](Benchmarks.md)). Change a role to swap models everywhere. Each profile records its price per million tokens, used only to estimate cost in reports.

| Setting | What it does |
|---|---|
| `roles.generator`, `roles.reviewer` | Which profile writes, which one reviews |
| `max_attempts` | Schema retries before a call is recorded as failed (default 3) |
| `offline` | Refuse every cloud model |
| `replay` | Reuse a stored answer when the same model saw the same prompt and input |
| `knowledge_file` | House rules, terms and units added to every call (copy `knowledge.example.md`) |

## From source

To work on Zyn itself (Windows, PowerShell, inside a clone):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\review.ps1        # builds the screen on first run (needs Node.js), then opens it
```

A clone is its own Zyn folder. To make a release wheel: `.\scripts\build-release.ps1`. More in [Development](Development.md).
