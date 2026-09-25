# Agent rules

This repository builds a local LLM appliance on a Retroid Pocket 5. The long-term design is in `PROJECT_GUIDANCE.md`. These rules override convenience.

The Linux system is upstream [Pocknix](https://github.com/shuuri-labs/pocknix-os) on a microSD card. Do not fork Pocknix or add a custom image build. `scripts/flash-sd.sh` downloads the pinned image in `image/upstream.env` and writes it only when `--device` and `--confirm` are both present.

## Do not

- Modify Android partitions, repartition internal UFS, or flash a bootloader. The stock boot menu is how the device selects the SD card. Upstream's optional ROCKNIX ABL installer is out of scope.
- Let a script pick a disk by itself, or write a disk without `--confirm`.
- Assume the device has 8 GB of RAM. Measure it.
- Bind the inference API to anything except `127.0.0.1` unless LAN access is an explicit, documented option.
- Commit model weights, image files, `image/cache/`, SSH private keys, tokens, or generated hardware reports that include a home network.
- Disable SSH password login until key login has been checked.
- Treat Vulkan as faster than CPU without a recorded benchmark. CPU inference has to work first.

## Do

- Keep installer steps safe to run twice.
- Put runtime files in `/opt/rp5-llm`, `/var/lib/rp5-llm`, and `/etc/rp5-llm`, not only in the git checkout.
- Leave an uninstall or rollback path for anything the installer changes.
- Prefer an upstream Pocknix mechanism over a device-specific workaround.
- Develop on the device over SSH (`scripts/prepare-ssh.sh`, then Cursor Remote SSH). Avoid cross-compilation unless a native build is impractical.
