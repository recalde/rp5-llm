#!/usr/bin/env bash
# Install the dashboard service onto a booted Pocknix system.
# Does not build llama.cpp, download a model, or change boot configuration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"

DRY=0

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/install-ui.sh [--dry-run]

Copies this checkout into /opt/rp5-llm/src, creates a virtualenv, and enables
rp5-llm-ui.service. The llama-server and kiosk units are installed and left disabled.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY=1
      shift
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

if [[ "$DRY" -eq 1 ]]; then
  log_step "would copy ui, config, and scripts to /opt/rp5-llm/src"
  log_step "would install Python dependencies into /opt/rp5-llm/venv"
  log_step "would enable rp5-llm-ui.service and leave llama-server and kiosk disabled"
  log_ok "dry run only"
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  die "run this on the Pocket, or pass --dry-run on this computer"
fi
if [[ "$(id -u)" -ne 0 ]]; then
  die "re-run with sudo"
fi

log_step "copying the management service"
install -d -m 0755 /opt/rp5-llm/src /etc/rp5-llm /var/lib/rp5-llm
rm -rf /opt/rp5-llm/src/ui /opt/rp5-llm/src/config /opt/rp5-llm/src/scripts
cp -R "$ROOT/ui" /opt/rp5-llm/src/ui
cp -R "$ROOT/config" /opt/rp5-llm/src/config
cp -R "$ROOT/scripts" /opt/rp5-llm/src/scripts
chmod 0755 /opt/rp5-llm/src/scripts/kiosk.sh

if [[ ! -e /etc/rp5-llm/defaults.env ]]; then
  cp "$ROOT/config/defaults.env" /etc/rp5-llm/defaults.env
  chmod 0644 /etc/rp5-llm/defaults.env
  log_ok "installed /etc/rp5-llm/defaults.env"
else
  log_ok "kept existing /etc/rp5-llm/defaults.env"
fi

log_step "creating the virtualenv"
python3 -m venv /opt/rp5-llm/venv
/opt/rp5-llm/venv/bin/pip install -r /opt/rp5-llm/src/ui/backend/requirements.txt

install -m 0644 \
  "$ROOT/systemd/rp5-llm.service" \
  "$ROOT/systemd/rp5-llm-ui.service" \
  "$ROOT/systemd/rp5-llm-setup.service" \
  "$ROOT/systemd/rp5-llm-kiosk.service" \
  /etc/systemd/system/
systemctl daemon-reload
systemctl enable rp5-llm-ui.service
systemctl restart rp5-llm-ui.service
log_ok "dashboard is enabled on the management port"
log_warn "llama-server stays disabled until its binary exists"
log_warn "kiosk stays disabled unless RP5_UI_KIOSK=true and you enable rp5-llm-kiosk.service"
