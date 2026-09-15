# Plan 05 — Multi-frequency demod + configurable packetizer refactor

## Status / prerequisite
Single-frequency ADC path is **working end to end** (verified 2026-07-16: 450 kHz
excitation → analog HPF → AD9467 → LVDS capture → deinterleave → demod; clean 50 kHz
alias at −33 dBFS, 57 dB over noise). This plan scales that to multi-frequency.

## Locked decisions (from the user)
1. **4 simultaneous demod frequencies.**
2. **ADC runs at 200 MSPS**; the raw-ADC monitor channel is **decimated to the common
   record rate** (~200 kHz), uniform with the demod channels.
3. **No per-channel coherent phase restart** → a single group DDS reset covers all 4.

## Open decisions to confirm at kickoff
- **DDS Compiler vs 4× replicated CORDIC** for the sin/cos generators. *Recommendation:
  DDS Compiler* — integrates accumulator + sin/cos, takes freq/phase words directly, and
  eliminates the scaled-radians phase headache (phase_accumulator.v hand-fix). Fallback:
  replicate the existing CORDIC + phase_accumulator 4×.
- **Full-rate "scope mode"** for raw ADC (burst full-rate ADC into a DMA buffer for
  waveform/oscillation inspection): in scope now, or deferred? Default: **deferred** — ship
  the decimated monitor channel first; the tagged-stream design accommodates a bursty
  channel later.

---

## Target architecture

```
                   ┌ DDS0(FCW0) sin/cos0 ─┬─cos─┐
ADC(200MSPS) ─┬────┤ DDS1(FCW1) sin/cos1 ─┼─cos─┤ Σ → DAC (multitone excitation)
              │    │ DDS2(FCW2) sin/cos2 ─┼─cos─┤
              │    └ DDS3(FCW3) sin/cos3 ─┴─cos─┘
              │        │ sin/cos i
              │        ▼ (per channel)
              │   mixer_i → CIC_i → FIR_i → mag/phase_i ─→ AXIS ch(1..4)
              └─→ CIC decimate → raw-ADC monitor ─────────→ AXIS ch0
                                          status/OR ───────→ AXIS chS
   AXIS ch0,1..4,S → enable-mask router → packetizer → self-describing pkt → S2MM DMA → UDP
```

- The 4 sin/cos generators serve BOTH sides: `cos` outputs sum into the DAC (multitone
  excitation at the 4 frequencies), `sin/cos` feed the 4 demod mixers. Same "one generator
  shared DAC+demod" pattern as today, replicated to 4.
- Mixing MUST be at full 200 MSPS (carrier can sit well above any decimated rate); CIC
  decimates AFTER mixing. So 4 parallel mixer→CIC→FIR chains (no time-multiplex possible at
  200 MHz fabric = sample rate).
- Two clock domains remain: **DCO (D20)** capture vs **CLKin (Y6)** processing; the
  `fifo_generator` CDC FIFO stays (with the FWFT read fix already in adc_fifo_read.v).

---

## Stage A — Reset consolidation (do first, clean foundation)
Collapse the ~14 per-IP `*_nreset_N` ilslices into functional groups; 2-tier scheme:
- **Hardware system reset** from `proc_sys_reset` (PS FCLK_RESET + clk `locked`) — brings up
  the PL incl. the register file. NOT software-sourced.
- **Software soft-resets** (register bits) for runtime re-init groups:
  | group | resets | sw-visible |
  |---|---|---|
  | system | all PL | no (hw) |
  | dds | all 4 phase accumulators/DDS (one reset) | yes |
  | capture+packetizer+DMA FIFO | ADC capture, FIFO, packetizer | yes |
  | dac config | DAC SPI hold (existing reg2 bit12 use) | yes |
- Each block reset = `system_aresetn AND soft_reset_n[group]`; soft resets through a
  reset synchronizer (async-assert / sync-deassert). Standardize **active-low `aresetn`**
  (kill the bit3 active-high oddball). Demod datapath (mixers/CIC/FIR) gets **no** dedicated
  reset — self-flushing; skipping it frees routing and lets DSP/SRL pack.
- Verify: pipeline still runs; soft-reset each group individually and confirm scope-level
  behavior (DDS restart, packetizer flush).

## Stage B — Configurable tagged packetizer + self-describing format
- Make each producer an **AXIS with a TID**: raw-ADC=0, demod ch=1..4, status/OR=S.
- **Enable-mask register** (new reg, set by iza_ctrl) gates which channels enter the DMA →
  disabled channel = 0 bytes = bandwidth saved.
