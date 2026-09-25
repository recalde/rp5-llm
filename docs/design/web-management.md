# Web management design

This document is the decision record for the on-device status UI, the documentation site, and browser-based provisioning. `PROJECT_GUIDANCE.md` and `AGENTS.md` still govern safety. The flash script, hardware detector, and bootstrap script stay the way they are.

## Current baseline

Already in the repo:

- pinned upstream Pocknix image and `scripts/flash-sd.sh`
- `scripts/detect-hardware.sh`
- `scripts/bootstrap.sh`, which only records hardware and creates runtime directories
- `scripts/prepare-ssh.sh` for Cursor Remote SSH
- README operator notes

Not in the repo yet, and not invented here as if they already worked:

- llama.cpp build, model download, or a running `llama-server`
- a Vulkan-vs-CPU benchmark result
- a custom disk image

CPU inference remains the required baseline. Vulkan stays a configured choice, not an assumed win.

## 1. Architecture

One management process sits beside llama.cpp. It does not run a model.

```text
browser or OpenAI client
        │
        ▼
rp5-llm management process  (default 127.0.0.1:8080)
        │
        ├── static dashboard and setup wizard
        ├── /api/* status, hardware, metrics, history, config
        ├── /v1/*  thin gateway
        │
        ▼
llama-server  (127.0.0.1:8081, never bound to the LAN)
```

`llama-server` stays responsible for inference. The gateway forwards `/v1/*` and records metadata. Prometheus `/metrics` on llama.cpp is aggregate and off unless `--metrics` is set. `/slots` can contain prompt text, so the history store does not scrape it.

Ports:

| Listener | Bind | Role |
|---|---|---|
| Management, dashboard, gateway | `127.0.0.1:8080` unless LAN exposure is explicitly enabled | What people open |
| `llama-server` | `127.0.0.1:8081` always | Inference only |

`RP5_LLM_BIND` and `RP5_LLM_PORT` remain the public management address. `RP5_LLM_LLAMA_URL` is the upstream. Enabling LAN access restarts the management process on `0.0.0.0`. It does not move llama.cpp.

Runtime files stay in `/opt/rp5-llm`, `/var/lib/rp5-llm`, and `/etc/rp5-llm`.

## 2. Processes

```text
boot
  │
  ├─ rp5-llm.service
  │    llama-server
  │    installed disabled until the binary exists
  │    ConditionPathExists=/opt/rp5-llm/bin/llama-server
  │
  ├─ rp5-llm-ui.service
  │    dashboard, status API, gateway
  │    this is the process the browser talks to
  │
  ├─ rp5-llm-setup.service
  │    oneshot, root
  │    reads a validated plan and applies a fixed set of changes
  │    not a shell API
  │
  └─ rp5-llm-kiosk.service
       optional, disabled unless RP5_UI_KIOSK=true
       opens http://127.0.0.1:8080/ in a local browser
       SSH and the rest of the desktop stay available
```

The HTTP process writes a plan. The setup oneshot is the only root applier, and it only understands hostname, one SSH public key, backend, LAN flag, kiosk flag, and a checksummed model file. The UI service does not grow an `exec` endpoint.

Kiosk mode is off by default. The unit is experimental on Pocknix because the browser package and Wayland flags still have to be confirmed on hardware. If no browser is installed, the script exits without crashing boot.

## 3. Request tracing

llama.cpp's OpenAI-compatible responses already include a `usage` object. The gateway reads token counts from that object and throws the rest away.

Recorded fields:

```text
timestamp, request id, source IP, model, backend,
prompt tokens, generated tokens, duration, tokens/sec,
success/failure, HTTP status
```

Storage is SQLite at `/var/lib/rp5-llm/history.sqlite`. Retention is whichever bound is hit first: `RP5_LLM_HISTORY_LIMIT` (default 1000) and `RP5_LLM_HISTORY_DAYS` (default 7).

Prompt and response bodies are not stored. `RP5_LLM_CAPTURE_CONTENT=true` is the only switch that keeps them, and even then each field is capped. The gateway does not trust `X-Forwarded-For` from a non-loopback peer.

Streaming responses are forwarded chunk by chunk. The gateway keeps the current SSE event long enough to read `usage`, not the conversation.

`/metrics` on llama.cpp can be added later for aggregate throughput. It is not the history log.

## 4. Security model

