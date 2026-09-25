"""Process settings. Environment wins; code defaults match config/defaults.env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer") from exc
    if value < low or value > high:
        raise SystemExit(f"{name} must be between {low} and {high}")
    return value


@dataclass(frozen=True)
class Settings:
    bind: str
    port: int
    llama_url: str
    state_dir: Path
    config_dir: Path
    frontend_dir: Path
    models_path: Path
    detect_script: Path
    user: str
    backend: str
    kiosk: bool
    expose_lan: bool
    capture_content: bool
    history_limit: int
    history_days: int
    max_body_bytes: int
    allow_host_changes: bool
    allow_privileged_apply: bool
    ssh_home: Path | None

    @property
    def loopback_only(self) -> bool:
        return self.bind in {"127.0.0.1", "localhost", "::1"}

    @classmethod
    def from_env(cls) -> Settings:
        root = repo_root()
        state_default = root / "out" / "state"
        configured_state = os.environ.get("RP5_LLM_STATE", "").strip()
        if configured_state:
            state_dir = Path(configured_state)
        else:
            system_state = Path("/var/lib/rp5-llm")
            state_dir = system_state if os.access(system_state, os.W_OK) else state_default
        config_default = os.environ.get("RP5_LLM_CONFIG", "/etc/rp5-llm")
        ssh_home = os.environ.get("RP5_LLM_SSH_HOME", "").strip()
        backend = os.environ.get("RP5_LLM_BACKEND", "cpu").strip().lower() or "cpu"
        if backend not in {"cpu", "vulkan", "auto"}:
            raise SystemExit("RP5_LLM_BACKEND must be cpu, vulkan, or auto")
        return cls(
            bind=os.environ.get("RP5_LLM_BIND", "127.0.0.1").strip() or "127.0.0.1",
            port=_int("RP5_LLM_PORT", 8080, 1, 65535),
            llama_url=os.environ.get("RP5_LLM_LLAMA_URL", "http://127.0.0.1:8081").rstrip("/"),
            state_dir=state_dir,
            config_dir=Path(config_default),
            frontend_dir=Path(os.environ.get("RP5_LLM_FRONTEND", root / "ui" / "frontend")),
            models_path=Path(os.environ.get("RP5_LLM_MODELS", root / "config" / "models.yaml")),
            detect_script=root / "scripts" / "detect-hardware.sh",
            user=os.environ.get("RP5_LLM_USER", "deck").strip() or "deck",
            backend=backend,
            kiosk=_flag("RP5_UI_KIOSK"),
            expose_lan=_flag("RP5_LLM_EXPOSE_LAN"),
            capture_content=_flag("RP5_LLM_CAPTURE_CONTENT"),
            history_limit=_int("RP5_LLM_HISTORY_LIMIT", 1000, 1, 100000),
            history_days=_int("RP5_LLM_HISTORY_DAYS", 7, 1, 3650),
            max_body_bytes=_int("RP5_LLM_MAX_BODY", 2_000_000, 1024, 32_000_000),
            allow_host_changes=_flag("RP5_LLM_ALLOW_HOST_CHANGES"),
            allow_privileged_apply=_flag("RP5_LLM_ALLOW_PRIVILEGED_APPLY"),
            ssh_home=Path(ssh_home) if ssh_home else None,
        )
