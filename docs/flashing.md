# Installation

The card is an upstream Pocknix SM8250 image. This repository pins the file, URL, and checksum in `image/upstream.env`.

From a checkout:

```bash
./scripts/flash-sd.sh
./scripts/flash-sd.sh --download
./scripts/flash-sd.sh --device diskN --confirm
```

The first command lists external disks and writes nothing. `--confirm` is what erases the card you named. The script refuses the computer's internal disk. It never sees the Pocket's internal storage.

Balena Etcher can write the same cached `.img.zst` after `--download` has checked the checksum.

`--visionox` is only for a 2026 12 GB unit whose screen stays black on first boot. It creates an empty `visionox` file next to `KERNEL` on the `POCKNIX` partition.

A browser cannot do this write. See [Web installer](web-installer.md).
