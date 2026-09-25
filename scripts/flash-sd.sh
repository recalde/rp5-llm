#!/usr/bin/env bash
# Download the pinned upstream Pocknix SM8250 image and write it to a microSD card.
# Writes nothing unless --device and --confirm are both present.
# This never selects a disk on its own, and it never touches the Retroid Pocket 5
# internal storage. Android and the bootloader stay as they are.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"
# shellcheck source=../image/upstream.env
source "$ROOT/image/upstream.env"

CACHE="$ROOT/image/cache"
DEVICE=""
CONFIRM=0
DOWNLOAD_ONLY=0
VISIONOX=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/flash-sd.sh
      Show the pinned image and external disks. Writes nothing.

  ./scripts/flash-sd.sh --download
      Download the image into image/cache and verify its checksum.

  ./scripts/flash-sd.sh --device diskN
      Check that diskN looks like a removable card. Writes nothing.

  ./scripts/flash-sd.sh --device diskN --confirm
      Download if needed, verify, and write the image to that card.

  ./scripts/flash-sd.sh --device diskN --confirm --visionox
      Same, then create an empty "visionox" file on the POCKNIX partition
      for untested 2026 12 GB Retroid Pocket 5 panels.

diskN is the whole card (disk4), not a partition (disk4s1). On Linux pass
sda or mmcblk0. The card must be plugged into this computer.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --download)
      DOWNLOAD_ONLY=1
      shift
      ;;
    --confirm)
      CONFIRM=1
      shift
      ;;
    --visionox)
      VISIONOX=1
      shift
      ;;
    --device)
      [[ $# -ge 2 ]] || die "--device needs a disk id, for example disk4"
      DEVICE=$2
      shift 2
      ;;
    *)
      die "unknown argument: $1 (try --help)"
      ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

lowercase() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

checksum_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{ print $1 }'
  else
    shasum -a 256 "$1" | awk '{ print $1 }'
  fi
}

verify_published_checksum() {
  local published want curl_status
  require_cmd curl
  log_step "checking the published checksum against the pin"
  set +e
  published="$(
    curl --fail --silent --show-error --location --retry 3 \
      --user-agent "rp5-llm-flash" \
      "$POCKNIX_SHA_URL" | awk 'NF { print $1; exit }'
  )"
  curl_status=$?
  set -e
  if [[ "$curl_status" -ne 0 || -z "$published" ]]; then
    return 1
  fi
  want="$(lowercase "$POCKNIX_SHA256")"
  published="$(lowercase "$published")"
  if [[ "$published" != "$want" ]]; then
    die "pin ${want} does not match ${POCKNIX_SHA_URL} (${published}). Update image/upstream.env only after you trust the new image."
  fi
  log_ok "pin matches the published checksum"
}

hash_matches() {
  local got want
  log_step "hashing $(basename "$1")"
  got="$(lowercase "$(checksum_of "$1")")"
  want="$(lowercase "$POCKNIX_SHA256")"
  if [[ "$got" != "$want" ]]; then
    log_err "checksum mismatch for $1"
    log_err "expected ${want}"
    log_err "got      ${got}"
    return 1
  fi
  log_ok "checksum matches"
}

ensure_image() {
  local dest partial
  require_cmd curl
  mkdir -p "$CACHE"
  dest="$CACHE/$POCKNIX_IMAGE"
  partial="${dest}.partial"
  if [[ -f "$dest" ]] && hash_matches "$dest"; then
    if ! verify_published_checksum; then
      log_warn "could not fetch ${POCKNIX_SHA_URL}; the cached file still matches the pin"
    fi
    log_ok "using cached ${dest}"
    return 0
  fi
  if ! verify_published_checksum; then
    die "could not read ${POCKNIX_SHA_URL}"
  fi
  if [[ -f "$dest" ]]; then
    log_warn "cached image failed verification; downloading again"
    rm -f "$dest"
  fi
  log_step "downloading ${POCKNIX_URL}"
  log_warn "about 10.5 GB, saved under image/cache (not committed)"
  curl --fail --location --retry 5 --retry-delay 2 --continue-at - \
    --user-agent "rp5-llm-flash" \
    --output "$partial" \
    "$POCKNIX_URL"
  mv "$partial" "$dest"
  hash_matches "$dest"
}

