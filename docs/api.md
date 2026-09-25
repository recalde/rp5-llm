# API

The management process defaults to `127.0.0.1:8080`. OpenAPI is published at `/docs` only while that bind is loopback.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Management process is up. `llama` may still be `offline`. |
| GET | `/api/status` | Dashboard payload. Includes `setupCode` for loopback clients during setup. |
| GET | `/api/hardware` | Detected hardware and pass/warn checks. |
| GET | `/api/model` | Selected manifest entry. |
| GET | `/api/metrics` | Totals from the history database and the active request count. |
| GET | `/api/requests` | Recent metadata. No prompt or response text. |
| GET | `/api/config` | Non-secret configuration. |
| GET | `/api/setup/session` | Sets the CSRF cookie. |
| GET | `/api/setup/options` | Models and backends. |
| GET | `/api/setup/check` | Same checks the wizard shows. |
| POST | `/api/setup/install` | Validates and saves a plan. |
| POST | `/api/setup/complete` | Locks install. |
| POST | `/api/setup/unlock` | Loopback only. Body must be `{"confirm":"unlock"}`. |
| * | `/v1/*` | Forwarded to llama-server. |

Setup posts require the CSRF cookie echoed in `X-CSRF-Token` and the device code in `X-Setup-Code`. After setup is complete, install returns 403.

`/api/config` does not accept writes. Change settings through the setup plan.

Example status:

```json
{
  "status": "online",
  "device": "Retroid Pocket 5",
  "ip": "192.168.1.100",
  "model": "example.gguf",
  "backend": "cpu",
  "uptimeSeconds": 4217,
  "requests": { "total": 124, "active": 0 }
}
```

`device` is "Retroid Pocket 5" only when the detected model string says so. On any other machine the detected model is shown instead.
