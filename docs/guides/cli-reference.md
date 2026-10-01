# CLI Reference

The PC-side command-line tools live in `petalinux_overlay/pc/`. They share the
wire protocol library `iza_packet.py` and the control client `iza_ctrl.py`.
Run them from that directory with Python 3 (`numpy` required; `matplotlib`/
`pyqtgraph` for the plotters; `scipy` optional for high-quality resampling).

The board's default address in examples is `192.168.0.80`.

---

## `iza_ctrl.py` — board control client

Configures the board over the UDP control channel (port 7202): writes/reads any
AXI register, runs raw SPI to the DAC/ADC, and arms triggering. Importable as
`class IzaCtrl` (the GUI reuses it) and a CLI. Full register map is in the
Reference Manual, ch. 4.

```bash
python iza_ctrl.py --board 192.168.0.80 <command> [args]
```

| Command | Args | Purpose |
|---|---|---|
| `run` | — | release all resets + enable run (`SYS_CTRL0 = 0x3F`) |
| `reset` | — | graceful stop then hold all resets (preserves routing bits). Wipes the DAC's setup: run `run` + `dac-init` afterwards |
| `pga` | `gain_db` | set input PGA gain, even dB in 6..26 (higher = more gain + noise) |
| `pga-code` | `code` | raw 4-bit PGA code (0 = 26 dB … 10 = 6 dB) |
| `demod-input` | `sel` | demod input mux: 0 = analog ADC, 1 = internal loopback |
| `dac-output` | `sel` | DAC output mux: 0 = generator tones, 1 = test/replay |
| `carrier` | `hz` | channel-0 carrier (snaps to 12.5 kHz grid) |
| `freq` | `ch hz` | channel `ch` (0..3) carrier |
| `amp` | `ch val` | channel `ch` DAC amplitude (Q1.15, 0x8000 = full scale) |
| `phase` | `ch poff` | legacy per-tone phase offset (no hardware effect now) |
| `channels` | `demod_mask [--adc] [--tx M] [--amp A]` | enable demod channels, auto-size packets to the MTU, auto-balance DAC amplitudes to avoid clipping |
| `regwrite` | `reg value` | write AXI register (0..15) |
| `regread` | `reg` | read AXI register |
| `dac-init` | `[--interp {1,2,4,8}]` | AD9122 byte-mode bring-up (default 2×). **Run `run` first** so the chip is out of reset |
| `adc-init` | `[--pattern P]` | AD9467 setup (twos-complement); optional test pattern |
| `dac-write`/`dac-read` | `addr [val]` | raw AD9122 SPI |
| `adc-write`/`adc-read` | `addr [val]` | raw AD9467 SPI (writes auto-commit) |
| `fir-design` | `cutoff [--taps 127 --atten 80 --cic-comp --save f.coe]` | design a symmetric low-pass at `cutoff` Hz and load it into the FIR |
| `fir-load` | `coe [--non-symmetric]` | load FIR coefficients from a `.coe` file |
| `trig-off` | — | disarm triggering |
| `trig-soft` | `[--ampch --thr --mindiff --shift --holdoff --event --fixed-delay --pulse --polarity]` | arm soft (no-pin) triggering; events stream to UDP 7203 |

**Startup ordering (required every boot; `run` + `dac-init` again after any `reset`):**

```bash
python iza_ctrl.py --board 192.168.0.80 run          # release resets, enable run
python iza_ctrl.py --board 192.168.0.80 dac-init      # AD9122 (needs run first)
python iza_ctrl.py --board 192.168.0.80 adc-init      # AD9467
python iza_ctrl.py --board 192.168.0.80 channels 0xF  # enable 4 demod channels
```

Without `dac-init`/`adc-init` after a power cycle the converters emit garbage.
`reset` (and the GUI's Stop / Reset) holds the DAC in reset (`SYS_CTRL0`
bit 4 = 0), which puts its registers back to power-on defaults. So after the next
`run`, repeat `dac-init`. The ADC has no reset bit in `SYS_CTRL0` and keeps its
setup. After `run`, `dac-read 0x03` shows which state the DAC is in: it prints
`0x1` when initialized (byte mode), `0x0` at power-on defaults, and `0xff` if
the DAC isn't answering on SPI. Don't use it while the DAC is still held in
reset after `reset`: its SPI path is dead then, and `dac-read` doesn't check
`SYS_CTRL0` bit 4 the way `dac-init` does.

