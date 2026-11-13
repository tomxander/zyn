# Getting started

Zyn runs locally on Windows. The Python API and the React review screen run on the same machine. Commands below are for PowerShell, from the project folder.

## What you need

- Python 3.11 (the project uses a virtual environment in `.venv`)
- Node.js, to build the review screen the first time
- An Anthropic API key for Claude models, or Ollama for local models (or both)

## 1. Install

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## 2. Add your key

Creates `.env` and opens it in Notepad. Paste the key after `ANTHROPIC_API_KEY=`, save, close. `.env` is ignored by Git.

```powershell
Copy-Item .env.example .env; notepad .env
```

## 3. Check what is ready

Lists every model profile in `config.yaml` and whether it can be reached.

```powershell
.\.venv\Scripts\python -m harness profiles
```

## 4. Run the smoke test

Two model calls (generate, then AI review) on a five-sentence synthetic fuel-gauge specification. Costs well under USD 0.50.

```powershell
.\.venv\Scripts\python -m harness smoke
```

## 5. Open the review screen

The first run builds the screen. Enter your name under Reviewer, then approve or reject. Until you enter a name, the screen is read-only.

```powershell
.\review.ps1
```

## Try the checkers without any model

Anvil Review and the DBC checks run on code only, so they need no key:

```powershell
.\.venv\Scripts\python -m harness testcheck my_tests.py --dbc data\synthetic\icx100.dbc --reqs data\synthetic\icx100_reqset.csv
```

## Local models

1. Install Ollama: `winget install Ollama.Ollama`
2. Pull a model (about 9 GB): `ollama pull qwen3:14b`
3. Generate locally and review with Claude:
   ```powershell
   .\.venv\Scripts\python -m harness smoke --generator local-qwen3-14b --reviewer claude-opus
   ```

Set `offline: true` in `config.yaml` (or `ZYN_OFFLINE=1`) to make every cloud call fail before it is sent. Stored answers can still be replayed offline, because nothing leaves the machine.

## Configuration

`config.yaml` holds the model switch. Two roles, `generator` and `reviewer`, point at profiles. Change a role to swap models everywhere. Each profile records its price per million tokens, used only to estimate cost in reports.

| Setting | What it does |
|---|---|
| `roles.generator`, `roles.reviewer` | Which profile writes, which one reviews |
| `max_attempts` | Schema retries before a call is recorded as failed (default 3) |
| `offline` | Refuse every cloud model |
| `replay` | Reuse a stored answer when the same model saw the same prompt and input |
| `knowledge_file` | House rules, terms and units added to every call (copy `knowledge.example.md`) |
