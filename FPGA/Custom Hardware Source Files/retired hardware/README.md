# Retired Hardware

These Verilog modules are **not used by the current design**. They have zero live
instantiations in `full_design.bd` or `modulator_chain.bd`, and no active module
instantiates them (verified by grepping every active module). They are kept for
reference and history. Their testbenches are in `testbenches/`.

Determined 2026-07-24 against the authoritative block design.

| Module | Retired because |
|---|---|
| `output_packetizer.v` | superseded by `output_packetizer_v2.v` (self-describing packetizer) |
| `trigger_logic.v` | superseded by `trigger_engine.v` (Plan-07 fire-at-timestamp) |
| `state_machine.v` | legacy control FSM, no longer instantiated |
| `mag_phase_calculator.v` | replaced by the CORDIC IP inside `modulator_chain` |
| `decimator_lpf_wrapper.v` | replaced by the CIC Compiler IP inside `modulator_chain` |
| `lock-in_mixer.v` | replaced by DDS + mult_gen IP inside `modulator_chain` |
| `mixer.v` | replaced by DSP/mult_gen IP (only referenced in comments now) |
| `phase_accumulator.v` | replaced by the DDS Compiler IP |
| `phase_accumulator_aligner.v` | part of the retired hand-rolled DDS |
| `phase_accumulator_slave.v` | part of the retired hand-rolled DDS |
| `phase_adjuster.v` | part of the retired hand-rolled DDS |
| `phase_synchronizer.v` | part of the retired hand-rolled DDS |
| `running_mean_subtractor.v` | unused |
| `path_delay_calibration.v` | unused |
| `DAC_driver_top.v` | superseded by `dac_output_wrapper.v` + SelectIO IP |
| `adc_data_realignment.v` | superseded by the current ADC capture path |
| `adc_fifo_write.v` | superseded by the current ADC capture path |
| `adc_input_selectio_wiz.v` | superseded by the SelectIO Wizard IP |

## Not retired (kept in the parent folder)

- `reset_sync.v` — a live leaf: instantiated four times inside the active
  `reset_manager.v`.

## Notes

- Some of these (e.g. `DAC_driver_top.v`, `adc_input_selectio_wiz.v`) may have
  been top/leaf modules of earlier standalone test designs (the `DAC_test` /
  "working dac" builds), not just the main pipeline. They are retired **from the
  current `full_design`**.
- If you reinstate any of these, remember Vivado compiles the imported copies
  under `…srcs/sources_1/imports/…`, not this GitHub-tree source — re-import after
  restoring (see `docs/guides/fpga-developer-guide.md`).

The active module set and the full rationale are in
`docs/guides/fpga-developer-guide.md`.