- **Self-describing packet**: header carries the active `channel_mask` (+ derived record
  stride). Recommended payload = **fixed-schema super-records**: since all channels share the
  common record rate, one record instant = concatenated fields of the *enabled* channels; the
  header mask tells the PC the layout. (Avoids per-record tag overhead vs. a tagged-record
  scheme.) Keep the existing 16 B demod record (signal i32, phase i32, ts) as the per-channel
  demod unit; raw-ADC unit = i16 (+ pack). Timestamp packing stays: [63:62] OR, [61:46] raw
  ADC debug tap (can retire once ch0 exists), [45:0] counter.
- Bandwidth: 4 demod × ~26 Mbps + decimated ADC ~26 Mbps ≈ 130 Mbps — fits GbE with room.
- Deliver the earlier "ADC → packetizer" ask AS channel 0 of this mechanism (not a bypass).
- Verify: toggle mask via iza_ctrl, confirm packet size changes and PC parses variable payloads.

## Stage C — Replicate demod to 4× + multitone DAC + DDS + register map
- 4× {phase word → DDS sin/cos → complex mixer → CIC → FIR → mag/phase}. Sum the 4 `cos`
  into the DAC (multitone). One `dds` soft-reset for all 4 (no per-channel restart).
- **Register map expansion** (exact layout TBD from current regfile width):
  - 4 × 48-bit FCW (2 regs each) = 8 regs
  - soft-reset word (functional groups)
  - channel enable mask (packetizer)
  - PGA (dB→code map already in iza_ctrl), demod source/test, DAC multitone enable
  - keep OR/status wiring
- Resource check on the 7020 (~220 DSP48): 4 chains (mixers + CICs + FIRs + DDS). Comfortable
  unless FIRs are long — do a DSP/LUT estimate once FIR taps are chosen.
- Verify: set 4 distinct FCWs, multitone on DAC (scope = sum of 4 tones), 4 demod magnitudes
  track their respective tones with a known DUT.

## Stage D — Host tooling (iza_ctrl / plotter / receiver)
- iza_ctrl: `set_freq(ch, hz)` (per-channel FCW), `set_channel_mask(mask)`,
  `soft_reset(group)`. Keep dB-based `set_pga`.
- Packet parsers (iza_receiver, iza_plotter, iza_validate): parse the **self-describing
  header** (mask → layout) instead of a hardcoded struct; render N demod channels + raw-ADC +
  the live spectrum (already added). Per-channel magnitude/phase traces.
- Update the mask/counter constants: with ch0 raw-ADC as a real channel, the timestamp
  [61:46] debug tap can be retired and the counter mask widened back to [61:0].

---

## Risks / notes
- **DSP budget** on the 7020 with 4 chains — estimate early; long FIRs are the risk. Consider
  sharing/among channels or shorter FIRs if tight.
- **CDC** stays real: DCO(D20) capture vs CLKin(Y6) processing — keep the FIFO; don't wire
  raw cross-domain paths (the no-FIFO tap was debug-only).
- **Carrier constraints**: analog HPF passes only >400 kHz; keep 2·fc on a CIC null (multiple
  of the ~50 kHz output grid) per channel to suppress sum images.
- **Multitone DAC**: watch DAC full-scale — sum of 4 tones must not clip; scale each.
- **Self-describing format is load-bearing**: if the packetizer content is configurable, the
  PC MUST parse from the header, or every mask change desyncs the parser.

## Verification gate (end state)
- Mask any subset of {raw-ADC, demod0..3}; PC parses correctly; bandwidth scales with mask.
- 4 distinct carriers >400 kHz; multitone on DAC scope; 4 independent magnitude/phase readings
  on a known reference DUT; live spectrum shows all tones (aliased in the raw monitor).
- Soft-reset each group independently without disturbing others.

## Key files
- FPGA: full_design.bd, adc_lvds_capture.v, adc_bit_reorder.v, adc_fifo_read.v,
  phase_accumulator.v (retire if DDS Compiler), dac_output_wrapper.v, dac_test_constraints.xdc
- Firmware: petalinux_overlay/meta-user/recipes-apps/iza-stream/files/{iza_replay.c,
  iza_protocol.h}
- PC: petalinux_overlay/pc/{iza_ctrl.py, iza_plotter.py, iza_receiver.py, iza_validate.py}
- Memory: plan04-control-spi.md (all the single-freq bring-up gotchas)
