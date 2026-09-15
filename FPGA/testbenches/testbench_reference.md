# Testbench Reference

Documents every test case for all custom RTL testbenches. Updated as new modules are built.

All testbenches use a 200 MHz clock (5 ns period), async active-low reset, and a shared `check` task that reports PASS/FAIL with an error counter. Reset is always released at `@(negedge clock)` to avoid posedge race conditions with the DUT.

---

## tb_phase_accumulator.sv

**DUT:** `phase_accumulator.v` -- 48-bit DDS phase accumulator
**Parameters:** `ACCUM_WIDTH = 48`, `PHASE_WIDTH = 16`

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: phase_out is zero | Assert reset for 4 cycles, verify `phase_out == 0` |
| 1b | Reset: phase_msb is zero | Same reset window, verify `phase_msb == 0` |
| 2a | Increment: phase_out == 1 after first cycle | FCW = `1 << 32`, release reset, verify `phase_out` increments by 1 per cycle |
| 2b | Increment: phase_out == 11 after 11 cycles | Same FCW, verify correct accumulation after 11 total cycles |
| 3 | MSB toggle: toggles every cycle (100 toggles in 100 cycles) | FCW = `48'h8000_0000_0000` (half accumulator range), count MSB transitions over 100 cycles, expect 100 toggles |
| 4 | Resolution: phase_out stays 0 with FCW=1 after 100 cycles | FCW = 1 (minimum step), verify `phase_out` remains 0 since 100 < 2^32 |
| 5a | Rollover: phase_out == 0xFFFF after 1 cycle with FCW=0xFFFF<<32 | FCW = `48'hFFFF_0000_0000`, verify phase wraps to 0xFFFF after 1 cycle |
| 5b | Rollover: phase_out == 0xFFFE after 2 cycles | Same FCW, verify continued wrap-around subtraction |
| 6a | FCW change: phase_out == 5 after 5 cycles with FCW=1<<32 | Run 5 cycles with FCW = `1 << 32`, expect `phase_out == 5` |
| 6b | FCW change: phase_out == 15 after 5 more cycles with FCW=2<<32 | Change FCW to `2 << 32` mid-operation, expect `5 + 5*2 = 15` |

---

## tb_timestamp_counter.sv

**DUT:** `timestamp_counter.v` -- 64-bit free-running counter
**Parameters:** `COUNT_WIDTH = 64`

| Test | Check String | Description |
|------|-------------|-------------|
| 1 | Reset: timestamp is zero | Assert reset for 4 cycles, verify `timestamp === 0` |
| 2a | Increment: timestamp == 1 after first cycle | Release reset, verify counter is 1 after one active clock |
| 2b | Increment: timestamp == 2 after second cycle | Verify counter is 2 after two active clocks |
| 2c | Increment: timestamp == 3 after third cycle | Verify counter is 3 after three active clocks |
| 3 | Count: timestamp == 1000 after 1000 cycles | Reset, release, run 1000 cycles, verify exact count |
| 4 | Continue: timestamp == 1500 after 500 more cycles | Without reset, run 500 more cycles, verify `1000 + 500 = 1500` |
| 5a | Mid-count reset: timestamp is zero | Assert reset while counter is at 1500, verify immediate clear to 0 |
| 5b | Resume: timestamp == 10 after reset and 10 cycles | Release reset, run 10 cycles, verify counting resumes from 0 |

---

## tb_phase_adjuster.sv

**DUT:** `phase_adjuster.v` -- 32-bit signed subtractor with clock enable
**Parameters:** `WIDTH = 32`

| Test | Check String | Description |
|------|-------------|-------------|
| 1 | Reset: corrected_phase is zero | Assert reset for 4 cycles, verify output is 0 |
| 2 | Positive offset: 0x1000 - 0x0400 == 0x0C00 | Basic subtraction with `measured > offset` |
| 3 | CE deasserted: output holds at 0x0C00 | Deassert `ce`, change inputs, verify output does not update for 5 cycles |
| 4 | Wrap: 0x0100 - 0x0400 == 0xFFFF_FD00 | `measured < offset`, verify unsigned wrap-around (correct for phase arithmetic) |
| 5 | Large offset: 0x80000000 - 0x7FFFFFFF == 0x00000001 | Near-boundary subtraction |
| 6 | Zero offset: passthrough 0x12345678 | Offset = 0, verify measured phase passes through unchanged |
| 7 | Equal: same input and offset == 0 | Identical values, verify result is exactly 0 |
| 8 | Full wrap: 0x0 - 0x1 == 0xFFFFFFFF | Zero minus one, verify full 32-bit wrap |
| 9a | CE pulse: output updated to 0xF0 | Pulse `ce` for a single cycle with `0xFF - 0x0F`, verify output updates to 0xF0 |
| 9b | CE pulse hold: output still 0xF0 | After single-pulse update, verify output holds for 5 more cycles with `ce` deasserted |