# Print the uncompressed size of a zstd frame, or nothing if the header omits it.
zst_uncompressed_bytes() {
  python3 - "$1" <<'PY'
import sys
path = sys.argv[1]
with open(path, "rb") as handle:
    blob = handle.read(64)
if len(blob) < 6:
    sys.exit(0)
offset = 0
magic = blob[offset:offset + 4]
# Skip one skippable frame if that is what the file starts with.
if 0x50 <= magic[0] <= 0x5F and magic[1:] == b"\x2a\x4d\x18":
    if len(blob) < 8:
        sys.exit(0)
    skip = int.from_bytes(blob[4:8], "little")
    offset = 8 + skip
    with open(path, "rb") as handle:
        handle.seek(offset)
        blob = handle.read(64)
    offset = 0
if blob[0:4] != b"\x28\xb5\x2f\xfd":
    sys.exit(0)
desc = blob[4]
fcs = (desc >> 6) & 0x3
single = (desc >> 5) & 0x1
did = desc & 0x3
index = 5
if not single:
    index += 1
index += {0: 0, 1: 1, 2: 2, 3: 4}[did]
if fcs == 0 and not single:
    sys.exit(0)
nbytes = {0: 1, 1: 2, 2: 4, 3: 8}[fcs]
raw = blob[index:index + nbytes]
if len(raw) != nbytes:
    sys.exit(0)
value = int.from_bytes(raw, "little")
if fcs == 1:
    value += 256
print(value)
PY
}

preflight_capacity() {
  local bytes
  case "$(uname -s)" in
    Darwin)
      bytes="$(macos_disk_bytes "$DEVICE")"
      ;;
    Linux)
      bytes="$(linux_disk_bytes "${DEVICE#/dev/}")"
      ;;
    *)
      die "flashing is supported on macOS and Linux"
      ;;
  esac
  [[ -n "$bytes" ]] || die "could not read the size of ${DEVICE}"
  if [[ "$bytes" -lt "$POCKNIX_MIN_DISK_BYTES" ]]; then
    die "disk is ${bytes} bytes. Pocknix wants a 64 GB card or larger (128 GB recommended)."
  fi
  log_ok "disk reports ${bytes} bytes"
}

disk_is_large_enough() {
  local disk_bytes=$1 image=$2 image_bytes
  if [[ "$disk_bytes" -lt "$POCKNIX_MIN_DISK_BYTES" ]]; then
    die "disk is ${disk_bytes} bytes. Pocknix wants a 64 GB card or larger (128 GB recommended)."
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    log_warn "python3 is missing, so the uncompressed image size was not checked"
    return 0
  fi
  image_bytes="$(zst_uncompressed_bytes "$image" || true)"
  if [[ -z "$image_bytes" ]]; then
    log_warn "image header has no uncompressed size; relying on the 64 GB minimum"
    return 0
  fi
  log_step "uncompressed image is ${image_bytes} bytes; disk is ${disk_bytes} bytes"
  if [[ "$image_bytes" -gt "$disk_bytes" ]]; then
    die "the image is larger than this card"
  fi
  log_ok "the card is large enough"
}

normalize_disk() {
  local name=$1
  name="${name#/dev/}"
  case "$name" in
    rdisk*)
      name="disk${name#rdisk}"
      ;;
  esac
  printf '%s' "$name"
}

macos_field() {
  local disk=$1 field=$2
  diskutil info "$disk" | awk -F': +' -v f="$field" '
    $0 ~ "^[[:space:]]*" f ":" {
      sub(/^[[:space:]]*[^:]+:[[:space:]]*/, "")
      print
      exit
    }
  '
}

macos_list_disks() {
  local listing
  log_step "external disks on this Mac"
  listing="$(diskutil list external physical 2>/dev/null || true)"
  if [[ -z "$listing" ]]; then
    log_warn "no external disk is attached"
  else
    printf '%s\n' "$listing"
  fi
}

