from fastapi.testclient import TestClient

from rp5_llm.setup import SetupError, privileged_commands, validate_plan, validate_ssh_key


PUBLIC = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGtestkeyvaluecomment"


def _auth(client: TestClient) -> tuple[dict, str]:
    status = client.get("/api/status").json()
    session = client.get("/api/setup/session")
    csrf = session.json()["csrf"]
    headers = {"x-csrf-token": csrf, "x-setup-code": status["setupCode"]}
    return headers, status["setupCode"]


def test_private_key_is_rejected():
    try:
        validate_ssh_key("-----BEGIN OPENSSH PRIVATE KEY-----\nabc")
    except SetupError as exc:
        assert "private" in str(exc)
    else:
        raise AssertionError("private key was accepted")


def test_install_rejects_unknown_model_and_accepts_manifest(client: TestClient):
    headers, _code = _auth(client)
    rejected = client.post("/api/setup/install", headers=headers, json={"model": "not-a-model", "backend": "cpu"})
    assert rejected.status_code == 400
    accepted = client.post(
        "/api/setup/install",
        headers=headers,
        json={"model": "small", "backend": "cpu", "exposeLan": False, "kiosk": False, "hostname": "rp5-llm"},
    )
    assert accepted.status_code == 200
    steps = {step["id"]: step["status"] for step in accepted.json()["steps"]}
    assert steps["configuration"] == "pass"
    assert steps["model"] == "blocked"
    assert steps["llama"] == "blocked"


def test_install_requires_csrf_and_setup_code(client: TestClient):
    response = client.post("/api/setup/install", json={"backend": "cpu"})
    assert response.status_code == 403


def test_complete_locks_install(client: TestClient):
    headers, _code = _auth(client)
    assert client.post("/api/setup/complete", headers=headers, json={}).status_code == 200
    locked = client.post("/api/setup/install", headers=headers, json={"backend": "cpu"})
    assert locked.status_code == 403


def test_privileged_commands_are_a_fixed_list():
    from rp5_llm.settings import repo_root
    from rp5_llm.settings import Settings
    from pathlib import Path

    root = repo_root()
    settings = Settings(
        bind="127.0.0.1",
        port=8080,
        llama_url="http://127.0.0.1:8081",
        state_dir=Path("/tmp"),
        config_dir=Path("/tmp"),
        frontend_dir=root / "ui" / "frontend",
        models_path=root / "config" / "models.yaml",
        detect_script=root / "scripts" / "detect-hardware.sh",
        user="deck",
        backend="cpu",
        kiosk=False,
        expose_lan=False,
        capture_content=False,
        history_limit=10,
        history_days=7,
        max_body_bytes=1000,
        allow_host_changes=True,
        allow_privileged_apply=True,
        ssh_home=None,
    )
    plan = validate_plan({"hostname": "rp5-llm", "backend": "cpu", "kiosk": False, "exposeLan": False}, [])
    commands = privileged_commands(settings, plan)
    assert commands[0] == ["hostnamectl", "set-hostname", "rp5-llm"]
    assert all(isinstance(part, str) for command in commands for part in command)
    assert PUBLIC not in " ".join(" ".join(command) for command in commands)