---

## tb_adc_data_realignment.sv

**DUT:** `adc_data_realignment.v` -- reconstructs 16-bit ADC sample from 32-bit IDDR DDR output
**Parameters:** `WIDTH = 16`

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: adc_sample is zero | Assert reset for 4 cycles, verify `adc_sample === 0` |
| 1b | Reset: adc_valid is low | Same reset window, verify `adc_valid === 0` |
| 2a | Upper select: adc_sample == 0xA5A5 (upper half) | `capture_select = 0`, verify upper 16 bits of `raw_data` selected |
| 2b | Upper select: adc_valid asserted | Verify `adc_valid` goes high after reset release |
| 3 | Lower select: adc_sample == 0x5A5A (lower half) | `capture_select = 1`, verify lower 16 bits of `raw_data` selected |
| 4a | Single-bit invert: bit 0 inverted, adc_sample == 0x0001 | `polarity_mask = 0x0001` with zero input, verify bit 0 inverted (upper half) |
| 4b | Single-bit invert lower: bit 0 inverted, adc_sample == 0x0001 | Same mask, `capture_select = 1`, verify inversion applies to lower half too |
| 5 | Per-lane invert: all 16 bits independently verified | Walk a 1 through each bit of `polarity_mask` with zero input, verify each bit inverts independently |
| 6 | All-ones mask: 0xA5A5 inverted == 0x5A5A | `polarity_mask = 0xFFFF`, verify full bitwise inversion |
| 7 | All-zeros mask: 0xA5A5 unchanged | `polarity_mask = 0x0000`, verify no inversion |
| 8a | Combined upper: 0xFF00 ^ 0x0F0F == 0xF00F | Polarity + capture_select = 0, verify combined operation |
| 8b | Combined lower: 0x00FF ^ 0x0F0F == 0x0FF0 | Polarity + capture_select = 1, verify combined operation |
| 9a | Realistic pattern upper: 0xFE0C passthrough | 2's complement sample, no inversion, upper half |
| 9b | Realistic pattern lower: 0x01F3 passthrough | 2's complement sample, no inversion, lower half |
| 10a | Re-reset: adc_valid deasserted | Assert reset mid-operation, verify `adc_valid` drops |
| 10b | Re-release: adc_valid reasserted | Release reset again, verify `adc_valid` comes back |

---

## tb_phase_synchronizer.sv

**DUT:** `phase_synchronizer.v` -- continuous master-slave CDC with double-flop, edge detect, and correction
**Parameters:** `FCW_WIDTH = 48`
**Note:** Uses two independent clocks -- DAC at 5.0 ns, ADC at 5.008 ns (async).

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: synced_phase_msb is zero | Assert reset, verify synced MSB is 0 |
| 1b | Reset: correction is zero | Assert reset, verify correction is 0 |
| 1c | Reset: synced_fcw is zero | Assert reset, verify synced FCW is 0 |
| 2 | CDC: synced_phase_msb == 1 after master MSB transition | Toggle master MSB in DAC domain, verify it appears in ADC domain within 5 cycles |
| 3 | Correction: non-zero when slave MSB disagrees with synced master MSB | Master MSB → 1, slave stays 0, verify correction = `2'b01` (+1) |
| 4 | Correction: zero when slave MSB agrees with synced master MSB | Master MSB → 1, slave also 1, verify correction = `2'b00` |
| 5 | Correction: returns to zero when no edge detected | After an edge event, verify correction returns to 0 on subsequent cycles |
| 6 | FCW: synced_fcw matches input after registration | Set FCW, release reset, verify `synced_fcw` matches after a few ADC cycles |
| 7 | Multi-toggle: 10 MSB transitions all propagated correctly | Toggle master MSB 10 times with slave matching, verify all propagate through CDC |