---

## `iza_sender.py` — waveform replay (PC → board)

Pushes a recorded or generated waveform to the board's replay input (port 7200),
servoing its send rate from the board's telemetry (port 7201) toward ~50 % ring
fill. Use it to drive the analog pipeline with real lab signals or a synthetic
tone.

```bash
python iza_sender.py Test_Signal.txt --board 192.168.0.80 --loop
python iza_sender.py --board 192.168.0.80 --gen sine --gen-freq 1000 --gen-amp 0.5
```

Key options: `--gen {sine,ramp,dc}` with `--gen-freq/--gen-amp/--gen-seconds`;
`--src-rate` + resampling to the board rate (`--no-resample`, or `--hq` for
scipy polyphase — numpy linear is the default and avoids a scipy import hang on
Python 3.14); `--loop`; `--seconds`; `--save`; `--sync-file`.

---

## `iza_receiver.py` — capture the data stream to disk

UDP sink for the measurement stream (port 7100): writes raw datagrams to a
`.bin` capture and reports sequence gaps, drops, and timestamp uniformity.

```bash
python iza_receiver.py --port 7100 --out capture.bin --sample-rate 200000 --seconds 60
```

---

## `iza_plotter.py` — live real-time scope

Live plot of the incoming demod stream (the CLI counterpart to the GUI Scope
tab). `--decimate` thins points for speed; `--ref <stem>_adc_int16.bin` overlays
a recorded raw-ADC reference on channel 0; `--window` sets the time span.

```bash
python iza_plotter.py --port 7100 --window 3.0 --decimate 10
```

---

## `iza_sweep.py` — frequency-response sweep

Steps one tone across log-spaced frequencies (default 500 kHz–40 MHz, 40
points, channel 0) at a low amplitude (default 5 %). At each point it averages
the demod output x + jy and divides by the amplitude used, so the result is
"demod output per unit DAC full-scale amplitude".

**Before you run it.**
- Close the GUI first, because it holds UDP 7100.
- The board must be running with both converters initialized (GUI: Start,
  then Initialize DAC + ADC; CLI: `run`, `dac-init`, `adc-init`). The sweep
  refuses if the instrument is stopped, the DAC is in reset or uninitialized,
  the demod input or DAC output mux is not at its normal setting, or the ADC
  looks uninitialized. For that check the sweep probes the raw ADC with the
  tones off: an uninitialized ADC's offset-binary output, read as two's
  complement, sits near ± full scale with no over-range, while an initialized
  one reads a few LSB.
- Bad arguments (including `--port` outside 1–65535), a bad `--open`/`--ref`
  file, or an output that can't be written are reported before the board is
  touched. That covers a read-only folder, or a CSV held open without write
  sharing, as Excel does. A missing output folder is created. If a program
  that does allow writing (a viewer, OneDrive) holds the CSV, it is
  overwritten in place.

**What it changes on the board.**
- **Triggering is disarmed** at the start. Frequency and amplitude steps look
  like events, and the sweep's traffic would keep the trigger watchdog fed.
  The sweep can't re-arm it afterwards.
- **The tone, channel-mask and packet registers it touched are restored** when
  it finishes, including after an error or Ctrl-C. A second Ctrl-C during the
  restore is ignored, and console errors (e.g. output piped to `head`) can't
  skip it. The channel mask is restored first, so the swept channel never
  plays its old amplitude under the sweep's mask. If the mask can't be
  restored and that tone was off before, its register is left at the sweep's
  low amplitude instead.
- **Control datagrams are retried** (UDP can lose one), and a short data stall
  is retried once. If the sweep still fails part-way, the points measured so
  far are saved, with a `# aborted = …` line.

**Exit codes.**

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | The sweep aborted part-way (its points are saved), the board settings were not fully restored, or de-embedding or the plot failed |
| 2 | The requested CSV could not be written: it was **not** updated, and the rows are in a `sweep_rescued_*.csv` in the temp folder (the path is printed) |

