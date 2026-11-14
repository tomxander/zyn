"""The light install: Zyn folder resolution, first-run setup, the demo and optional extras."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

from harness import __main__ as cli
from harness import config as zc

ROOT = Path(__file__).resolve().parent.parent


def test_zyn_home_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("ZYN_HOME", str(tmp_path / "mine"))
    assert zc.resolve_home() == (tmp_path / "mine").resolve()


def test_source_folder_is_its_own_home(monkeypatch):
    monkeypatch.delenv("ZYN_HOME", raising=False)
    assert zc.resolve_home() == ROOT


def test_installed_copy_uses_zyn_in_home_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("ZYN_HOME", raising=False)
    monkeypatch.setattr(zc, "SOURCE_ROOT", tmp_path / "site-packages")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "user")
    assert zc.resolve_home() == tmp_path / "user" / "zyn"


def test_new_folder_gets_starting_files_and_keeps_edits(tmp_path):
    home = tmp_path / "zyn"
    home.mkdir()
    (home / "config.yaml").write_text("mine", encoding="utf-8")
    copied = zc.ensure_home(home)
    assert "config.yaml" not in copied  # never overwrites
    assert (home / "config.yaml").read_text(encoding="utf-8") == "mine"
    for item in ("rules", "data/synthetic", ".env.example"):
        assert item in copied
    assert (home / "data" / "synthetic" / "icx100_reqset.csv").is_file()
    assert zc.ensure_home(home) == []  # second run: nothing to do


def test_light_install_leaves_out_the_heavy_stack():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    core = " ".join(meta["dependencies"]).lower()
    for heavy in ("docling", "streamlit", "torch", "transformers"):
        assert heavy not in core
    for needed in ("starlette", "uvicorn", "python-multipart", "cantools"):
        assert needed in core
    assert meta["scripts"]["zyn"] == "harness.__main__:main"


def test_pdf_without_document_reader_says_what_to_install(monkeypatch, tmp_path):
    from harness.sift import ingest

    monkeypatch.setitem(sys.modules, "docling.document_converter", None)
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match=r"pipx inject zyn-harness docling"):
        ingest.convert(pdf)


def test_demo_checks_by_code_and_reuses_its_run(cfg, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEMO_MARKER", tmp_path / "demo_run.txt")
    run_id, created = cli.demo_run(cfg)
    assert created
    again, created_again = cli.demo_run(cfg)
    assert (again, created_again) == (run_id, False)


def test_version_matches_pyproject():
    import harness

    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert harness.__version__ == meta["version"]


def test_ensure_home_personal_vs_team_mode(tmp_path, monkeypatch):
    """Personal mode keeps deleted files; team mode seeds missing starter items on every start."""
    # 1. Personal mode
    personal_home = tmp_path / "personal"
    personal_home.mkdir()
    personal_cfg = personal_home / "config.yaml"
    personal_cfg.write_text(
        """
db_path: audit.sqlite
roles: {generator: fake}
profiles: {fake: {provider: fake, model: m}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(zc, "PROJECT_ROOT", personal_home)
    zc.load_config(personal_cfg)
    assert not (personal_home / "rules").exists()

    # 2. Team mode
    team_home = tmp_path / "team"
    team_home.mkdir()
    team_cfg = team_home / "config.yaml"
    team_cfg.write_text(
        """
db_path: audit.sqlite
roles: {generator: fake}
profiles: {fake: {provider: fake, model: m}}
team:
  trial: true
  database_url: postgresql://zyn:trial-only-app-password@localhost/zyn
  public_url: http://localhost:8600
  session_secret: trial-only-session-secret-at-least-32-chars-long
  oidc:
    issuer: http://localhost:8080/realms/zyn-trial
    client_id: cid
    client_secret: zyn-trial-client-secret
  admins: [admin]
  projects: {}
  allowed_models: [fake]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(zc, "PROJECT_ROOT", team_home)
    zc.load_config(team_cfg)
    assert (team_home / "rules").is_dir()
