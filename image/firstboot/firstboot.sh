#!/usr/bin/env bash
# Copy the management service into a Linux root the operator names.
# This does not flash a card, mount a filesystem, or touch a bootloader.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../scripts/lib/log.sh
source "$ROOT/scripts/lib/log.sh"

DRY=0
TARGET=""

usage() {
  cat <<'EOF'
Usage:
  ./image/firstboot/firstboot.sh --dry-run
  ./image/firstboot/firstboot.sh --root /mnt/pocknix
  sudo ./image/firstboot/firstboot.sh

--root copies ui, config, scripts, and systemd units into that directory.
It must be an absolute path, and it cannot be /. On a booted Pocket, run
without --root to call scripts/install-ui.sh.
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
    --root)
      [[ $# -ge 2 ]] || die "--root needs a directory"
      TARGET=$2
      shift 2
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

if [[ -n "$TARGET" ]]; then
  case "$TARGET" in
    /*) ;;
    *)
      die "--root must be an absolute path"
      ;;
  esac
  case "$TARGET" in
    /|/boot|/boot/*)
      die "refusing to layer onto ${TARGET}"
      ;;
  esac
  if [[ "$DRY" -eq 1 ]]; then
    log_step "would copy the management service into ${TARGET}"
    log_ok "dry run only; no bootloader or disk image is modified"
    exit 0
  fi
  [[ -d "$TARGET" ]] || die "directory does not exist: ${TARGET}"
  log_step "copying the management service into ${TARGET}"
  install -d -m 0755 \
    "$TARGET/opt/rp5-llm/src" \
    "$TARGET/etc/systemd/system/multi-user.target.wants" \
    "$TARGET/etc/rp5-llm"
  rm -rf "$TARGET/opt/rp5-llm/src/ui" "$TARGET/opt/rp5-llm/src/config" "$TARGET/opt/rp5-llm/src/scripts"
  cp -R "$ROOT/ui" "$TARGET/opt/rp5-llm/src/ui"
  cp -R "$ROOT/config" "$TARGET/opt/rp5-llm/src/config"
  cp -R "$ROOT/scripts" "$TARGET/opt/rp5-llm/src/scripts"
  unit=""
  for unit in "$ROOT"/systemd/rp5-llm*.service; do
    cp "$unit" "$TARGET/etc/systemd/system/"
    chmod 0644 "$TARGET/etc/systemd/system/$(basename "$unit")"
  done
  if [[ ! -e "$TARGET/etc/rp5-llm/defaults.env" ]]; then
    cp "$ROOT/config/defaults.env" "$TARGET/etc/rp5-llm/defaults.env"
  fi
  ln -sfn ../rp5-llm-ui.service "$TARGET/etc/systemd/system/multi-user.target.wants/rp5-llm-ui.service"
  log_ok "files copied into ${TARGET}"
  log_warn "llama-server and the kiosk unit were not enabled"
  exit 0
fi

if [[ "$DRY" -eq 1 ]]; then
  log_step "would run scripts/install-ui.sh"
  log_ok "dry run only"
  exit 0
fi

exec "$ROOT/scripts/install-ui.sh"