---

## tb_phase_accumulator_slave.sv

**DUT:** `phase_accumulator_slave.v` -- 48-bit accumulator with signed 2-bit correction input
**Parameters:** `ACCUM_WIDTH = 48`, `PHASE_WIDTH = 16`

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: phase_out is zero | Assert reset, verify `phase_out === 0` |
| 1b | Reset: phase_msb is zero | Assert reset, verify `phase_msb === 0` |
| 2 | No correction: phase_out == 10 after 10 cycles (same as master) | FCW = `1 << 32`, correction = 0, verify identical to master accumulator |
| 3a | +1 setup: phase_out == 5 before correction | Run 5 cycles, verify baseline before applying correction |
| 3b | +1 correction: phase_out == 6 after correction cycle | Apply +1 for 1 cycle, verify accumulator advanced by FCW+1 |
| 3c | +1 aftermath: phase_out == 10 after 4 more cycles | Continue without correction, verify normal accumulation resumes |
| 4a | -1 setup: phase_out == 5 before correction | Run 5 cycles, verify baseline |
| 4b | -1 correction: phase_out == 5 (increment upper bits == 0 this cycle) | Apply -1 for 1 cycle; FCW-1 = `0x0000_FFFF_FFFF`, upper 16 bits = 0, so `phase_out` does NOT advance this cycle |
| 5 | Multi +1: phase_out == 10 after 10 cycles with +1 each | Apply +1 every cycle for 10 cycles, verify phase_out = 10 (corrections accumulate below phase_out) |
| 6a | Integration: offset is stable (drift < 4 between checkpoints) | Full system: master (DAC clk) + synchronizer + slave (ADC clk) with same-freq async clocks. Sample offset at two points 1000 cycles apart, verify drift < 4 (stable tracking) |
| 6b | Integration: absolute offset within expected range | Verify constant offset is < 300 phase_out counts (expected ~FCW/2^32 due to FCW registration delay, compensated by Phase Adjuster in real system) |

---

## tb_mixer.sv

**DUT:** `mixer.v` -- signed 16×16→32 lock-in mixer with FIFO read control
**Parameters:** `INPUT_WIDTH = 16`, `OUTPUT_WIDTH = 32`, `FIFO_COUNT_WIDTH = 8`

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: i_out is zero | Assert reset, verify I output is 0 |
| 1b | Reset: q_out is zero | Assert reset, verify Q output is 0 |
| 1c | Reset: valid_out is low | Assert reset, verify valid is 0 |
| 1d | Reset: fifo_rd_en is low | Assert reset, verify FIFO read enable is 0 |
| 2a | Positive: i_out == 100 * 200 = 20000 | Known positive inputs, verify correct signed product |
| 2b | Positive: q_out == 100 * 300 = 30000 | Same sample, different sin reference |
| 2c | Positive: valid_out asserted | Verify valid goes high during active mixing |
| 2d | Positive: fifo_rd_en asserted | Verify FIFO read enabled during active mixing |
| 3a | Negative: i_out == -1000 * 500 = -500000 | Negative ADC × positive cos |
| 3b | Negative: q_out == -1000 * -750 = 750000 | Negative ADC × negative sin |
| 4a | Disabled: i_out is zero | `processing_enable = 0`, verify I output cleared |
| 4b | Disabled: q_out is zero | Q output cleared |
| 4c | Disabled: valid_out is low | Valid deasserted |
| 4d | Disabled: fifo_rd_en is low | FIFO read disabled |
| 5a | Empty FIFO: fifo_rd_en is low | `fifo_data_count = 0`, verify no read attempt |
| 5b | Empty FIFO: valid_out is low | No valid output when FIFO empty |
| 5c | FIFO has data: fifo_rd_en asserted | `fifo_data_count = 1`, verify read resumes |
| 5d | FIFO has data: valid_out asserted | Valid output resumes |
| 6 | Full-scale pos: i_out == 32767^2 = 0x3FFF0001 | Max positive × max positive, verify no overflow |
| 7 | Full-scale neg: i_out == (-32768)^2 = 0x40000000 | Max negative × max negative |
| 8a | Cross sign: i_out == 32767 * (-32768) | Max positive × max negative |
| 8b | Cross sign: q_out == 32767 * (-32767) | Cross-sign multiplication on Q channel |
| 9a | Zero sample: i_out == 0 | ADC = 0, verify product is 0 regardless of reference |
| 9b | Zero sample: q_out == 0 | Same for Q channel |

