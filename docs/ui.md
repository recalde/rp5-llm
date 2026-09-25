# Dashboard

The screen at `/` is built for a 1920×1080 landscape panel: large type, high contrast, and a dark background. It polls `/api/status` on the device. It does not load fonts or scripts from the network.

The screen shows status, model, backend, LAN address, API base, uptime, call counts, the last request time, and that request's token counts. A Requests button lists recent metadata. Prompts and replies are not on that list.

Kiosk mode is off unless `RP5_UI_KIOSK=true` and `rp5-llm-kiosk.service` is enabled. The script looks for Chromium or Firefox and opens `http://127.0.0.1:8080/`. If no browser is installed it exits without stopping SSH or the rest of the desktop. Treat the kiosk unit as experimental on Pocknix until it has been confirmed on hardware.

`sudo ./scripts/uninstall-ui.sh` removes the service and leaves request history in place. `--purge-state` deletes `/var/lib/rp5-llm` as well.
