# Web installer

A normal SD card reader is a USB mass-storage device. WebUSB treats interface class `0x08` (mass storage) as a protected class, and Chrome does not offer those interfaces to a page. The File System Access API can save a file the user picks. It does not open the raw block device. WebSerial only reaches serial ports.

Because of that:

- A page on this site cannot flash the Pocknix image.
- There is no browser flashing prototype in this repository.
- The supported write path is [Installation](flashing.md): Etcher, or `scripts/flash-sd.sh` after the checksum check.

A future native helper could wrap the same pinned image. It is not required for the dashboard, and it is not part of this milestone.

What the browser can do, after Linux is already running, is the [setup wizard](web-setup.md).
