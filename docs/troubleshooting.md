# Troubleshooting

The dashboard says `offline` when llama-server is not answering `127.0.0.1:8081/health`. The management `/health` endpoint can still be ok. Install the llama.cpp binary before expecting `online`.

The setup code is on the local dashboard and in `/var/lib/rp5-llm/setup-code` (mode 0600). A browser that opens the LAN address, even on the Pocket, is not loopback and will not receive the code. Use `http://127.0.0.1:8080/`.

A black screen on a 2026 12 GB unit may be the Visionox panel. Recreate the card with `--visionox`, or add an empty `visionox` file beside `KERNEL` on the `POCKNIX` partition.

If the first boot seems stuck on the Pocknix logo, leave it. First start from an SD card is slow.

`scripts/flash-sd.sh` will not write without `--device` and `--confirm`. If it refuses the disk, the disk is internal, virtual, or not the whole card.

To drop the dashboard without deleting models or history:

```bash
sudo ./scripts/uninstall-ui.sh
```