---

## tb_dac_output_wrapper.sv

**DUT:** `dac_output_wrapper.v` -- registered MUX selecting between DDS and test pulse data
**Parameters:** `WIDTH = 16`

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: dac_data is zero | Assert reset for 4 cycles, verify `dac_data === 0` |
| 1b | Reset: dac_data_valid is low | Same reset window, verify `dac_data_valid === 0` |
| 2a | Normal mode: dac_data == dds_data (0x1234) | `test_mode = 0`, verify DDS data passes through |
| 2b | Normal mode: dac_data_valid asserted | Verify valid goes high after reset release |
| 3 | Test mode: dac_data == test_pulse_data (0xABCD) | `test_mode = 1`, verify test pulse passes through |
| 4a | Switch to normal: dac_data == 0x7FFF | Switch `test_mode` 1->0, verify DDS source selected |
| 4b | Switch to test: dac_data == 0x8000 | Switch `test_mode` 0->1, verify test source selected |
| 4c | Switch back to normal: dac_data == 0x7FFF | Switch `test_mode` 1->0 again, verify clean switching |
| 5a | Data update 1: dac_data == 0x0001 | Change DDS data while in normal mode, verify propagation |
| 5b | Data update 2: dac_data == 0xFFFE | Another DDS data change, verify propagation |
| 6a | Test update 1: dac_data == 0x0000 | Change test pulse data while in test mode, verify propagation |
| 6b | Test update 2: dac_data == 0xFFFF | Another test pulse data change, verify propagation |
| 7a | Re-reset: dac_data_valid deasserted | Assert reset mid-operation, verify valid drops |
| 7b | Re-release: dac_data_valid reasserted | Release reset, verify valid comes back |

---

## tb_decimator_lpf_wrapper.sv

**DUT:** `decimator_lpf_wrapper.v` -- CIC + FIR plumbing, config loading, enable gating
**Parameters:** `DATA_WIDTH = 32`, `CONFIG_WIDTH = 16`, `RELOAD_WIDTH = 24`
**Note:** CIC and FIR IP ports are exposed as wrapper ports; testbench drives/monitors them directly.

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: cic_s_axis_data_tvalid is low | Assert reset, verify CIC input valid is 0 |
| 1b | Reset: cic_s_axis_config_tvalid is low | Assert reset, verify CIC config valid is 0 |
| 2a | Enable gate: cic_s_axis_data_tvalid low when disabled | `processing_enable = 0`, verify CIC input gated |
| 2b | Enable gate: cic_s_axis_data_tdata passes data | Data bus is always connected (valid gates it) |
| 2c | Enable gate: cic_s_axis_data_tvalid high when enabled | `processing_enable = 1`, verify CIC input active |
| 3 | Data passthrough: cic_s_axis_data_tdata == 0x12345678 | Change input data, verify CIC input matches |
| 4a | Config load: cic_s_axis_config_tvalid pulsed high | Assert `config_load`, verify single-cycle pulse |
| 4b | Config load: cic_s_axis_config_tdata == 500 | Verify decimation ratio loaded correctly |
| 4c | Config load: tvalid returns low after one cycle | Verify config valid deasserts after one cycle |
| 4d | Config load: no re-pulse while held high | Hold `config_load` high, verify no duplicate pulse |
| 5a | Config re-load: tvalid pulsed for new ratio | Deassert then reassert `config_load`, verify new pulse |
| 5b | Config re-load: tdata == 1000 | Verify new decimation ratio value |
| 6a | CIC->FIR: fir_s_axis_data_tdata == 0xCAFEBABE | Drive CIC output, verify FIR input matches |
| 6b | CIC->FIR: fir_s_axis_data_tvalid high | Verify FIR input valid follows CIC output valid |
| 6c | CIC->FIR: fir_s_axis_data_tvalid low when CIC invalid | Deassert CIC valid, verify FIR valid drops |
| 7a | FIR reload: tdata == 0xABCDEF | Drive reload data, verify passthrough |
| 7b | FIR reload: tvalid high | Verify reload valid passthrough |
| 7c | FIR reload: tlast low | Verify tlast passthrough (not last) |
| 7d | FIR reload last: tdata == 0x123456 | New reload data with last flag |
| 7e | FIR reload last: tlast high | Verify tlast passthrough (last) |
| 8a | FIR output: data_out == 0x0000FACE | Drive FIR output, verify wrapper output matches |
| 8b | FIR output: data_valid_out high | Verify wrapper output valid follows FIR output valid |
| 8c | FIR output: data_valid_out low when FIR invalid | Deassert FIR valid, verify wrapper valid drops |
| 9a | Full pipeline: CIC input valid with data | Drive data through wrapper with enable, verify CIC input |
| 9b | Full pipeline: FIR receives CIC output | Simulate CIC output, verify FIR input |
| 9c | Full pipeline: wrapper output from FIR | Simulate FIR output, verify wrapper output |

