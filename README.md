# rp5-llm

Local LLM appliance for a Retroid Pocket 5. Android stays on the internal storage. Linux is upstream [Pocknix](https://github.com/shuuri-labs/pocknix-os) on a microSD card. This repo does not build a custom image: it downloads a pinned Pocknix release, checks the published checksum, and writes that file to the card. Setup after boot is finished over SSH from Cursor.

The design notes are in [PROJECT_GUIDANCE.md](PROJECT_GUIDANCE.md).

## What you need

- Retroid Pocket 5
- microSD card, 128 GB recommended, 64 GB minimum
- A Mac or Linux computer to write the card
- `zstd` (`brew install zstd` on a Mac)
- An SSH key (`ssh-keygen -t ed25519 -C rp5-llm` if you do not have one)

The flash script refuses the computer's internal disk. It does not see the Pocket's internal storage, and it does not install a bootloader.

## 1. Flash the microSD card

From this repo:

```bash
./scripts/flash-sd.sh
./scripts/flash-sd.sh --download
./scripts/flash-sd.sh --device diskN --confirm
```

The first command only prints the pinned image and the external disks it can see. `diskN` is the whole card from that list (`disk4`, not `disk4s1`). On Linux, pass the whole-disk name (`sda` or `mmcblk0`).

`--download` fetches about 10.5 GB into `image/cache/`, which git ignores, and checks it against the checksum published for the pin in `image/upstream.env`. The current pin is Pocknix **v0.4.0**, `pocknix-sm8250-20260912-sd.img.zst`.

`--confirm` is what erases the card. Without it, nothing is written. `make flash-plan` and `make download` are the same first two steps.

A GUI flasher such as Balena Etcher can write that same cached `.img.zst` if you would rather not use `dd`. Still run `--download` first so the checksum is checked.

### 2026 12 GB units (Visionox panel)

Some 2026 Retroid Pocket 5 units use a Visionox panel. Pocknix cannot tell it apart from the older panel before the display driver loads, so the first boot can stay black. Support is in the image and is still untested on hardware. Add `--visionox` to the write command:

```bash
./scripts/flash-sd.sh --device diskN --confirm --visionox
```

That creates an empty file named `visionox` next to `KERNEL` on the small `POCKNIX` partition. To do it by hand, mount that partition after writing and create the same empty file.

## 2. Boot Pocknix

Android is left in place. This project does not copy `rocknix_abl` or run `flash_abl.sh`. Upstream documents that bootloader install as optional; SM8250 devices can boot the card from the stock menu.

1. Power the Pocket off and insert the card.
2. Hold **Volume Down** while powering on. Volume keys move through the menu. Power selects.
3. Switch the boot mode off Android so the device boots from the SD card.
4. Leave the first boot alone. From an SD card, the Steam session can sit on the Pocknix logo for a long time. That wait is normal.

To get back to Android, open the same menu and switch the boot mode back. You do not have to wipe the card to do that.

## 3. Wi-Fi, password, SSH

Pocknix **v0.3 and later leave SSH off** until you turn it on. The default password is `pocknix`, and it is public. Change it before enabling SSH.

1. Use the power button to switch from the Steam session to the Plasma Mobile desktop.
2. Connect to Wi-Fi in the system settings.
3. Open Konsole and run `passwd`.
4. Open **Pocknix Tools** and choose **Remote access (SSH) is off - turn it on...**
5. The dialog prints the account name and the IP address. The image's account is `deck`. Root login over SSH is disabled and stays disabled.

## 4. Connect from Cursor

On the Mac, after SSH is on:

```bash
./scripts/prepare-ssh.sh deck@DEVICE_IP --write-config
```

`ssh-copy-id` asks for the password you just set, then the script checks that key login works and appends a `Host rp5` block to `~/.ssh/config`. A template is in `ssh/config.example`. Password login is left on until that key check succeeds.

Clone the repo onto the device and open it in Cursor:

```bash
ssh rp5 'git clone https://github.com/recalde/rp5-llm.git ~/workspaces/rp5-llm'
```

In Cursor, run **Remote-SSH: Connect to Host** and choose `rp5`. Open `~/workspaces/rp5-llm`. The first connection installs Cursor's remote server on the device; that can take a few minutes.

## 5. Bootstrap

On the device:

```bash
cd ~/workspaces/rp5-llm
sudo ./scripts/bootstrap.sh
```

Today this records the live hardware and creates `/opt/rp5-llm`, `/var/lib/rp5-llm`, and `/etc/rp5-llm`. It is safe to run again. It does not install llama.cpp, download a model, or change boot settings. Those steps are the work to finish over SSH. CPU inference comes before any Vulkan attempt.

Running the same command on the Mac only prints a hardware report. It does not create those directories unless it is actually on aarch64 Linux.

## Updating later

An installed Pocknix system updates with its own updater or `sudo pacman -Syu`. A new SD image is for a fresh card, or when upstream says a reflash is required. When that happens, update every field in `image/upstream.env` together, using the checksum from the [Pocknix release](https://github.com/shuuri-labs/pocknix-os/releases/latest).
