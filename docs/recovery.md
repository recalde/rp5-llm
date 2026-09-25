# Recovery

Android is still on the internal storage. Hold **Volume Down** during power-on and switch the boot menu back to Android. You do not need to erase the SD card to do that.

If Linux itself is unusable, write the pinned Pocknix image again with [Installation](flashing.md). Then run bootstrap and `scripts/install-ui.sh`, or layer the files with `image/firstboot/firstboot.sh --root` from a Linux machine. Model weights are not in git, so a reflash does not restore them.

`scripts/uninstall-ui.sh --purge-state` deletes `/var/lib/rp5-llm`, including the request database and the setup plan. It does not repartition the Pocket or change the bootloader.

There is no supported path in this repository for installing Linux onto internal storage.
