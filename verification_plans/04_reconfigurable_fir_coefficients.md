# 04 — Runtime-Reconfigurable FIR Coefficients

**Objective:** Make the FIR filter coefficients reloadable after the bitstream is programmed, using the Xilinx FIR Compiler coefficient-reload interface, controlled from PS/Linux (and ultimately exposed to the PC).

**Prerequisites:** Doc 02 (PS access path established). Filters are Xilinx FIR Compiler IP.

**Effort:** 1–2 days.

## Steps

1. **FIR Compiler config.** Enable **Coefficient Reload**; set the number of reloadable coefficient sets needed. This exposes a coefficient **reload** AXI4-Stream channel plus a **config** channel (selects/commits the active set). Note coefficient count, decimation, and coefficient fixed-point width.

2. **Control path PS → reload channel.** Bridge the PS to the reload/config AXI4-Stream channels — e.g., a small AXI-Lite-to-Stream shim or a dedicated AXI DMA MM2S into the reload channel. Reuse existing AXI infrastructure where possible.

3. **Coefficient format.** Generate coefficients (Python/scipy) → quantize to the FIR Compiler's coefficient width/format → order them as the reload channel expects (the IP may require a specific/reversed order). Document the packing exactly — a wrong order produces a valid-looking but wrong response.

4. **Reload sequence.** Stream the new coefficients into the reload channel, then send the config packet to commit the set. Observe the IP's reload handshake and latency. Decide whether to flush/quiesce streaming data during reload to avoid a transient on in-flight samples.

5. **Linux interface.** Userspace utility (or IOCTL) to push a coefficient set by index/name. Later, expose the same control over the Ethernet channel so the PC can switch filters live.

6. **Verify.** Load two distinct filters (e.g., different cutoff) at runtime and confirm the measured frequency response changes accordingly, using the doc 03 validation setup.

## Acceptance criteria
- At least two coefficient sets loadable at runtime without re-flashing.
- Measured response matches each loaded set.
- No corruption of the live stream during/after reload (or a known, bounded transient).

## Risks & gotchas
- **Coefficient ordering/format mismatch** — silently wrong response, not an error.
- Reload-vs-config **channel sequencing** (load before commit).
- Reload during streaming causing a glitch/transient.
- Bit-growth/scaling changing between sets if coefficient magnitudes differ.

## Open decisions
- Which filters are reloadable (CIC-compensation FIR, per-channel FIRs, both).
- PS→reload transport (AXI-Lite-to-Stream shim vs AXI DMA).
- Whether coefficient sets are precompiled on the PC or generated on-target.
