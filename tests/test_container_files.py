from __future__ import annotations

import json

import pytest

from harness.config import PROJECT_ROOT, load_config


def test_container_and_doc_files_exist():
    assert (PROJECT_ROOT / "Dockerfile").is_file()
    assert (PROJECT_ROOT / ".dockerignore").is_file()
    assert (PROJECT_ROOT / "compose.yaml").is_file()
    assert (PROJECT_ROOT / "compose.trial.yaml").is_file()
    assert (PROJECT_ROOT / "deploy" / "team.example.yaml").is_file()
    assert (PROJECT_ROOT / "deploy" / "team.trial.yaml").is_file()
    assert (PROJECT_ROOT / "deploy" / "trial-realm.json").is_file()
    assert (PROJECT_ROOT / "docs" / "wiki" / "Team-server.md").is_file()


def test_dockerfile_spec():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "node:22-slim" in dockerfile
    assert "python:3.11-slim" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "USER zyn" in dockerfile
    assert "EXPOSE 8600" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "pip wheel" in dockerfile or ".whl" in dockerfile
    # E4: wheel glob is handled via shell expansion
    assert 'WHEEL=$(ls /dist/*.whl)' in dockerfile


def test_compose_password_isolation_and_port_bindings():
    import yaml

    compose_path = PROJECT_ROOT / "compose.yaml"
    compose_data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    # E6: App container does NOT get ZYN_DATABASE_ADMIN_PASSWORD or admin URL
    zyn_env = compose_data["services"]["zyn"].get("environment", {})
    assert "ZYN_DATABASE_ADMIN_PASSWORD" not in str(zyn_env)
    assert "ZYN_DATABASE_ADMIN_URL" not in zyn_env

    # Upgrade service gets admin password
    upgrade_env = compose_data["services"]["upgrade"].get("environment", {})
    assert "ZYN_DATABASE_ADMIN_URL" in upgrade_env
    assert "ZYN_DATABASE_ADMIN_PASSWORD" in upgrade_env["ZYN_DATABASE_ADMIN_URL"]

    # E5: Production compose mounts config
    zyn_volumes = compose_data["services"]["zyn"].get("volumes", [])
    assert "./deploy/team.yaml:/data/config.yaml:ro" in zyn_volumes

    # E7: Ports bound to localhost (127.0.0.1)
    zyn_ports = compose_data["services"]["zyn"].get("ports", [])
    assert any("127.0.0.1:8600:8600" in p for p in zyn_ports)

    # db is internal to docker network
    assert "ports" not in compose_data["services"]["db"]

    # F2: compose.yaml uses ${VAR:?message} with no defaults for all secrets
    compose_raw = compose_path.read_text(encoding="utf-8")
    for secret_var in [
        "ZYN_DATABASE_ADMIN_PASSWORD",
        "ZYN_DATABASE_PASSWORD",
        "ZYN_SESSION_SECRET",
        "ZYN_OIDC_CLIENT_SECRET",
    ]:
        assert f"${{{secret_var}:?" in compose_raw, f"{secret_var} must use ${{VAR:?message}} in compose.yaml"
        assert f"${{{secret_var}:-" not in compose_raw, f"{secret_var} must not use defaults in compose.yaml"

    trial_path = PROJECT_ROOT / "compose.trial.yaml"
    trial_data = yaml.safe_load(trial_path.read_text(encoding="utf-8"))
    kc_ports = trial_data["services"]["keycloak"].get("ports", [])
    assert any("127.0.0.1:8080:8080" in p for p in kc_ports)

    # Trial uses consistent source for app database password across upgrade and zyn
    trial_raw = trial_path.read_text(encoding="utf-8")
    assert "${ZYN_DATABASE_PASSWORD:-trial-only-app-password}" in trial_raw

    # Trial compose is self-contained: defines db, upgrade, keycloak, zyn, and volumes
    for svc in ("db", "upgrade", "keycloak", "zyn"):
        assert svc in trial_data["services"], f"{svc} must be in compose.trial.yaml"
    assert "volumes" in trial_data


def test_dockerignore():
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    for pattern in ("node_modules", "runs/", ".env", ".git"):
        assert pattern in dockerignore


def test_settings_variables_consistent_across_compose_example_and_guide():
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    guide_text = (PROJECT_ROOT / "docs" / "wiki" / "Team-server.md").read_text(encoding="utf-8")
    example_text = (PROJECT_ROOT / "deploy" / "team.example.yaml").read_text(encoding="utf-8")

    shared_vars = [
        "ZYN_DATABASE_PASSWORD",
        "ZYN_DATABASE_ADMIN_PASSWORD",
        "ZYN_SESSION_SECRET",
        "ZYN_OIDC_CLIENT_SECRET",
    ]
    for var in shared_vars:
        assert var in compose_text, f"{var} missing in compose.yaml"
        assert var in guide_text, f"{var} missing in Team-server.md"

    for var in ["ZYN_DATABASE_PASSWORD", "ZYN_SESSION_SECRET", "ZYN_OIDC_CLIENT_SECRET"]:
        assert var in example_text, f"{var} missing in team.example.yaml"