**Clipping guards.**
- **ADC peak.** The raw-ADC monitor and the over-range flag carry one ADC
  sample per record. A tone that is a multiple of the record rate (200 kHz at
  R = 1000, e.g. 15 or 25 MHz) would be sampled at the same point of its cycle
  in every record, which can hide its peaks. So each point uses the nearest
  grid frequency, inside `--start`/`--stop`, whose snapshot walks through 16
  points of the cycle. (If a narrow range has no such grid point, the nearest
  one outside is used and a note is printed.) The raw ADC is streamed, and a
  point's peak must stay below `--max-peak` (default 0.5 of full scale,
  −6 dBFS) with no over-range flags. Otherwise the amplitude is lowered (down
  to `--min-amp`, default 0.25 %) and the point is measured again. Above
  40 MHz the DAC's interpolation image alternates sign between ADC samples,
  so the peak limit applies to every other sample. The rest are guarded only
  by the over-range flag, at full scale.
- **Linearity.** On by default; `--no-linearity` skips it and is twice as
  fast. Each point is measured again at half amplitude, and the two normalized
  results must agree within `--lin-tol` (default 1 %) or within noise. If the
  half-amplitude window did not settle, the point is flagged `unsettled` and
  gets no linearity verdict.
- **Settling.** If the first and second halves of a point's window disagree
  beyond noise, it is measured again with a 4× longer settle. The noise
  estimate is built so that neither a transient nor a drift can inflate it.

**Flags (CSV `flags` column, red × on the plot).**

| Flag | Meaning |
|---|---|
| `headroom` | still above the peak limit at the minimum amplitude |
| `nonlinear` | failed the linearity check |
| `unsettled` | did not settle |
| `low-snr` | the signal (or the de-embedded result) is under 3× its standard error |
| `below-hpf` | the point is below 400 kHz |
| `dac-filter` | the point is above 40 MHz, past the DAC's 2× interpolation filter (see the peak-check note above) |
| `interp` | de-embedding had to interpolate the open/reference sweep |
| `open:…` / `ref:…` | the open / reference sweep's point used here was `headroom`, `nonlinear` or `unsettled` (its noise is in `d_se` instead) |

**De-embedding.** First sweep the fixture with the load removed (`--out
open.csv`). Then sweep with the load and `--open open.csv`, which subtracts the
fixture coupling point by point. `--ref ref.csv` also divides by a sweep of a
known reference load: the result is (H − H_open) / (H_ref − H_open). Its
first-order standard error is in the `d_se` column (it includes the open and
reference sweeps' noise). Measurement problems on the open or reference point
carry over as `open:…`/`ref:…` flags. Use the same
`--start/--stop/--points` for every sweep so the frequencies match.
`--analyze` redoes the de-embedding offline from saved CSVs. It needs `--open`
and/or `--ref`, and discards any earlier de-embedding stored in the file.

Each run writes a CSV (with `#` metadata lines) and a magnitude/phase PNG.
The plot title shows the fitted delay, and `--remove-delay` plots the phase
with that delay removed.

```bash
python iza_sweep.py --board 192.168.0.80 --amp 5 --out open.csv     # fixture, load removed
python iza_sweep.py --board 192.168.0.80 --amp 5 --open open.csv --out load.csv
python iza_sweep.py --analyze load.csv --open open.csv --ref ref.csv  # offline
```

---

## Offline analysis tools

| Tool | Purpose | Example |
|---|---|---|
| `iza_view.py` | plot a captured `.bin` (or ziBin) file; `--save` to PNG | `python iza_view.py capture.bin --zoom-ms 50` |
| `iza_validate.py` | validate a capture — recover the injected tone, check framing/timestamps | `python iza_validate.py capture.bin --msg-freq 100 --plot` |
| `ts_diag.py` | timestamp-delta diagnostics / histogram over a capture | `python ts_diag.py capture.bin --bucket 50` |
| `iza_packet.py` | shared parser library (`parse_header`, `deinterleave`, scaling) — imported, not run | — |

All offline tools default `--pl-clk` to `iza_packet.PL_CLK_HZ` (200 MHz-equivalent,
5 ns/count) and accept `--chan-mask`/`--channel` to select a layout or channel.
