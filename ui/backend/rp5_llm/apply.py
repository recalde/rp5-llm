"""Root oneshot entry: apply a plan that the HTTP process already validated."""

from __future__ import annotations

import argparse
import subprocess
import sys

from rp5_llm.models import load_models
from rp5_llm.settings import Settings
from rp5_llm.setup import apply_plan, load_plan, privileged_commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a saved rp5-llm setup plan")
    parser.add_argument("--dry-run", action="store_true", help="print privileged commands and write nothing")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    models = load_models(settings.models_path)
    plan = load_plan(settings.state_dir / "desired.json", models)
    if args.dry_run:
        preview = _privileged_view(settings)
        for command in privileged_commands(preview, plan):
            print(" ".join(command))
        return 0

    def runner(command: list[str]) -> None:
        subprocess.run(command, check=False)

    steps = apply_plan(settings, plan, runner=runner)
    for step in steps:
        print(f"{step['status']:8} {step['id']:16} {step['detail']}")
    return 0


def _privileged_view(settings: Settings) -> Settings:
    return Settings(
        bind=settings.bind,
        port=settings.port,
        llama_url=settings.llama_url,
        state_dir=settings.state_dir,
        config_dir=settings.config_dir,
        frontend_dir=settings.frontend_dir,
        models_path=settings.models_path,
        detect_script=settings.detect_script,
        user=settings.user,
        backend=settings.backend,
        kiosk=settings.kiosk,
        expose_lan=settings.expose_lan,
        capture_content=settings.capture_content,
        history_limit=settings.history_limit,
        history_days=settings.history_days,
        max_body_bytes=settings.max_body_bytes,
        allow_host_changes=True,
        allow_privileged_apply=True,
        ssh_home=settings.ssh_home,
    )


if __name__ == "__main__":
    sys.exit(main())
