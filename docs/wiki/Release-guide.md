# Release Guide

This document describes how to test, build, and publish clean release snapshots of Zyn.

## Versioning Scheme

Zyn uses Semantic Versioning (`MAJOR.MINOR.PATCH`).
The version is declared in `pyproject.toml` under `[project].version` and must match `harness.__version__`.

## Release Prerequisites

Before preparing a release snapshot:
1. Verify all unit and integration tests pass with PostgreSQL (`ZYN_TEST_PG_URL` set) using the development extra:
   ```bash
   pip install --upgrade pip "setuptools>=77"
   pip install -e ".[dev]"
   pytest -q
   ```
2. Verify code quality and styling:
   ```bash
   ruff check harness/ tests/ evals/
   ```
3. Verify the review screen web UI and site build and tests pass (Node 22 LTS):
   ```bash
   npm --prefix web run build
   npm --prefix web test -- --run
   npm --prefix site run build
   ```
4. Verify the trial compose verification script on a Docker host:
   ```bash
   ./scripts/verify-trial-docker.sh
   ```

## Publishing a Release Snapshot

GitHub receives clean repository snapshots only. Never run `git push` from the working repository.

1. Ensure the working tree is clean and `pyproject.toml` version matches `harness.__version__`.
2. Clone the public destination repository into a separate folder:
   ```bash
   git clone git@github.com:tomxander/zyn.git /tmp/zyn-clean
   ```
3. In the clean clone, remove existing files to keep deleted files in sync, then extract a clean snapshot of `HEAD`:
   ```bash
   cd /tmp/zyn-clean
   git rm -rq --ignore-unmatch .
   cd -
   git archive HEAD | tar -x -C /tmp/zyn-clean
   ```
4. In the clean clone, commit the snapshot and create an annotated release tag:
   ```bash
   cd /tmp/zyn-clean
   git add -A
   git commit -m "Release v0.2.0"
   git tag -a v0.2.0 -m "Release v0.2.0"
   ```
5. Push the commit and tag from the clean clone:
   ```bash
   git push origin main
   git push origin v0.2.0
   ```
6. GitHub Actions (`.github/workflows/release.yml`) will automatically:
   - Verify the git tag matches `pyproject.toml`.
   - Run the full test suite against PostgreSQL with `.[dev]`.
   - Build the frontend web bundle into `web/dist`.
   - Verify `web/dist/index.html` exists.
   - Package the Python wheel `zyn_harness-<version>-py3-none-any.whl`.
   - Publish a GitHub Release with the wheel attached.

## Local Wheel Build

To build the standalone wheel locally:
- **Windows (PowerShell):**
  ```powershell
  .\scripts\build-release.ps1
  ```
- **Linux / macOS:**
  ```bash
  npm --prefix web run build
  python -m pip install --upgrade pip "setuptools>=77"
  python -m pip wheel . --no-deps --no-build-isolation -w dist
  ```