macos_assert_safe() {
  local id=$1 location removable virtual protocol whole boot
  [[ "$id" != "disk0" ]] || die "refusing disk0, the internal Mac disk"
  case "$id" in
    *s[0-9]*)
      die "pass the whole card (${id} looks like a partition)"
      ;;
  esac
  diskutil info "$id" >/dev/null 2>&1 || die "no such disk: ${id}. Run ./scripts/flash-sd.sh to list external disks."
  location="$(macos_field "$id" "Device Location")"
  removable="$(macos_field "$id" "Removable Media")"
  virtual="$(macos_field "$id" "Virtual")"
  protocol="$(macos_field "$id" "Protocol")"
  whole="$(macos_field "$id" "Part of Whole")"
  whole="${whole%% *}"
  [[ "$whole" == "$id" ]] || die "pass the whole card, not a slice (part of ${whole})"
  case "$location" in
    *External*) ;;
    *)
      die "refusing ${id}: Device Location is '${location:-unknown}', not External"
      ;;
  esac
  case "$virtual" in
    *Yes*)
      die "refusing ${id}: it is a virtual disk"
      ;;
  esac
  case "$protocol" in
    *Disk\ Image*|*Apple\ Fabric*)
      die "refusing ${id}: protocol is ${protocol}"
      ;;
  esac
  case "$removable" in
    *Fixed*)
      die "refusing ${id}: Removable Media is Fixed"
      ;;
  esac
  boot="$(diskutil info / | awk -F': +' '/^[[:space:]]*Part of Whole:/ { print $2; exit }')"
  boot="${boot%% *}"
  [[ "$id" != "$boot" ]] || die "refusing ${id}: it holds this Mac's startup disk"
  log_ok "${id} is external ($(macos_field "$id" "Disk Size"))"
}

macos_disk_bytes() {
  diskutil info "$1" | sed -n 's/.*(\([0-9][0-9]*\) Bytes).*/\1/p' | head -n 1
}