def test_team_example_yaml_valid_and_rejects_missing_secrets(monkeypatch):
    example_path = PROJECT_ROOT / "deploy" / "team.example.yaml"
    assert example_path.is_file()

    monkeypatch.setenv("ZYN_DATABASE_PASSWORD", "pgpass123")
    monkeypatch.setenv("ZYN_SESSION_SECRET", "a" * 32)
    monkeypatch.setenv("ZYN_OIDC_CLIENT_SECRET", "oidcpass123")

    cfg = load_config(example_path)
    assert cfg.is_team()
    assert cfg.team is not None
    assert cfg.team.public_url == "https://zyn.corp.internal"
    assert len(cfg.team.projects) >= 1
    assert cfg.team.oidc.client_id
    assert cfg.team.database_url == "postgresql://zyn:pgpass123@db:5432/zyn"
    assert cfg.team.session_secret == "a" * 32
    assert cfg.team.oidc.client_secret == "oidcpass123"

    # allowed_models names profiles defined in config
    for m in cfg.team.allowed_models:
        assert m in cfg.profiles

    # Missing database password fails
    monkeypatch.delenv("ZYN_DATABASE_PASSWORD", raising=False)
    with pytest.raises(ValueError, match=r"ZYN_DATABASE_PASSWORD"):
        load_config(example_path)

    # Missing session secret fails
    monkeypatch.setenv("ZYN_DATABASE_PASSWORD", "pgpass123")
    monkeypatch.delenv("ZYN_SESSION_SECRET", raising=False)
    with pytest.raises(ValueError, match=r"ZYN_SESSION_SECRET"):
        load_config(example_path)


def test_trial_realm_and_trial_config(monkeypatch):
    realm_path = PROJECT_ROOT / "deploy" / "trial-realm.json"
    realm = json.loads(realm_path.read_text(encoding="utf-8"))
    client = next(c for c in realm["clients"] if c["clientId"] == "zyn-app")
    mapper = next(m for m in client["protocolMappers"] if m["name"] == "groups")
    assert mapper["protocolMapper"] == "oidc-group-membership-mapper"
    assert mapper["config"]["full.path"] == "false"
    assert mapper["config"]["claim.name"] == "groups"

    # Validate trial config
    trial_path = PROJECT_ROOT / "deploy" / "team.trial.yaml"
    monkeypatch.setenv("ZYN_DATABASE_PASSWORD", "trialpass")
    monkeypatch.setenv("ZYN_SESSION_SECRET", "t" * 32)
    cfg = load_config(trial_path)
    assert cfg.team is not None
    assert cfg.team.trial is True
    assert cfg.team.allow_insecure_http is True
    assert "localhost" in cfg.team.oidc.issuer


def test_it_guide_quality():
    guide_text = (PROJECT_ROOT / "docs" / "wiki" / "Team-server.md").read_text(encoding="utf-8")
    # No em dashes
    assert "—" not in guide_text
    # States what the container trial covers and what it does not
    assert "Tested in a container, not yet at a company" in guide_text
    assert "Not yet verified" not in guide_text
    assert "verify-trial-docker.sh" in guide_text
    # Notes stderr for structured JSON logging and null principal for 401
    assert "stderr" in guide_text
    assert "401" in guide_text and "null" in guide_text
    # Mentions PKCE and upgrades
    assert "PKCE" in guide_text
    assert "Upgrades" in guide_text or "upgrades" in guide_text
    # Mentions self-contained trial compose command
    assert "docker compose -f compose.trial.yaml up" in guide_text


def test_serve_refuses_all_interfaces_in_personal_mode(monkeypatch, capsys):
    from harness.__main__ import main

    monkeypatch.setenv("ZYN_DATABASE_URL", "")
    code = main(["serve", "--host", "0.0.0.0", "--no-browser"])
    assert code == 2
    err = capsys.readouterr().err
    assert "Personal mode only listens on this machine" in err


def test_batch_l_release_ci_builds_web_before_pytest():
    """Batch L finding 3: release.yml builds Web UI before running pytest so web/dist is present for tests."""
    release_yml = (PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    web_pos = release_yml.find("- name: Build Web UI")
    test_pos = release_yml.find("- name: Run linter and tests")
    assert web_pos != -1, "Build Web UI step missing in release.yml"
    assert test_pos != -1, "Run linter and tests step missing in release.yml"
    assert web_pos < test_pos, "Build Web UI must precede Run linter and tests in release.yml"


def test_batch_l_verify_trial_docker_cleanup_and_bcm_role():
    """Batch L finding 4 & Batch M finding 1: verify-trial-docker.sh cleanup trap, cookie cleanup, and list-shaped project role check."""
    script_text = (PROJECT_ROOT / "scripts" / "verify-trial-docker.sh").read_text(encoding="utf-8")
    # Only one trap on EXIT (calling cleanup)
    trap_lines = [line.strip() for line in script_text.splitlines() if line.strip().startswith("trap ") and "EXIT" in line]
    assert trap_lines == ["trap cleanup EXIT"], f"Expected single trap cleanup EXIT, got: {trap_lines}"

    # Cookie file removed inside cleanup()
    assert 'rm -f cookies.txt login_page.html "${COOKIE_FILE}"' in script_text

    # Role assertion checks bcm project with approver role in list shape
    assert "any(p.get('id') == 'bcm' and p.get('role') == 'approver' for p in d.get('projects', []))" in script_text
    assert '.projects[] | select(.id=="bcm" and .role=="approver")' in script_text

    # Test the behavior against a real /api/config response shape (where projects is a list)
    sample_config = {
        "person": {"name": "Alice", "email": "alice@test"},
        "projects": [
            {"id": "bcm", "name": "Body Control", "role": "approver", "four_eyes": True},
            {"id": "brake", "name": "Braking", "role": "viewer", "four_eyes": False},
        ],
        "admin": False,
        "mode": "team",
    }
    d = sample_config
    assert any(p.get("id") == "bcm" and p.get("role") == "approver" for p in d.get("projects", []))
    assert not any(p.get("id") == "brake" and p.get("role") == "approver" for p in d.get("projects", []))
    assert not any(p.get("id") == "other" and p.get("role") == "approver" for p in d.get("projects", []))