---

## tb_mag_phase_calculator.sv

**DUT:** `mag_phase_calculator.v` -- CORDIC vectoring wrapper for magnitude/phase
**Parameters:** `DATA_WIDTH = 32`, `CORDIC_WIDTH = 64`
**Note:** CORDIC IP ports are exposed as wrapper ports; testbench drives/monitors them directly.

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: CORDIC tvalid is low | Assert reset, verify CORDIC input valid is 0 |
| 1b | Reset: CORDIC tdata is zero | Assert reset, verify CORDIC input data is 0 |
| 1c | Reset: magnitude is zero | Assert reset, verify magnitude output is 0 |
| 1d | Reset: phase is zero | Assert reset, verify phase output is 0 |
| 1e | Reset: valid_out is low | Assert reset, verify output valid is 0 |
| 2a | Packing: lower 32 bits == I (0xAAAA_BBBB) | Set I/Q, verify I in lower 32 bits of CORDIC tdata |
| 2b | Packing: upper 32 bits == Q (0xCCCC_DDDD) | Verify Q in upper 32 bits of CORDIC tdata |
| 2c | Packing: tvalid asserted | Verify CORDIC tvalid follows valid_in when ce high |
| 3a | CE gate: tvalid low when ce deasserted | Deassert `ce`, verify CORDIC tvalid goes low |
| 3b | CE gate: tdata holds previous value | Verify data remains latched when ce deasserted |
| 4a | valid_in gate: tvalid low when valid_in deasserted | `ce = 1`, `valid_in = 0`, verify tvalid low |
| 4b | valid_in gate: tvalid high when valid_in reasserted | `valid_in = 1`, verify tvalid reasserts |
| 5a | Unpack: magnitude == 0x0000_7FFF (lower 32 bits) | Drive CORDIC output, verify magnitude from lower half |
| 5b | Unpack: phase == 0x3243_F6A9 (upper 32 bits) | Verify phase from upper half of CORDIC output |
| 5c | Unpack: valid_out asserted | Verify valid_out follows CORDIC output valid |
| 6a | valid_out: deasserts when CORDIC invalid | Deassert CORDIC valid, verify valid_out drops |
| 6b | valid_out: reasserts when CORDIC valid | Reassert CORDIC valid, verify valid_out comes back |
| 7a | Seq 1: I=1 Q=0 packed correctly | Verify `{32'h0, 32'h1}` packing |
| 7b | Seq 2: I=0 Q=1 packed correctly | Verify `{32'h1, 32'h0}` packing |
| 7c | Seq 3: I=-1 Q=-1 packed correctly | Verify `{32'hFFFFFFFF, 32'hFFFFFFFF}` packing |
| 8a | Mid-reset: CORDIC tvalid cleared | Assert reset mid-operation, verify CORDIC tvalid cleared |
| 8b | Mid-reset: magnitude cleared | Verify magnitude zeroed |
| 8c | Mid-reset: phase cleared | Verify phase zeroed |
| 8d | Mid-reset: valid_out cleared | Verify valid_out zeroed |

---

## tb_path_delay_calibration.sv

