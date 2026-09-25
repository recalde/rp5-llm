import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_still_exits_cleanly_off_device():
    completed = subprocess.run(
        ["./scripts/bootstrap.sh"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "aarch64" in completed.stdout


def test_ui_install_and_firstboot_dry_runs():
    install = subprocess.run(
        ["./scripts/install-ui.sh", "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0
    firstboot = subprocess.run(
        ["./image/firstboot/firstboot.sh", "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert firstboot.returncode == 0
    refused = subprocess.run(
        ["./image/firstboot/firstboot.sh", "--root", "/"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert refused.returncode != 0


def test_flash_help_and_confirm_guard():
    help_run = subprocess.run(["./scripts/flash-sd.sh", "--help"], cwd=ROOT, check=False, capture_output=True, text=True)
    assert help_run.returncode == 0
    refused = subprocess.run(["./scripts/flash-sd.sh", "--confirm"], cwd=ROOT, check=False, capture_output=True, text=True)
    assert refused.returncode != 0
    assert "device" in refused.stderr.lower()
