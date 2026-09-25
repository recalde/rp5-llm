# First boot

Power the Pocket off, insert the card, and hold **Volume Down** while powering on. Volume keys move. Power selects. Switch the stock boot menu off Android so the card starts. This project does not install the optional ROCKNIX bootloader.

The first Steam session from an SD card can sit on the Pocknix logo for a long time. That wait is normal. To return to Android, use the same menu and switch the boot mode back.

## Wi-Fi and SSH

Pocknix leaves SSH off until you turn it on. Change the public default password in Konsole with `passwd` before enabling SSH. In **Pocknix Tools**, choose the remote-access entry. The account is `deck`. Root SSH stays disabled.

## Putting the dashboard on the card

macOS cannot mount Pocknix's btrfs root, so a Mac cannot inject these files before the first boot. Two supported ways remain:

- On the booted Pocket, unpack a project release or clone the repo, then run `sudo ./scripts/install-ui.sh`.
- On a Linux computer that has already mounted the Pocknix root, run `./image/firstboot/firstboot.sh --root /mnt/pocknix`.

`--root /` is refused. The script copies files and enables the dashboard unit inside that directory. It does not call `dd`, and it does not change a bootloader.

`sudo ./image/firstboot/firstboot.sh` with no `--root` is the on-device form of the same install.