**DUT:** `path_delay_calibration.v` -- dual-domain step generator + threshold detector
**Parameters:** `DATA_WIDTH = 16`, `TIMESTAMP_WIDTH = 64`, `SETTLE_CYCLES = 10` (reduced for sim)
**Note:** Uses same-frequency DAC and ADC clocks for deterministic delay testing. Testbench provides simple timestamp counters for both domains.

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: test_mode is low | Assert reset, verify `test_mode === 0` |
| 1b | Reset: test_pulse_data is mid-scale | Verify output is mid-scale (0x0000) |
| 1c | Reset: tx_timestamp_valid is low | Verify DAC-side timestamp not captured |
| 1d | Reset: rx_timestamp_valid is low | Verify ADC-side timestamp not captured |
| 2a | Settle: test_mode asserted | After `calibration_start`, verify test_mode goes high |
| 2b | Settle: test_pulse_data is mid-scale | During settling period, output stays at mid-scale |
| 2c | Settle: tx_timestamp_valid still low | Timestamp not yet captured during settling |
| 3a | Step: test_pulse_data is full-scale | After SETTLE_CYCLES, output transitions to full-scale (0x7FFF) |
| 3b | Step: tx_timestamp_valid asserted | Timestamp captured at step edge |
| 3c | Step: test_mode still asserted | Test mode remains active after step |
| 4 | TX capture: tx_timestamp is non-zero | Verify captured timestamp has a valid value |
| 5a | Delay: rx_timestamp_valid still low before crossing | With armed detector, sample below threshold |
| 5b | Threshold: rx_timestamp_valid asserted | Sample crosses threshold, timestamp captured |
| 5c | Delay: measured delay is positive | `rx_timestamp - tx_timestamp > 0` |
| 6 | No re-trigger: rx_timestamp unchanged | After first capture, new crossing doesn't re-trigger |
| 7a | Disarm: rx_timestamp_valid cleared | De-asserting armed clears valid |
| 7b | Re-arm: rx_timestamp_valid re-triggers on armed sample | Re-arming with sample above threshold re-captures |
| 8a | Deassert: test_mode returns low | `calibration_start = 0` returns DAC side to IDLE |
| 8b | Deassert: test_pulse_data is mid-scale | Output returns to mid-scale |
| 9 | Sub-threshold: rx_timestamp_valid stays low | Sample below threshold doesn't trigger |

---

## tb_trigger_logic.sv

**DUT:** `trigger_logic.v` -- threshold crossing detector with mode selection and GPIO latch
**Parameters:** `DATA_WIDTH = 32`
**Config format:** `trigger_config[1:0]` = mode (00=disabled, 01=magnitude, 10=phase, 11=either), `trigger_config[2]` = edge (0=rising, 1=falling)

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: trigger_flag is low | Assert reset, verify trigger flag is 0 |
| 1b | Reset: gpio_out is low | Assert reset, verify GPIO is 0 |
| 2 | Disabled: trigger_flag stays low | Mode=00, magnitude crosses threshold, no trigger |
| 3a | Mag rising baseline: trigger_flag low | Magnitude below threshold, no trigger |
| 3b | Mag rising: trigger_flag asserted | Magnitude crosses above threshold, single-cycle pulse |
| 3c | Mag rising: trigger_flag clears next cycle | Verify pulse is only one cycle |
| 4 | GPIO: latched high after trigger | GPIO stays high after trigger fires |
| 4b | GPIO: still latched after 5 cycles | GPIO remains latched without reset |
| 5a | Mag falling baseline: trigger_flag low | Magnitude above threshold with edge=1, no trigger |
| 5b | Mag falling: trigger_flag asserted | Magnitude drops below threshold, trigger fires |
| 6a | Phase baseline: trigger_flag low | Phase below threshold, mode=10 |
| 6b | Phase rising: trigger_flag asserted | Phase crosses above threshold |
| 7a | Combined baseline: trigger_flag low | Both below threshold, mode=11 |
| 7b | Combined mag-only: trigger_flag asserted | Only magnitude crosses, trigger fires (OR logic) |
| 8a | No false trigger: stays low below threshold | Multiple samples below threshold, no trigger |
| 8b | No false trigger: GPIO stays low | GPIO not set when no trigger |
| 9 | Valid gating: trigger_flag stays low without data_valid | Crossing occurs but `data_valid` never asserted |
| 10a | Negative baseline: trigger_flag low | Negative threshold, magnitude below (more negative) |
| 10b | Negative rising: trigger_flag asserted | Magnitude crosses above negative threshold |

---

## tb_state_machine.sv

