#!/usr/bin/env bash
# First on-device setup. Safe to run more than once.
# Creates runtime directories and records hardware. It does not install llama.cpp,
# download a model, or change boot configuration. Finish those phases over SSH.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/bootstrap.sh

On aarch64 Linux this creates:
  /opt/rp5-llm
  /var/lib/rp5-llm
  /var/lib/rp5-llm/models
  /etc/rp5-llm

An existing /etc/rp5-llm/defaults.env is left in place.
Other machines only get a hardware report.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ $# -gt 0 ]]; then
  die "unknown argument: $1"
fi

log_step "hardware detection"
if [[ "$(id -u)" -eq 0 && "$(uname -s)" == "Linux" && "$(uname -m)" == "aarch64" ]]; then
  "$ROOT/scripts/detect-hardware.sh"
else
  "$ROOT/scripts/detect-hardware.sh" --out "$ROOT/out/hardware"
fi

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "aarch64" ]]; then
  log_warn "runtime directories are created only on aarch64 Linux"
  log_warn "flash the SD card, boot Pocknix, and run this again over SSH"
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  log_warn "not root; re-run with sudo to create runtime directories"
  exit 0
fi

log_step "creating runtime directories"
install -d -m 0755 \
  /opt/rp5-llm \
  /var/lib/rp5-llm \
  /var/lib/rp5-llm/models \
  /var/lib/rp5-llm/hardware \
  /etc/rp5-llm

"$ROOT/scripts/detect-hardware.sh" --out /var/lib/rp5-llm/hardware

if [[ ! -e /etc/rp5-llm/defaults.env ]]; then
  cp "$ROOT/config/defaults.env" /etc/rp5-llm/defaults.env
  chmod 0644 /etc/rp5-llm/defaults.env
  log_ok "installed /etc/rp5-llm/defaults.env"
else
  log_ok "kept existing /etc/rp5-llm/defaults.env"
fi

log_ok "runtime directories are ready"
log_warn "llama.cpp is not installed yet; CPU inference still has to come first"
log_warn "dashboard: sudo ./scripts/install-ui.sh"
