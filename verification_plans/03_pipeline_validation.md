# 03 — Demod Pipeline Validation with Real Lab Data + PC Plotting

**Objective:** Confirm the lock-in demodulation (CIC + FIR + CORDIC) reports correct magnitude and phase end-to-end, driven by real lab-generated input, plotted near-real-time on the PC.

**Prerequisites:** Doc 02 (verified data path to PC). Demod already verified in simulation (1/5/10/20 kHz) and in hardware at 1 kHz — this extends it to the 500 kHz–20 MHz operating band.

**Effort:** 1–2 days.

## Steps

1. **Define how real data enters.** If the custom PCB analog chain isn't up yet, inject digitized lab data into the demod front-end one of two ways:
   - Lab signal generator → ADC → FPGA (live), or
   - Pre-captured lab dataset replayed into the processing chain.
   Pick one and document the injection point so results are reproducible.

2. **Reference values.** For a known stimulus (single tone at `f` in band, known amplitude/phase, known load model), compute expected lock-in I/Q, magnitude (post-CORDIC), and phase analytically / in Python. This is the same demod math you simulated at kHz, now evaluated at MHz.

3. **Frequency sweep.** Step `f` across 500 kHz–20 MHz. Verify magnitude follows the expected response and phase is accurate. Check CIC/FIR passband behavior and the CORDIC magnitude scaling factor at the high end.

4. **Near-real-time PC plot.** Consume the UDP stream from doc 02 and plot magnitude/phase (and raw I/Q) vs time and frequency. Tool choice open — favor a high-update-rate plotter (e.g., PyQtGraph) over matplotlib if the rate is high.

5. **Integrity checks.** No saturation/overflow in the fixed-point datapath at MHz; correct fixed-point scaling; correct frequency-channel→value mapping; `seq_num`/timestamps consistent with what's plotted.

6. **Cross-check (secondary).** Same stimulus/load on the MFIA; compare magnitude/phase to bound systematic error. Primary goal remains correctness against real sample data.

## Acceptance criteria
- FPGA magnitude and phase match the reference within a defined tolerance across the band.
- PC plot updates near-real-time and is stable at the target rate.
- No overflow/saturation; scaling and channel mapping correct.
- MFIA cross-check consistent where used.

## Risks & gotchas
- Fixed-point **scaling/overflow** differences between kHz (validated) and MHz operation.
- Uncompensated **CIC droop** across the band.
- **CORDIC gain** factor not applied/normalized.
- **CDC** between the 200 MHz sample domain (PCB clock) and the processing/AXI clock.
- Anti-alias assumptions differing from the actual filter once the PCB is in the loop.

## Open decisions
- Real-data injection method (live ADC vs replay).
- PC plotting stack and target update rate.
- Pass/fail tolerance for magnitude and phase.
- Number of simultaneous frequencies exercised here (multifrequency is lower priority — single-tone is fine for first validation).