**DUT:** `state_machine.v` -- system-level FSM controlling measurement flow
**States:** IDLE(0), CONFIGURE(1), STARTUP_CIC(2), STARTUP_FIR(3), RUN(4), STOP(5), CAL_START(6), CAL_ARM(7), CAL_DONE(8)
**Commands:** NOP(0), CONFIGURE(1), START(2), STOP(3), CALIBRATE(4)
**Status format:** `[3:0]` = state, `[4]` = processing_enable, `[5]` = calibration_done

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: state is IDLE | Assert reset, verify state = 0 |
| 1b | Reset: pipeline_reset_n is low | Pipeline in reset |
| 1c | Reset: processing_enable is low | Processing disabled |
| 1d | Reset: calibration_start is low | No calibration activity |
| 2a | Configure: state is CONFIGURE | CMD_CONFIGURE from IDLE |
| 2b | Configure: pipeline_reset_n is low | Pipeline stays in reset |
| 2c | Configure: processing_enable is low | Processing stays disabled |
| 3 | Startup CIC: state is STARTUP_CIC or beyond | CMD_START triggers CIC config |
| 4a | Startup FIR: state is STARTUP_FIR | Auto-advances from CIC after 1 cycle |
| 4b | Startup FIR: pipeline still in reset | Pipeline not yet released |
| 5a | Run: state is RUN | `fir_reload_done` triggers RUN |
| 5b | Run: pipeline_reset_n is high | Pipeline released |
| 5c | Run: processing_enable is high | Processing active |
| 5d | Run stable: pipeline_reset_n still high | Stays active over multiple cycles |
| 5e | Run stable: processing_enable still high | Stays active |
| 6a | Stop: state is STOP or IDLE | CMD_STOP from RUN |
| 6b | Stop: pipeline_reset_n is low | Pipeline back in reset |
| 6c | Stop: processing_enable is low | Processing disabled |
| 6d | Back to IDLE: state is IDLE | STOP auto-transitions to IDLE |
| 7a | Cal start: state is CAL_START | CMD_CALIBRATE from IDLE |
| 7b | Cal start: calibration_start asserted | Step generator triggered |
| 7c | Cal start: pipeline in reset | Pipeline in reset during calibration |
| 7d | Cal arm: state is CAL_ARM | `tx_timestamp_valid` advances to ARM |
| 7e | Cal arm: calibration_armed asserted | Threshold detector armed |
| 7f | Cal done: state is CAL_DONE or IDLE | `rx_timestamp_valid` completes calibration |
| 7g | Cal complete: state is IDLE | Returns to IDLE |
| 7h | Cal complete: calibration_done in status | Status bit [5] set |
| 7i | Cal complete: calibration_start deasserted | Step generator released |
| 7j | Cal complete: calibration_armed deasserted | Detector disarmed |
| 8a | Invalid cmd: IDLE ignores CMD_STOP | Wrong command for state |
| 8b | Invalid cmd: IDLE ignores CMD_START | Must configure first |
| 8c | Invalid cmd: CONFIGURE ignores CMD_CALIBRATE | Wrong command for state |
| 9a | Pre-reset: state is RUN | Verify in RUN before reset test |
| 9b | Mid-reset: state is IDLE | Async reset from RUN -> IDLE |
| 9c | Mid-reset: pipeline_reset_n is low | Pipeline in reset |
| 9d | Post-reset: state is IDLE | Stable IDLE after reset release |
| 10a | Flow: entered CONFIGURE | Full normal flow test |
| 10b | Flow: in STARTUP_FIR waiting | Waiting for FIR reload |
| 10c | Flow: entered RUN | FIR done -> RUN |
| 10d | Flow: pipeline active | Processing enabled |
| 10e | Flow: back to IDLE | STOP -> IDLE |

---

## tb_am_modulator.sv

**DUT:** `am_modulator.v` -- AM modulates CORDIC cosine carrier with internal oscillator
**Parameters:** `INPUT_WIDTH = 16`, `OUTPUT_WIDTH = 17`, `MOD_ACCUM_WIDTH = 32`
**Note:** Output feeds mixer `adc_sample` (with `INPUT_WIDTH=17`). `mod_fcw = 0` gives carrier passthrough.

