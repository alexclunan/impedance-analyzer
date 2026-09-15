---
name: full-design-bd-known-nonissues
description: full_design.bd block design — design intents that look like bugs but are not
metadata:
  type: project
---

In the Vivado block design `full_design.bd`, two things look like wiring errors on review but are intentional — do NOT flag them again:

- **`dac_output_wrapper_0/dac_data_y` (and `dac_data_valid`) unconnected**: the DAC IP/wrapper was created with extra pins that aren't all used. Only `dac_data_x` drives the DAC DDR bus (`ilconcat_0` + `ilconstant_1`). By design.
- **ADC SelectIO (`adc_input`) capture clock vs FCLK_CLK0**: `adc_input` captures on the forwarded `adc_diff_clk`, and its parallel output feeds FCLK_CLK0-domain logic with no CDC synchronizer. Not a true async crossing — the ADC is driven from the same clock that will eventually drive the FPGA fabric clock. (May still warrant care, per the user, but not treated as a bug.)

**Why:** Avoid re-reporting these on future block-design reviews.
**How to apply:** When auditing `full_design.bd`, skip these two; focus elsewhere.

Real bugs found in the same review (since fixed by the user): `mag_phase_calc_nreset_13` ilslice was on bit 12 instead of 13 (dup of `DAC_nreset_12`); `SPI1_MOSI_O` had no DAC data path; `ilslice_1` `DIN_WIDTH=63` vs 64-bit timestamp source.
