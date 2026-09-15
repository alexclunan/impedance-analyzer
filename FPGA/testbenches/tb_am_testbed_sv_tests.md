# Testbench Documentation: tb_am_testbed_sv

## DUT Summary

- **Module:** `am_testbed_sv`
- **Type:** complex generated block-design wrapper
- **Clock:** 200 MHz
- **Carrier:** 20 MHz DDS carrier using `fcw = 48'h1999_9999_999A`
- **AM stimulus:** unipolar Q1.15 sine envelope multiplied by `data_out_to_pins_0`, then driven into `adc_input`. The envelope is `0.50 + 0.45*sin(...)`, so it stays positive with headroom.
- **Debug probes:** `mixer_i`, `mixer_q`, `cic_i`, `cic_q`, `fir_i`, and `fir_q` are observed from the generated block internals so the testbench still works if the SV wrapper lags the block-design port list. `signal_out` is the upper 32 bits of the CORDIC output and `phase_out` is the lower 32 bits. The `sampled_*` waveform signals update on the matching stage valid signal.

## Ports

| Port | Direction | Width | Purpose |
|------|-----------|-------|---------|
| `clk` | input | 1 | 200 MHz block-design clock |
| `fcw` | input | 48 | DDS frequency control word for the phase accumulator |
| `reset_register` | input | 32 | Bit-sliced reset/control word for generated sub-blocks |
| `DAC_test_data` | input | 32 | DAC test-mode control and test data; held in normal DDS mode by this testbench |
| `fifo_delay` | input | 32 | Low 10 bits set the FIFO delay threshold before mixer processing |
| `adc_input` | input | 16 | Signed AM-modulated sample driven into the mixer ADC path |
| `data_out_to_pins_0` | output | 16 | DAC pin output used as the carrier source for AM stimulus |
| `phase_msb_0` | output | 1 | Phase accumulator MSB, used to confirm carrier activity |
| `timestamps` | output | 64 | Free-running timestamp counter output |
| `signal_out` | output | 32 | Magnitude CORDIC output after mixer and filters, sliced from raw CORDIC `[63:32]` |
| `phase_out` | output | 32 | Phase CORDIC output after mixer and filters, sliced from raw CORDIC `[31:0]` |
| `signal_out_valid` | output | 1 | Valid qualifier for `signal_out` measurements |
| `mixer_i` | debug output | 32 | Mixer I output feeding the CIC I input |
| `mixer_q` | debug output | 32 | Mixer Q output feeding the CIC Q input |
| `cic_i` | debug output | 32 | CIC I output feeding the FIR I input |
| `cic_q` | debug output | 32 | CIC Q output feeding the FIR Q input |
| `fir_i` | debug output | 48 | FIR I output feeding the magnitude/phase CORDIC cartesian input |
| `fir_q` | debug output | 48 | FIR Q output feeding the magnitude/phase CORDIC cartesian input |
| `sampled_mixer_*` | testbench debug | 32 | Held mixer I/Q values captured only on `mixer_valid` |
| `sampled_cic_*` | testbench debug | 32 | Held CIC I/Q values captured only on `cic_i_valid` or `cic_q_valid` |
| `sampled_fir_*` | testbench debug | 48 | Held FIR I/Q values captured only on `fir_i_valid` |
| `sampled_signal_*` / `sampled_phase_out` | testbench debug | mixed | Held signal, phase, raw CORDIC output, timestamp, sample index, ADC, and envelope values captured only on `signal_out_valid` |

## Test Inventory

### 1. Reset Values

- **Checks:** `Reset: phase_msb_0 is zero`, `Reset: timestamps is zero`
- **Scenario:** Hold the generated block in reset.
- **Expected behavior:** Phase and timestamp outputs are cleared.
- **Why included:** Confirms the bit-sliced reset register is driving the expected reset lines.

### 2. Carrier Activity

- **Checks:** `Timestamp: timestamps increments after reset release`, `20 MHz carrier: phase_msb_0 toggles during observation window`, `20 MHz carrier: data_out_to_pins_0 changes during observation window`, `20 MHz carrier: data_out_to_pins_0 is known`
- **Scenario:** Release resets, run with the 20 MHz carrier FCW, and observe carrier-related outputs.
- **Expected behavior:** Timestamp advances, phase MSB toggles, and DAC output changes without X/Z values.
- **Why included:** Verifies the carrier source is alive before using it as the AM carrier.

### 3. AM Model

- **Check:** `AM model: adc_input follows unipolar Q1.15 carrier-envelope product`
- **Scenario:** Compute one known unipolar Q1.15 carrier-envelope product and drive it into `adc_input`.
- **Expected behavior:** `adc_input` equals `(carrier * envelope) >>> 15`.
- **Why included:** Confirms the testbench's ADC stimulus model is the intended signed Q1.15 AM model.

### 4. Sine Envelope Measurements

- **Checks:** `Sine 1000 Hz: settling completed`, `Sine 1000 Hz: collected measurement samples`, and equivalent checks for `5000`, `10000`, `15000`, and `20000` Hz.
- **Scenario:** Drive unipolar sine-envelope AM at representative passband, cutoff, and above-cutoff modulation frequencies.
- **Expected behavior:** For each frequency, the testbench discards 128 valid output samples, collects 256 valid output samples, and prints the average 32-bit `signal_out` value.
- **Why included:** Characterizes the 10 kHz filter response with bounded runtime before hard pass/fail thresholds are defined. The first valid collected sample also prints `adc_input`, mixer, CIC, FIR, magnitude, and phase debug values to locate where the envelope stops matching expectation.
- **Waveform tip:** Use `sampled_mixer_*`, `sampled_cic_*`, `sampled_fir_*`, `sampled_signal_out`, and `sampled_phase_out` for stage-aligned views. Compare `sampled_envelope` against `sampled_signal_out`, not raw invalid-cycle CORDIC data.

## Functional Coverage

- Frequency points covered: `1 kHz`, `5 kHz`, `10 kHz`, `15 kHz`, `20 kHz`.
- Carrier point covered: `20 MHz` at `200 MHz` sample clock.
- Envelope format covered: unipolar Q1.15 from roughly 0.05 to 0.95 full-scale.

## Verification Gaps

- The filter response is logged but not threshold-checked in this first version.
- Exact `signal_out` scaling is not asserted; the testbench reports the saved-BD 32-bit `signal_out` slice.
- `signal_out` is post-CORDIC magnitude/phase data, so it should be compared to a delayed/scaled unipolar envelope response rather than the instantaneous pre-filter envelope.
- The one-cycle testbench feedback delay from `data_out_to_pins_0` sampling to `adc_input` drive is intentional and not representative of analog loop timing.
- Xilinx IP internals are treated as black boxes; this testbench verifies top-level behavior visible at `am_testbed_sv`.
