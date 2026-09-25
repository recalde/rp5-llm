#!/usr/bin/env bash
# Remove the dashboard service. Model files and request history stay unless --purge-state.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"

PURGE=0
DRY=0

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/uninstall-ui.sh [--dry-run] [--purge-state]

Disables the rp5-llm units and removes /opt/rp5-llm/venv.
--purge-state also removes /var/lib/rp5-llm.
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
    --purge-state)
      PURGE=1
      shift
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

if [[ "$DRY" -eq 1 ]]; then
  log_step "would disable rp5-llm-ui, rp5-llm-kiosk, and rp5-llm"
  log_step "would remove /opt/rp5-llm/venv and the systemd units"
  if [[ "$PURGE" -eq 1 ]]; then
    log_warn "would also remove /var/lib/rp5-llm"
  fi
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  die "run this on the Pocket, or pass --dry-run on this computer"
fi
if [[ "$(id -u)" -ne 0 ]]; then
  die "re-run with sudo"
fi

systemctl disable --now rp5-llm-ui.service 2>/dev/null || true
systemctl disable --now rp5-llm-kiosk.service 2>/dev/null || true
systemctl disable --now rp5-llm.service 2>/dev/null || true
rm -f \
  /etc/systemd/system/rp5-llm.service \
  /etc/systemd/system/rp5-llm-ui.service \
  /etc/systemd/system/rp5-llm-setup.service \
  /etc/systemd/system/rp5-llm-kiosk.service
systemctl daemon-reload || true
rm -rf /opt/rp5-llm/venv /opt/rp5-llm/src
if [[ "$PURGE" -eq 1 ]]; then
  rm -rf /var/lib/rp5-llm
  log_ok "removed request history and setup state"
fi
log_ok "dashboard service removed"
