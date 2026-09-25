#!/usr/bin/env bash
# Print a hardware report. RAM, CPU, and device model come from the live system.
# Network addresses are omitted so the report can be kept without publishing a LAN map.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"

OUT=""

usage() {
  cat <<'EOF'
Usage: detect-hardware.sh [--out DIR] [--json]

Print the live machine's architecture, device model, CPU count, and RAM.
--out DIR writes current.md and current.json in that directory.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --json)
      JSON=1
      shift
      ;;
    --out)
      [[ $# -ge 2 ]] || die "--out needs a directory"
      OUT=$2
      shift 2
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

JSON="${JSON:-0}"

json_escape() {
  # Escape a string for a JSON value. Newlines become \n.
  printf '%s' "$1" | awk '
    BEGIN { ORS="" }
    {
      gsub(/\\/, "\\\\")
      gsub(/"/, "\\\"")
      gsub(/\r/, "\\r")
      gsub(/\t/, "\\t")
      if (NR > 1) printf "\\n"
      printf "%s", $0
    }
  '
}

read_model() {
  local path
  for path in /proc/device-tree/model /sys/firmware/devicetree/base/model; do
    if [[ -r "$path" ]]; then
      tr -d '\0' <"$path"
      return 0
    fi
  done
  printf '%s' "unknown"
}

read_mem_kib() {
  local bytes
  if [[ -r /proc/meminfo ]]; then
    awk '/^MemTotal:/ { print $2; exit }' /proc/meminfo
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    bytes="$(sysctl -n hw.memsize 2>/dev/null || true)"
    if [[ -n "$bytes" ]]; then
      awk -v bytes="$bytes" 'BEGIN { printf "%d", bytes / 1024 }'
      return 0
    fi
  fi
  printf '%s' ""
}

read_cores() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
    return 0
  fi
  getconf _NPROCESSORS_ONLN 2>/dev/null || printf '%s' "unknown"
}

mem_gib() {
  local kib=$1
  if [[ -z "$kib" ]]; then
    printf '%s' "unknown"
    return 0
  fi
  awk -v kib="$kib" 'BEGIN { printf "%.1f GiB", kib / 1024 / 1024 }'
}

ARCH="$(uname -m)"
OS="$(uname -s)"
KERNEL="$(uname -r)"
MODEL="$(read_model)"
CORES="$(read_cores)"
MEM_KIB="$(read_mem_kib)"
MEM_HUMAN="$(mem_gib "$MEM_KIB")"
ROOT_SRC="$(df -k -P / | awk 'NR == 2 { print $1 }')"
ROOT_AVAIL="$(df -k -P / | awk 'NR == 2 { print $4 }')"
ROOT_FSTYPE="unknown"
if [[ "$OS" == "Linux" ]]; then
  ROOT_FSTYPE="$(df -T / | awk 'NR == 2 { print $2 }')"
fi

render_text() {
  cat <<EOF
Device:        ${MODEL}
OS:            ${OS}
Kernel:        ${KERNEL}
Architecture:  ${ARCH}
CPU cores:     ${CORES}
RAM:           ${MEM_HUMAN}
Root:          ${ROOT_SRC:-unknown} (${ROOT_FSTYPE}, ${ROOT_AVAIL:-unknown} KiB free)
EOF
}

render_json() {
  printf '{\n'
  printf '  "model": "%s",\n' "$(json_escape "$MODEL")"
  printf '  "os": "%s",\n' "$(json_escape "$OS")"
  printf '  "kernel": "%s",\n' "$(json_escape "$KERNEL")"
  printf '  "arch": "%s",\n' "$(json_escape "$ARCH")"
  printf '  "cpu_cores": "%s",\n' "$(json_escape "$CORES")"
  printf '  "mem_kib": "%s",\n' "$(json_escape "$MEM_KIB")"
  printf '  "mem": "%s",\n' "$(json_escape "$MEM_HUMAN")"
  printf '  "root_source": "%s",\n' "$(json_escape "${ROOT_SRC:-}")"
  printf '  "root_fstype": "%s",\n' "$(json_escape "$ROOT_FSTYPE")"
  printf '  "root_avail_kib": "%s"\n' "$(json_escape "${ROOT_AVAIL:-}")"
  printf '}\n'
}

if [[ "$JSON" -eq 1 ]]; then
  render_json
else
  render_text
fi

if [[ -n "$OUT" ]]; then
  mkdir -p "$OUT"
  render_text >"$OUT/current.md"
  render_json >"$OUT/current.json"
  log_ok "wrote ${OUT}/current.md and ${OUT}/current.json"
fi
