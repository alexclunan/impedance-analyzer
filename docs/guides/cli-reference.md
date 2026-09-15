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
| `reset` | — | graceful stop then hold all resets (preserves routing bits) |
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

**Startup ordering (required every boot):**

```bash
python iza_ctrl.py --board 192.168.0.80 run          # release resets, enable run
python iza_ctrl.py --board 192.168.0.80 dac-init      # AD9122 (needs run first)
python iza_ctrl.py --board 192.168.0.80 adc-init      # AD9467
python iza_ctrl.py --board 192.168.0.80 channels 0xF  # enable 4 demod channels
```

Without `dac-init`/`adc-init` after a power cycle the converters emit garbage.

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

## Offline analysis tools

| Tool | Purpose | Example |
|---|---|---|
| `iza_view.py` | plot a captured `.bin` (or ziBin) file; `--save` to PNG | `python iza_view.py capture.bin --zoom-ms 50` |
| `iza_validate.py` | validate a capture — recover the injected tone, check framing/timestamps | `python iza_validate.py capture.bin --msg-freq 100 --plot` |
| `ts_diag.py` | timestamp-delta diagnostics / histogram over a capture | `python ts_diag.py capture.bin --bucket 50` |
| `iza_packet.py` | shared parser library (`parse_header`, `deinterleave`, scaling) — imported, not run | — |

All offline tools default `--pl-clk` to `iza_packet.PL_CLK_HZ` (200 MHz-equivalent,
5 ns/count) and accept `--chan-mask`/`--channel` to select a layout or channel.
