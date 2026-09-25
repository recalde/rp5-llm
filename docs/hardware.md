# Hardware

The Pocket this project targets is a Retroid Pocket 5: Snapdragon 865 / SM8250, Adreno 650, and a 1920×1080 panel. RAM size is measured at runtime. Do not assume 8 GB.

`scripts/detect-hardware.sh` prints the live architecture, device model, CPU count, and RAM. Network addresses are left out of that report. The dashboard reads the LAN address separately so the screen can show it.

Vulkan, when present, comes from Mesa Turnip. A detected Vulkan driver is not treated as faster than CPU. That comparison waits for a recorded benchmark.

Newer 2026 12 GB units may use a Visionox panel. Pocknix selects it with an empty `visionox` file on the small `POCKNIX` partition. `scripts/flash-sd.sh --visionox` creates that file. Support is still untested on that panel.
