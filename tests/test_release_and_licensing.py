from __future__ import annotations

import tomllib

import pytest
import yaml

from harness.config import PROJECT_ROOT


def test_dockerfile_node22_and_licenses():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "node:22-slim" in dockerfile, "Dockerfile must use Node 22 LTS"
    assert "LICENSE" in dockerfile, "Dockerfile must copy LICENSE"
    assert "THIRD_PARTY_NOTICES.md" in dockerfile, "Dockerfile must copy THIRD_PARTY_NOTICES.md"


def test_release_workflow_spec():
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    assert workflow_path.is_file()
    text = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)

    # Job level permissions (contents: write for release job)
    assert "permissions" not in data or data["permissions"] is None, "Workflow root must not have blanket permissions"
    job = data["jobs"]["build-and-release"]
    assert job["permissions"]["contents"] == "write"

    # Node 22 LTS
    assert 'node-version: "22"' in text

    # Postgres service container configured with 5432 and ZYN_TEST_PG_URL
    assert "postgres:16-alpine" in text
    assert "5432:5432" in text
    assert "ZYN_TEST_PG_URL" in text

    # Installs .[dev] and lints evals/
    assert 'pip install -e ".[dev]"' in text
    assert "ruff check harness/ tests/ evals/" in text

    # Pin action-gh-release to real SHA of release tag v2.0.8 (J3)
    assert "softprops/action-gh-release@c062e08bd532815e2082a85e87e3ef29c3e6d191" in text
    assert "# v2.0.8" in text
    assert "c062e49c" not in text

    # Verifies tag matches version and web/dist exists
    assert "Verify Tag Matches pyproject.toml Version" in text
    assert "Verify Web UI Build Output" in text
    assert "web/dist" in text

    # persist-credentials: false
    assert "persist-credentials: false" in text


def test_docker_trial_workflow_spec():
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "docker-trial.yml"
    assert workflow_path.is_file()
    text = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)

    # permissions: contents: read
    assert data["permissions"]["contents"] == "read"

    # path filter includes the workflow file itself
    on_trigger = data.get("on") or data.get(True)
    assert ".github/workflows/docker-trial.yml" in on_trigger["pull_request"]["paths"]

    # persist-credentials: false
    assert "persist-credentials: false" in text


def test_verify_trial_docker_script_spec():
    script_path = PROJECT_ROOT / "scripts" / "verify-trial-docker.sh"
    assert script_path.is_file()
    text = script_path.read_text(encoding="utf-8")

    # Uses project namespace to avoid wiping real trial
    assert 'PROJECT_NAME="zyn-verify-$$"' in text
    assert '-p "${PROJECT_NAME}"' in text
    assert 'cd "$(dirname "$0")/.."' in text

    # Proper health check grep
    assert 'grep -q "(healthy)"' in text

    # Checks upgrade has exited with code 0
    assert "status=exited" in text
    assert "ExitCode" in text

    # Interactive OIDC PKCE flow with mktemp cookies and project bcm/approver verification (J5)
    assert "alice" in text
    assert "alice123" in text
    assert "COOKIE_FILE=$(mktemp)" in text
    assert "/auth/callback" in text
    assert "/api/config" in text
    assert r'\"bcm\"' in text
    assert r'\"approver\"' in text


def test_pyproject_licensing_and_build_requires():
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data["project"]
    assert project.get("license") == "LicenseRef-Proprietary"
    assert "Private :: Do Not Upload" in project.get("classifiers", [])
    assert "LICENSE" in project.get("license-files", [])
    assert "THIRD_PARTY_NOTICES.md" in project.get("license-files", [])

    build_requires = data["build-system"]["requires"]
    assert any("setuptools>=77" in r for r in build_requires)


def test_license_and_third_party_notices():
    import json

    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "PRIVACY GUARANTEE" not in license_text
    assert "THIRD_PARTY_NOTICES.md" in license_text
    assert "Zyn sends nothing to its makers" in license_text
    assert "\u2014" not in license_text

    notices_path = PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices_path.is_file()
    notices_text = notices_path.read_text(encoding="utf-8")
    assert "SIL Open Font License" in notices_text
    assert "IBM Plex Mono" in notices_text
    assert "Space Grotesk" in notices_text
    assert "D-DIN" in notices_text
    assert "Reserved Font Name: Plex" in notices_text
    assert "Reserved Font Name: IBM Plex Mono" not in notices_text
    assert "fonts do not ship in the Python wheel" in notices_text
    assert "tslib" in notices_text
    assert "0BSD" in notices_text
    assert "react" in notices_text
    assert "radix-ui" in notices_text
    assert "\u2014" not in notices_text

    # Every production package in web/package-lock.json must be listed (J6)
    lock_data = json.loads((PROJECT_ROOT / "web" / "package-lock.json").read_text(encoding="utf-8"))
    prod_pkgs = [
        k.replace("node_modules/", "")
        for k, v in lock_data.get("packages", {}).items()
        if k and not v.get("dev") and not v.get("devOptional")
    ]
    for pkg in prod_pkgs:
        assert pkg in notices_text, f"Production package {pkg} missing from THIRD_PARTY_NOTICES.md"


def test_release_guide_clean_publishing():
    guide_text = (PROJECT_ROOT / "docs" / "wiki" / "Release-guide.md").read_text(encoding="utf-8")
    assert "git archive HEAD" in guide_text
    assert "git rm -rq --ignore-unmatch ." in guide_text
    assert "Never run `git push` from the working repository" in guide_text
    assert "Node 22 LTS" in guide_text
    assert ".[dev]" in guide_text
    assert "\u2014" not in guide_text


def test_site_docs_loader_excludes_unlisted_wiki_pages():
    docs_ts = (PROJECT_ROOT / "site" / "src" / "docs" / "docs.ts").read_text(encoding="utf-8")
    # Only loads listed files
    assert "Release-guide.md" not in docs_ts
    assert "_Sidebar.md" not in docs_ts
    assert 'file: "Getting-started"' in docs_ts


def test_remaining_copy_updates():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "checks passed or failed" not in readme
    assert "It is never passed." not in readme
    assert "Nothing is verified until" not in readme
    assert "flagged and which raised no flag" in readme
    assert "It is never reported as no flag." in readme
    assert "It is never approved." not in readme
    assert "Nothing is approved until" in readme

    home = (PROJECT_ROOT / "docs" / "wiki" / "Home.md").read_text(encoding="utf-8")
    assert "Nothing is verified until" not in home
    assert "Nothing is approved until" in home

    research = (PROJECT_ROOT / "docs" / "wiki" / "Research-basis.md").read_text(encoding="utf-8")
    assert "Quotes are verified by code" not in research
    assert "Quotes are located by code" in research


def test_batch_l_notices_generator_refuses_missing_license_or_copyright():
    """Batch L finding 6: extract_package_info fails on missing license or missing copyright."""
    from scripts.generate_third_party_notices import extract_package_info

    # Missing license must fail
    with pytest.raises(ValueError, match="has no license defined"):
        extract_package_info("fakepkg-no-lic", {"version": "1.0.0"})

    # Missing copyright must fail
    with pytest.raises(ValueError, match="has no identifiable copyright"):
        extract_package_info("fakepkg-no-cr", {"version": "1.0.0", "license": "MIT"})