| Test | Check String | Description |
|------|-------------|-------------|
| 1 | Reset: am_out is zero | Assert reset, verify output cleared |
| 2a | Passthrough: max positive cos_in == am_out | `mod_fcw=0`, carrier passes through unchanged |
| 2b | Passthrough: max negative cos_in == am_out | Negative carrier also passes through |
| 2c | Passthrough: zero cos_in == 0 | Zero carrier gives zero output |
| 3 | Modulation: am_out differs from carrier with non-zero FCW | Non-zero `mod_fcw` causes output to deviate from carrier |
| 4 | Range: no overflow in 256 cycles with max carrier | Run max carrier with fast modulation, verify 17-bit range |
| 5 | Zero carrier: am_out is zero with any FCW | Zero carrier × any envelope = zero output |
| 6a | Symmetry: positive envelope increases output | Positive modulation envelope makes output > carrier |
| 6b | Symmetry: negative envelope decreases output | Negative modulation envelope makes output < carrier |
| 7a | Small mod: am_out close to carrier with mod_envelope=1 | Tiny envelope change barely affects output |
| 7b | Accum check: output > carrier after 257 cycles of modulation | Accumulated envelope causes measurable output increase |
| 8 | Mid-reset: am_out cleared | Assert reset mid-operation, verify output zeroed |

---

## tb_am_testbed_sv.sv

**DUT:** `am_testbed_sv.sv` -- generated block-design wrapper for DDS carrier, DAC output, lock-in mixer, CIC/FIR filtering, 32-bit signal output, and 32-bit phase output
**Parameters:** 200 MHz clock, `fcw = 48'h1999_9999_999A` for 20 MHz carrier, unipolar Q1.15 sine envelope `0.50 + 0.45*sin(...)`
**Note:** Filter response checks are measurement/logging only in this first version; they do not enforce pass/fail cutoff thresholds. The testbench also probes mixer, CIC, and FIR internals so waveform/debug data is available even if the generated SV wrapper has not yet exposed the new block-design debug ports. `sampled_*` signals update only on their matching stage valid signal.

| Test | Check String | Description |
|------|-------------|-------------|
| 1a | Reset: phase_msb_0 is zero | Assert block resets, verify phase accumulator MSB is cleared |
| 1b | Reset: timestamps is zero | Assert timestamp reset, verify timestamp output is cleared |
| 2a | Timestamp: timestamps increments after reset release | Release resets, verify timestamp counter advances |
| 2b | 20 MHz carrier: phase_msb_0 toggles during observation window | Use `fcw = 48'h1999_9999_999A`, count phase MSB transitions |
| 2c | 20 MHz carrier: data_out_to_pins_0 changes during observation window | Verify the DAC pin output is active in normal DDS mode |
| 2d | 20 MHz carrier: data_out_to_pins_0 is known | Verify the DAC pin output is not X/Z after reset release |
| 3 | AM model: adc_input follows unipolar Q1.15 carrier-envelope product | Check testbench AM model computes `(carrier * envelope) >>> 15` before driving `adc_input` |
| 4a | Sine 1000 Hz: settling completed | Discard 128 `signal_out_valid` samples before measuring 1 kHz modulation |
| 4b | Sine 1000 Hz: collected measurement samples | Collect 256 valid `signal_out` samples and print average value plus FIR I/Q debug averages |
| 5a | Sine 5000 Hz: settling completed | Discard 128 valid samples before measuring 5 kHz modulation |
| 5b | Sine 5000 Hz: collected measurement samples | Collect 256 valid `signal_out` samples and print average value plus FIR I/Q debug averages |
| 6a | Sine 10000 Hz: settling completed | Discard 128 valid samples before measuring 10 kHz cutoff behavior |
| 6b | Sine 10000 Hz: collected measurement samples | Collect 256 valid `signal_out` samples and print average value plus FIR I/Q debug averages |
| 7a | Sine 15000 Hz: settling completed | Discard 128 valid samples before measuring above-cutoff behavior |
| 7b | Sine 15000 Hz: collected measurement samples | Collect 256 valid `signal_out` samples and print average value plus FIR I/Q debug averages |
| 8a | Sine 20000 Hz: settling completed | Discard 128 valid samples before measuring 20 kHz modulation |
| 8b | Sine 20000 Hz: collected measurement samples | Collect 256 valid `signal_out` samples and print average value plus FIR I/Q debug averages |