macos_mark_visionox() {
  local disk=$1 vol name
  log_step "looking for the POCKNIX partition to mark the Visionox panel"
  diskutil mountDisk "$disk" || true
  vol=""
  if [[ -f /Volumes/POCKNIX/KERNEL ]]; then
    vol="/Volumes/POCKNIX"
  else
    for name in /Volumes/*; do
      if [[ -f "${name}/KERNEL" ]]; then
        vol=$name
        break
      fi
    done
  fi
  if [[ -z "$vol" ]]; then
    die "the image was written, but the POCKNIX volume did not mount. Mount it and create an empty file named visionox next to KERNEL, then boot."
  fi
  if ! : >"${vol}/visionox"; then
    sudo tee "${vol}/visionox" >/dev/null
  fi
  log_ok "created ${vol}/visionox"
}

macos_write() {
  local id=$1 image=$2 node bytes
  node="/dev/r${id}"
  bytes="$(macos_disk_bytes "$id")"
  [[ -n "$bytes" ]] || die "could not read the size of ${id}"
  disk_is_large_enough "$bytes" "$image"
  log_step "unmounting ${id}"
  diskutil unmountDisk "$id"
  sudo -v
  log_step "writing ${image} to ${node}"
  log_warn "this erases the card. The Retroid Pocket 5 internal storage is not attached to this computer."
  zstd -dc -- "$image" | sudo dd of="$node" bs=4194304 status=progress
  sync
  log_ok "image written to ${id}"
  if [[ "$VISIONOX" -eq 1 ]]; then
    macos_mark_visionox "$id"
  fi
  diskutil eject "$id" || diskutil unmountDisk "$id" || true
  log_ok "card ejected; you can remove it"
}

linux_list_disks() {
  log_step "disks on this computer"
  lsblk -dn -o NAME,RM,TRAN,SIZE,TYPE,MODEL
}

linux_assert_safe() {
  local name=$1 tran rm type root_src parent
  name="${name#/dev/}"
  case "$name" in
    *[0-9]p[0-9]*|*s[0-9]*)
      die "pass the whole disk (${name} looks like a partition)"
      ;;
  esac
  type="$(lsblk -dn -o TYPE "/dev/${name}")"
  [[ "$type" == "disk" ]] || die "refusing ${name}: type is ${type:-unknown}"
  rm="$(lsblk -dn -o RM "/dev/${name}")"
  tran="$(lsblk -dn -o TRAN "/dev/${name}")"
  if [[ "$rm" != "1" && "$tran" != "usb" ]]; then
    die "refusing ${name}: it is not a removable or USB disk (RM=${rm:-?} TRAN=${tran:-?})"
  fi
  root_src="$(findmnt -no SOURCE /)"
  parent="$(lsblk -no PKNAME "$root_src" 2>/dev/null || true)"
  [[ "$name" != "$parent" ]] || die "refusing ${name}: it holds this computer's root filesystem"
  log_ok "${name} looks like a removable disk ($(lsblk -dn -o SIZE "/dev/${name}"))"
}

linux_disk_bytes() {
  lsblk -dn -b -o SIZE "/dev/$1"
}

linux_write() {
  local name=$1 image=$2 bytes
  name="${name#/dev/}"
  bytes="$(linux_disk_bytes "$name")"
  [[ -n "$bytes" ]] || die "could not read the size of ${name}"
  disk_is_large_enough "$bytes" "$image"
  log_step "unmounting volumes on ${name}"
  while read -r mount; do
    if [[ -n "$mount" ]]; then
      sudo umount "$mount"
    fi
  done < <(lsblk -ln -o MOUNTPOINT "/dev/${name}")
  sudo -v
  log_step "writing ${image} to /dev/${name}"
  log_warn "this erases the card. The Retroid Pocket 5 internal storage is not attached to this computer."
  zstd -dc -- "$image" | sudo dd of="/dev/${name}" bs=4194304 status=progress conv=fsync
  sync
  log_ok "image written to ${name}"
  if [[ "$VISIONOX" -eq 1 ]]; then
    log_warn "on Linux, mount the POCKNIX partition and create an empty file named visionox next to KERNEL"
  fi
}

show_plan() {
  local dest cached
  dest="$CACHE/$POCKNIX_IMAGE"
  cat <<EOF
Pinned image
  version:   ${POCKNIX_VERSION}
  soc:       ${POCKNIX_SOC}
  file:      ${POCKNIX_IMAGE}
  url:       ${POCKNIX_URL}
  sha256:    ${POCKNIX_SHA256}

EOF
  if [[ -f "$dest" ]]; then
    cached="$(wc -c <"$dest" | tr -d ' ')"
    log_ok "cache present (${cached} bytes). Checksum is verified on --download or --confirm."
  else
    log_warn "image is not downloaded yet. Run: ./scripts/flash-sd.sh --download"
  fi
  echo
  case "$(uname -s)" in
    Darwin)
      require_cmd diskutil
      macos_list_disks
      ;;
    Linux)
      require_cmd lsblk
      linux_list_disks
      ;;
    *)
      die "flashing is supported on macOS and Linux"
      ;;
  esac
  cat <<'EOF'

Nothing was written.
Plug in the microSD, then:

  ./scripts/flash-sd.sh --device diskN --confirm

Use the whole-disk id from the list above. Add --visionox only for a 2026
12 GB Retroid Pocket 5 whose screen stays black on first boot.
EOF
}

if [[ "$CONFIRM" -eq 1 && -z "$DEVICE" ]]; then
  die "--confirm needs --device diskN. Run with no arguments to list disks."
fi

if [[ "$DOWNLOAD_ONLY" -eq 1 ]]; then
  require_cmd zstd
  ensure_image
  exit 0
fi

if [[ -z "$DEVICE" ]]; then
  show_plan
  exit 0
fi

require_cmd zstd
case "$(uname -s)" in
  Darwin)
    require_cmd diskutil
    DEVICE="$(normalize_disk "$DEVICE")"
    macos_assert_safe "$DEVICE"
    ;;
  Linux)
    require_cmd lsblk
    require_cmd findmnt
    DEVICE="${DEVICE#/dev/}"
    linux_assert_safe "$DEVICE"
    ;;
  *)
    die "flashing is supported on macOS and Linux"
    ;;
esac

if [[ "$CONFIRM" -ne 1 ]]; then
  log_warn "${DEVICE} passed the safety checks. Re-run with --confirm to erase and write it."
  exit 0
fi

preflight_capacity
ensure_image
case "$(uname -s)" in
  Darwin)
    macos_write "$DEVICE" "$CACHE/$POCKNIX_IMAGE"
    ;;
  Linux)
    linux_write "$DEVICE" "$CACHE/$POCKNIX_IMAGE"
    ;;
esac
