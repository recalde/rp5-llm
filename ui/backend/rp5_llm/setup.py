"""Validated setup plan. The HTTP process saves it. The root oneshot applies it.

There is no route that accepts a shell command.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rp5_llm.models import find_model, load_models
from rp5_llm.settings import Settings

HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
PUBLIC_KEY_RE = re.compile(
    r"^(ssh-ed25519|ssh-rsa|ssh-ed25519-sk|ecdsa-sha2-nistp256|"
    r"sk-ecdsa-sha2-nistp256@openssh.com) [A-Za-z0-9+/=]+(?: .*)?$"
)
PLAN_KEYS = {"hostname", "sshPublicKey", "model", "backend", "exposeLan", "kiosk"}


class SetupError(ValueError):
    pass


def empty_plan() -> dict:
    return {
        "hostname": "",
        "sshPublicKey": "",
        "model": "",
        "backend": "cpu",
        "exposeLan": False,
        "kiosk": False,
    }


def load_plan(path: Path, models: list[dict]) -> dict:
    if not path.is_file():
        return empty_plan()
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError("saved plan is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SetupError("saved plan is not an object")
    return validate_plan(payload, models)


def validate_plan(payload: dict, models: list[dict]) -> dict:
    unknown = set(payload) - PLAN_KEYS
    if unknown:
        raise SetupError("unsupported plan fields")
    plan = empty_plan()
    hostname = payload.get("hostname", "")
    if not isinstance(hostname, str):
        raise SetupError("hostname must be a string")
    hostname = hostname.strip().lower()
    if hostname and not HOST_RE.match(hostname):
        raise SetupError("hostname must be a single DNS label")
    plan["hostname"] = hostname
    key = payload.get("sshPublicKey", "")
    if not isinstance(key, str):
        raise SetupError("ssh public key must be a string")
    plan["sshPublicKey"] = validate_ssh_key(key)
    model_id = payload.get("model", "")
    if not isinstance(model_id, str):
        raise SetupError("model must be a string")
    model_id = model_id.strip()
    if model_id:
        if find_model(models, model_id) is None:
            raise SetupError("model is not in the manifest")
    plan["model"] = model_id
    backend = payload.get("backend", "cpu")
    if backend not in {"cpu", "vulkan", "auto"}:
        raise SetupError("backend must be cpu, vulkan, or auto")
    plan["backend"] = backend
    for field in ("exposeLan", "kiosk"):
        value = payload.get(field, False)
        if not isinstance(value, bool):
            raise SetupError(f"{field} must be true or false")
        plan[field] = value
    return plan


def validate_ssh_key(value: str) -> str:
    if value.strip() == "":
        return ""
    if "PRIVATE" in value.upper() or "-----" in value:
        raise SetupError("private keys are not accepted")
    line = value.strip()
    if "\n" in line or "\r" in line:
        raise SetupError("paste one public key")
    if len(line) > 8192:
        raise SetupError("public key is too long")
    if not PUBLIC_KEY_RE.match(line):
        raise SetupError("expected a single OpenSSH public key")
    return line


def save_plan(path: Path, plan: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(plan, indent=2) + "\n")
    temp.chmod(0o640)
    temp.replace(path)


def render_ui_env(plan: dict) -> str:
    bind = "0.0.0.0" if plan["exposeLan"] else "127.0.0.1"
    lines = [
        f"RP5_LLM_BIND={bind}",
        f"RP5_LLM_EXPOSE_LAN={'true' if plan['exposeLan'] else 'false'}",
        f"RP5_UI_KIOSK={'true' if plan['kiosk'] else 'false'}",
        f"RP5_LLM_BACKEND={plan['backend']}",
        f"RP5_LLM_MODEL={plan['model']}",
    ]
    return "\n".join(lines) + "\n"


def write_ui_env(path: Path, plan: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_ui_env(plan))
    path.chmod(0o644)


def setup_complete(path: Path) -> bool:
    return path.is_file()


def mark_complete(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("complete\n")
    path.chmod(0o644)


def clear_complete(path: Path) -> None:
    if path.is_file():
        path.unlink()


def install_ssh_key(home: Path, key: str) -> None:
    if not key:
        return
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    ssh_dir.chmod(0o700)
    auth = ssh_dir / "authorized_keys"
    existing = auth.read_text() if auth.is_file() else ""
    if key in existing.splitlines():
        auth.chmod(0o600)
        return
    with auth.open("a") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(key + "\n")
    auth.chmod(0o600)


def privileged_commands(settings: Settings, plan: dict) -> list[list[str]]:
    """Fixed argument lists. Nothing here is taken from a shell string."""
    if not settings.allow_privileged_apply:
        return []
    commands: list[list[str]] = []
    if plan["hostname"] and settings.allow_host_changes:
        commands.append(["hostnamectl", "set-hostname", plan["hostname"]])
    if plan["kiosk"]:
        commands.append(["systemctl", "enable", "rp5-llm-kiosk.service"])
    else:
        commands.append(["systemctl", "disable", "rp5-llm-kiosk.service"])
    return commands


def apply_plan(settings: Settings, plan: dict, runner=None) -> list[dict]:
    """Write config files and, when privileged apply is enabled, run the fixed commands."""
    models = load_models(settings.models_path)
    plan = validate_plan(plan, models)
    desired = settings.state_dir / "desired.json"
    save_plan(desired, plan)
    write_ui_env(settings.state_dir / "ui.env", plan)
    config_env = settings.config_dir / "ui.env"
    if _writable_dir(settings.config_dir):
        write_ui_env(config_env, plan)
    steps = [
        {"id": "configuration", "status": "pass", "detail": "saved the setup plan"},
    ]
    if plan["sshPublicKey"]:
        if settings.ssh_home is not None and settings.allow_privileged_apply:
            install_ssh_key(settings.ssh_home, plan["sshPublicKey"])
            steps.append({"id": "ssh", "status": "pass", "detail": "installed the public key"})
        else:
            pending = settings.state_dir / "pending-authorized-keys"
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(plan["sshPublicKey"] + "\n")
            pending.chmod(0o600)
            steps.append({"id": "ssh", "status": "queued", "detail": "public key saved for the setup service"})
    else:
        steps.append({"id": "ssh", "status": "pass", "detail": "no key submitted"})
    commands = privileged_commands(settings, plan)
    if plan["hostname"]:
        if any(cmd[:2] == ["hostnamectl", "set-hostname"] for cmd in commands):
            steps.append({"id": "hostname", "status": "pass", "detail": plan["hostname"]})
        else:
            steps.append({"id": "hostname", "status": "queued", "detail": "saved for the setup service"})
    else:
        steps.append({"id": "hostname", "status": "pass", "detail": "unchanged"})
    model = find_model(models, plan["model"]) if plan["model"] else None
    if model is None:
        steps.append({"id": "model", "status": "pass", "detail": "no model selected"})
    elif not model["sha256"]:
        steps.append({"id": "model", "status": "blocked", "detail": "checksum is not pinned; download refused"})
    else:
        steps.append({"id": "model", "status": "queued", "detail": model["file"]})
    steps.append(
        {
            "id": "llama",
            "status": "blocked",
            "detail": "llama.cpp installer is not in this build; CPU remains the baseline",
        }
    )
    if commands and runner is not None:
        for command in commands:
            runner(command)
    elif commands and runner is None:
        import subprocess

        for command in commands:
            subprocess.run(command, check=False)
    return steps


def _writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return path.is_dir() and os_access_write(path)


def os_access_write(path: Path) -> bool:
    import os

    return os.access(path, os.W_OK)
