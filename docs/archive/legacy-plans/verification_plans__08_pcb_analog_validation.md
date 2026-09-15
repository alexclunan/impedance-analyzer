# 08 — Analog Signal-Chain Validation (DAC → Load → ADC → Real Samples)

**Objective:** Validate the full analog chain on the custom PCB and the end-to-end measurement, first on known loads, then on real lab sample data. MFIA is a secondary cross-check; real sample data is the primary goal. This is the convergence point of both tracks.

**Prerequisites:** Doc 07 (PCB configured, ADC link verified) and doc 03 (readout pipeline). Signal chain: DAC9122 → buffer → SMA → sensor/load → diff TIA → diff op-amp → LMH6881 PGA → LC Bessel anti-alias → AD9467.

**Effort:** 1–2 days.

## Steps

1. **Stage-by-stage bring-up (scope), low-risk stimulus first.** With a known load (start with a plain resistor), probe each stage and confirm level/shape, no clipping or oscillation:
   - DAC output at buffer/SMA (amplitude, frequency).
   - TIA output → diff op-amp → PGA output → anti-alias filter output.

2. **Digital readout — DAC → load → ADC.** With the ADC capturing (doc 07) and the demod pipeline running (doc 03), the reported magnitude/phase should match the known load:
   - **Resistor** validates the **magnitude** path (≈0° phase).
   - **RC network** validates **phase** across the 500 kHz–20 MHz band (a bare resistor won't exercise phase).

3. **Sweep on known loads.** Step frequency across the band; compare measured |Z| and phase against the analytic model; quantify error.

4. **MFIA cross-check (secondary).** Same load on the MFIA; compare to bound systematic/fixture error.

5. **Real sample data (primary).** Introduce actual lab samples. Confirm the system produces repeatable, physically-sensible impedance magnitude/phase, and sanity-check against expected sample behavior.

6. **Optional calibration.** If accuracy needs it, run an open/short/load sequence to de-embed fixture parasitics.

## Acceptance criteria
- Every analog stage verified clean on the scope.
- Known-R magnitude and known-RC phase match the model within tolerance.
- MFIA cross-check consistent where used.
- Real samples produce repeatable, sensible measurements end-to-end.

## Risks & gotchas
- Clipping/saturation anywhere in the chain (wrong PGA gain, DAC level too high).
- Anti-alias filter response differing from assumptions used in demod (ties to doc 03).
- Phase error from cabling/fixture at MHz; ground/SI issues.
- ADC full-scale vs chain output level mismatch.
- Demod fixed-point scaling (doc 03) showing up as a magnitude offset here.

## Open decisions
- Known load values (R and RC).
- Real sample types and handling.
- Tolerance targets for |Z| and phase.
- Whether OSL calibration is needed for the accuracy you want.
