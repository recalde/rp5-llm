# Getting started

You need a Retroid Pocket 5, a microSD card (128 GB recommended, 64 GB minimum), and a computer that can write the card. You do not need Cursor or a local clone to read these pages. Writing the card still uses a normal flasher, because a browser cannot raw-write an SD card. That limit is explained in [Web installer](web-installer.md).

1. Download the SM8250 image from the [latest Pocknix release](https://github.com/shuuri-labs/pocknix-os/releases/latest).
2. Write it with Balena Etcher, or with `scripts/flash-sd.sh` from a checkout. See [Installation](flashing.md).
3. Boot the Pocket from the card. See [First boot](first-boot.md).
4. Install the dashboard with `sudo ./scripts/install-ui.sh` once the files are on the device, or layer them with [firstboot](first-boot.md) from a Linux machine that can mount the root filesystem.
5. Open `http://127.0.0.1:8080/` on the device, or follow [Web setup](web-setup.md).

Developers who want a shell on the device use [Cursor over SSH](cursor-setup.md). That path is optional.

llama.cpp itself is not installed by the wizard yet. The dashboard will show the model as offline until that installer exists. CPU remains the baseline.
