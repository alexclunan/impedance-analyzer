# 07 — Device Config (SPI) + Clocking + SelectIO/XDC

**Objective:** Bring the PCB's 200 MHz clock into the FPGA, set up SelectIO/XDC matching the schematic (including swapped P/N pairs), and configure the ADC/DAC (and PGA) over SPI.

**Prerequisites:** Doc 06 (power verified, VCCO confirmed). PCB schematic / net-to-pin mapping.

**Effort:** 1–2 days.

## Steps

1. **Clock in.** Route the PCB 200 MHz clock to a clock-capable pin (MRCC/SRCC) on the appropriate bank. Add MMCM/PLL for any derived/processing clocks. Constrain with `create_clock`. **Verify the clock is present and clean before relying on it** (probe, or a clock-check counter toggling an LED / status register).

2. **Clock domains.** Define the 200 MHz ADC-sample domain and the CDC to the processing/AXI clock; add the timing constraints and CDC structures. (Same domain-crossing concern flagged in doc 03.)

3. **SelectIO / XDC.** Set I/O standards per the schematic (e.g., LVDS for the AD9467 data bus, LVCMOS for SPI/control) and assign pins.

4. **Swapped P/N handling.** Document each swapped pair and where it's corrected:
   - **Single-ended swapped nets:** just reassign the pin in the XDC.
   - **Differential pairs with swapped P/N:** you generally cannot freely swap P/N in the constraint — Xilinx pins the logical "P" to the master site of the pair. Correct the polarity by **inverting the bit in RTL** (or use the IP's pin-swap/polarity option). Note which pairs are inverted and where.

5. **SPI config.** Bring up SPI to the ADC, DAC, and PGA (LMH6881 gain). Under Linux the simplest master is **PS SPI via `spidev`** (alternatively a PL AXI Quad SPI). Write each device's config registers per datasheet and **read back to confirm**. Watch CPOL/CPHA/mode.
   - **AD9467:** set output format/mode; enable a **built-in test pattern** to validate the digital capture link *before* trusting real samples.
   - **DAC:** configure as required.
   - **LMH6881 PGA:** set gain.

6. **ADC link bring-up.** With the AD9467 in test-pattern mode, capture in the FPGA and verify bit alignment/deskew on the LVDS bus at 200 MHz. Add IDELAY/bitslip if the bits aren't aligned.

## Acceptance criteria
- 200 MHz clock verified present/clean (and MMCM/PLL locked if used).
- SPI register read-backs match what was written, for each device.
- ADC test pattern captured correctly over the real interface (no bit errors).
- All swapped pairs corrected and verified.

## Risks & gotchas
- **VCCO mismatch** (recheck against doc 06 before driving pins).
- **Diff P/N swap not corrected** → inverted/garbled data that looks plausible.
- Clock landed on a non-clock-capable pin.
- ADC interface **timing/alignment** at 200 MHz (need IDELAY/bitslip).
- Wrong SPI mode (CPOL/CPHA) → silent bad writes.

## Open decisions
- SPI master: PS `spidev` vs PL AXI Quad SPI.
- Exact I/O standards per net.
- Which pins/pairs are swapped (from schematic).
- ADC data interface type and exact capture rate.
