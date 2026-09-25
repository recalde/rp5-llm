from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rp5_llm.app import create_app
from rp5_llm.settings import Settings, repo_root


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    root = repo_root()
    return Settings(
        bind="127.0.0.1",
        port=8080,
        llama_url="http://127.0.0.1:9",
        state_dir=tmp_path / "state",
        config_dir=tmp_path / "config",
        frontend_dir=root / "ui" / "frontend",
        models_path=root / "config" / "models.yaml",
        detect_script=root / "scripts" / "detect-hardware.sh",
        user="deck",
        backend="cpu",
        kiosk=False,
        expose_lan=False,
        capture_content=False,
        history_limit=1000,
        history_days=7,
        max_body_bytes=2_000_000,
        allow_host_changes=False,
        allow_privileged_apply=False,
        ssh_home=None,
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
