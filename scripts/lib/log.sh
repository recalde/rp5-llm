#!/usr/bin/env bash
# Shared status lines. Source this file; do not execute it.

log_step() { printf '[+] %s\n' "$*"; }
log_ok() { printf '[✓] %s\n' "$*"; }
log_warn() { printf '[!] %s\n' "$*"; }
log_err() { printf '[x] %s\n' "$*" >&2; }

die() {
  log_err "$*"
  exit 1
}