- Management listens on loopback until a saved plan sets `exposeLan` and the process is restarted.
- llama.cpp always listens on loopback.
- Setup mutations need a CSRF cookie echoed in `X-CSRF-Token`, plus the setup code.
- The setup code is shown to loopback clients (the kiosk opens `http://127.0.0.1:8080/`) and stored mode `0600` on disk. A laptop on the LAN has to read it off the handheld screen.
- After setup is marked complete, plan and install routes return 403. Unlock requires loopback, the code, CSRF, and the confirmation string `unlock`.
- SSH input must be one OpenSSH public key. `PRIVATE` and PEM armor are rejected.
- Model ids have to exist in `config/models.yaml`. Download runs only when that entry has a sha256, and the file is renamed into place only after the hash matches.
- Hostname changes are a fixed `hostnamectl set-hostname` argument list, and only when `RP5_LLM_ALLOW_HOST_CHANGES=true` on the setup oneshot.
- No endpoint accepts a shell command, a private key, or an internal-storage operation.
- OpenAPI is served only while the management bind is loopback.

## 5. Setup wizard

The wizard is static HTML on the same process, at `/setup`. It calls the explicit routes below. It does not talk to llama.cpp directly.

```text
GET  /api/setup/session     CSRF cookie
GET  /api/setup/check       Linux, storage, network, Vulkan, temperature
GET  /api/setup/options     models and backends from the manifest
POST /api/setup/install     validate and save the plan, return step results
POST /api/setup/complete    lock privileged routes
POST /api/setup/unlock      local unlock
```

Steps the wizard can finish now: hardware report, writing configuration, queueing an SSH key and hostname for the setup oneshot.

Steps that stay honest about missing pieces: llama.cpp is not built by this tree yet, and a model with an empty checksum is not downloaded. Those steps come back `blocked` rather than a fake pass. CPU is the default backend. `auto` stays on CPU until a benchmark file names a winner. Vulkan is selectable and labeled experimental.

Default API exposure is local. The wizard explains that LAN exposure publishes the gateway, not a private llama.cpp port.

## 6. GitHub Pages

Markdown under `docs/` is the site source. MkDocs Material builds it. The workflow uploads the built `site/` directory with `actions/upload-pages-artifact` and publishes it with `actions/deploy-pages` into the `github-pages` environment. Generated HTML is not committed.

`make docs` and `make docs-serve` are for people changing the docs. Flashing an SD card does not require them.

The home page states the project and points at upstream Pocknix's latest release for the image, plus this repo's latest GitHub release when one exists. Versioned image filenames stay in `image/upstream.env`, which is what `scripts/flash-sd.sh` verifies.

The repository Pages setting has to be "GitHub Actions" before the first deploy succeeds.

## 7. Browser SD flashing

A normal SD reader enumerates as USB mass storage, interface class `0x08`. The WebUSB specification treats that class as protected, and Chrome hides those interfaces from pages. The File System Access API can save a file the user picks. It does not open the raw block device. WebSerial only talks to serial ports.

So:

| Option | Decision |
|---|---|
| A. Flash the card from the browser | Not feasible for a commodity SD reader |
| B. Site explains the download, checksum, and Etcher or `scripts/flash-sd.sh` | This is the supported path |
| C. A small native flasher | Not built |

There is no browser flashing prototype. `docs/web-installer.md` is the short version of this finding. Isolated Web Apps can request unrestricted USB, and Chrome's own recovery tool uses an extension. Neither is a path for a public documentation site.

## 8. Implementation phases

| Phase | What landed | What it does not do |
|---|---|---|
| 1 | `/api/status`, `/health`, hardware, model, metrics, config | llama.cpp itself |
| 2 | Dashboard at `/` | Kiosk on by default |
| 3 | SQLite history and the `/v1` gateway | Prompt logging |
| 4 | MkDocs and the Pages workflow | Enabling Pages in the repo settings |
| 5 | Setup wizard and the root oneshot | Downloading an unchecksummed model |
| 6 | `image/firstboot/firstboot.sh` copies files into a root the operator names | Forking Pocknix, or mounting a btrfs root from macOS |
| 7 | Flashing feasibility written down | |
| 8 | Skipped | A browser raw-device writer |

Preserved on purpose: `scripts/flash-sd.sh` still requires `--device` and `--confirm`, bootstrap still refuses to create system directories on a non-aarch64 host, and nothing in this milestone touches Android, internal UFS, or a bootloader.
