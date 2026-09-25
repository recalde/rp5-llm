# Benchmarking

No benchmark is shipped as a winner. CPU is the supported path until prompt and generation speeds are recorded for this hardware.

When a comparison exists, keep CPU as a fallback. A Vulkan result has to include the model, quantization, context size, backend, and token rates before the wizard's auto choice should prefer it. That choice is not wired to a results file yet. `auto` stays on CPU.

Results, once measured on a device, can live under `benchmarks/results/` and be summarized here. They are not invented in advance.
