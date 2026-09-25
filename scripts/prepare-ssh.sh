#!/usr/bin/env bash
# Install this Mac's SSH public key on the Retroid Pocket 5 and print a Cursor host block.
# The device must already be on Wi-Fi with SSH turned on in Pocknix Tools.
# Password login is left enabled. Turn it off only after key login works.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/log.sh
source "$ROOT/scripts/lib/log.sh"

TARGET=""
ALIAS="rp5"
KEY=""
WRITE_CONFIG=0

usage() {
  cat <<'EOF'
Usage: ./scripts/prepare-ssh.sh deck@DEVICE_IP [--write-config] [--alias rp5] [--key PATH]

Copies your public key to the device with ssh-copy-id, checks that key login works,
and prints an ~/.ssh/config host block for Cursor Remote SSH.

--write-config appends that block when the alias is not already present.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --write-config)
      WRITE_CONFIG=1
      shift
      ;;
    --alias)
      [[ $# -ge 2 ]] || die "--alias needs a name"
      ALIAS=$2
      shift 2
      ;;
    --key)
      [[ $# -ge 2 ]] || die "--key needs a private key path"
      KEY=$2
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown argument: $1"
      ;;
    *)
      if [[ -n "$TARGET" ]]; then
        die "unexpected argument: $1"
      fi
      TARGET=$1
      shift
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  usage >&2
  die "pass the device as deck@IP"
fi

if [[ "$TARGET" != *@* ]]; then
  TARGET="deck@${TARGET}"
fi

command -v ssh >/dev/null 2>&1 || die "ssh is not installed"
command -v ssh-copy-id >/dev/null 2>&1 || die "ssh-copy-id is not installed"

if [[ -z "$KEY" ]]; then
  if [[ -f "$HOME/.ssh/id_ed25519" ]]; then
    KEY="$HOME/.ssh/id_ed25519"
  elif [[ -f "$HOME/.ssh/id_rsa" ]]; then
    KEY="$HOME/.ssh/id_rsa"
  else
    die "no SSH key found. Create one with: ssh-keygen -t ed25519 -C rp5-llm"
  fi
fi

if [[ "$KEY" == *.pub ]]; then
  PUB="$KEY"
  KEY="${KEY%.pub}"
else
  PUB="${KEY}.pub"
fi

[[ -f "$KEY" ]] || die "private key not found: $KEY"
[[ -f "$PUB" ]] || die "public key not found: $PUB"

case "$ALIAS" in
  *[!A-Za-z0-9._-]*)
    die "alias must contain only letters, numbers, dots, underscores, and hyphens"
    ;;
esac

USER_NAME="${TARGET%@*}"
HOST_NAME="${TARGET#*@}"

log_step "copying ${PUB} to ${TARGET}"
log_warn "ssh-copy-id will ask for the device password. Root SSH stays disabled."
ssh-copy-id -i "$PUB" -o StrictHostKeyChecking=accept-new "$TARGET"

log_step "checking key login"
ssh \
  -i "$KEY" \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o ConnectTimeout=10 \
  -o StrictHostKeyChecking=accept-new \
  "$TARGET" \
  'uname -sm; mkdir -p "$HOME/workspaces/rp5-llm"'

log_ok "key login works for ${TARGET}"

BLOCK="$(cat <<EOF

# rp5-llm Retroid Pocket 5
Host ${ALIAS}
  HostName ${HOST_NAME}
  User ${USER_NAME}
  IdentityFile "${KEY}"
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 4
EOF
)"

printf '%s\n' "$BLOCK"

CONFIG="$HOME/.ssh/config"
if [[ "$WRITE_CONFIG" -eq 1 ]]; then
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
  if [[ -f "$CONFIG" ]] && grep -Eq "^[[:space:]]*Host[[:space:]]+${ALIAS}([[:space:]]|\$)" "$CONFIG"; then
    log_warn "Host ${ALIAS} is already in ${CONFIG}; left it unchanged"
  else
    touch "$CONFIG"
    printf '%s\n' "$BLOCK" >>"$CONFIG"
    log_ok "appended Host ${ALIAS} to ${CONFIG}"
  fi
else
  log_warn "not written to ${CONFIG}. Re-run with --write-config to append it."
fi

cat <<EOF

Next, from this Mac:

  ssh ${ALIAS} 'git clone https://github.com/recalde/rp5-llm.git ~/workspaces/rp5-llm'

In Cursor: Remote-SSH, connect to ${ALIAS}, and open ~/workspaces/rp5-llm.
Then on the device: sudo ./scripts/bootstrap.sh
EOF
