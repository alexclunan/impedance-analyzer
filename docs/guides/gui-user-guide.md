# GUI User Guide (`iza_gui`)

`iza_gui` is the PySide6 / pyqtgraph desktop application for operating the
instrument — a LabOne-style front end over the same `iza_ctrl` control client and
UDP data stream the CLIs use.

```bash
cd petalinux_overlay/pc
python -m iza_gui
```

Requires `PySide6`, `pyqtgraph`, and `numpy`.

## Architecture

| Module | Role |
|---|---|
| `app.py` | main window, tabs, connection bar, stats |
| `data_stream.py` | UDP 7100 ingest (background thread → bounded queue → GUI-thread drain) |
| `control_client.py` | wraps `iza_ctrl.IzaCtrl`; verified register writes; trigger-event receiver (7203) |
| `recorder.py` | streams to ziBin on disk, with optional decimation |
| `*_panel.py` | the individual tabs |

The receive thread does the absolute minimum (header unpack + enqueue); the
GUI-thread timer bulk-parses batches. This keeps the kernel socket drained so the
link doesn't drop packets under drawing load.

> **Screenshots needed.** Add an annotated screenshot of each tab under
> `docs/reference-manual/figures/` (or inline here); they can't be captured from
> a running GUI automatically.

## Connection bar

Top of the window: board IP/connect, live stats (records/s, Mbit/s, link alive),
an instrument-wide over-range LED, a dropped-samples warning (turns red with a
count), the **Record** button, and the **Rec rate** decimation selector.

## Tabs

### Control
Drives the instrument through `iza_ctrl`:
- **System:** the **① Initialize DAC + ADC** button (must be run every startup or
  the converters output garbage) with a warning banner; `run`/`reset`.
- **Signal output:** per-tone frequency and amplitude; **Quick setup** (up to 3
  tones); **Apply balanced setup** (enables channels and applies even, non-clipping
  amplitudes, reflected in the amplitude fields); the DAC output-level bar.
- **Muxes:** demod input (ADC vs loopback, `SYS_CTRL0[6]`) and DAC output (tones
  vs test/replay, `SYS_CTRL0[8]`); PGA gain; DAC interpolation (default 2×).
- **FIR filter:** set a low-pass **Cutoff** and *Design + load* a 127-tap
  symmetric linear-phase filter live, or *Upload .coe* to load your own
  coefficients (optional CIC-droop compensation). Requires the reloadable-FIR
  bitstream; see the FPGA developer guide.

### Scope
Real-time traces of demod magnitude/phase (and raw ADC when enabled):
- **Counts toggle** — display raw 32-bit counts vs normalized full scale.
- **Threshold overlay** — draws the trigger amplitude threshold on the demod plot
  so you can see which peaks would fire (these lines are excluded from autorange
  so they never blow out the Y bounds).
- **Trigger markers** — fired events appear as points on the timeline.
- **Plot show/hide** checkboxes (only show plots in use); **pop-out** a single
  plot into its own window.

### Numeric
Large LabOne-style metric cards per channel with a persistence "histogram" bar
(fading blocks at each polled value, with Min/Max labels) — good for reading a
steady value at a glance. Only channels in use are shown.

### Triggering
Configure, arm, and monitor the trigger engine (see `triggering-guide.md`):
mode/arm, safety watchdog, test-fire buttons, amplitude thresholds (raw counts
with %FS hints), per-channel phase classification, fire timing (fixed/velocity),
a scrolling **event log** with per-event timing, run statistics, and load/save of
a calibration JSON. Auto-disarms on link loss.

### Registers
Browse/read/write the FPGA, AD9122, and AD9467 register spaces with per-register
descriptions and bitfield decoders (from `register_map.py`; TRM ch. 4).

### Console
A Vivado-Tcl-style log of every command issued and its result, including
register-write read-back verification and trigger events.

## Recording

Click **Record** to stream the relative differential admittance to disk. Each
session has a unique `iza_<timestamp>_<suffix>/D1/` directory:

- `Freq<N>.ziBin`: **Relative differential admittance**, the `x + jy` values
  with unchanged scaling and the seven-column big-endian float64 layout
  (TRM ch. 3, §ziBin).
- `Freq<N>.validity.bin`: one unsigned byte per `Freq<N>.ziBin` row. Zero means
  valid; bit 1 means nonfinite input or negative magnitude, and bit 2 means ADC
  over-range. Flags can be combined. Flagged rows are **written unchanged** —
  the sidecar only marks them. Analysis should exclude flagged rows rather than
  treating them as measured peaks or interpolating across them without an
  explicit rule.
- `meta.json`: quantity labels, file paths, validity definitions/counts,
  recording state and accepted/written/rejected record counts. Existing
  `zi_meta`, `channels` and `scaling` fields remain available for older
  readers. All relative file paths are based at `D1/`. Recording status shows
  flagged-row counts.

No impedance file is recorded. The front end is differential, so
`x + jy ∝ I₁ − I₂`, and `1/(x + jy)` is not the impedance of any element (TRM
ch. 2, "Physical quantity"). Only in a **single-path** configuration — one
sense input open, e.g. bench calibration against a known component — is the
reciprocal a relative impedance. Compute it after the fact from the recording:

```python
rec = np.fromfile("Freq1.ziBin", dtype=">f8").reshape(-1, 7)
ok = np.fromfile("Freq1.validity.bin", dtype="u1") == 0
z_rel = 1 / (rec[ok, 1] + 1j * rec[ok, 2])   # relative (K = 1); single-path only
```

Conversion and file writes run on a separate worker. The input queue is bounded
by 32 MiB and 128 batches, including a batch in progress in the byte budget.
A slow/full disk or queue overflow stops recording and reports an error in the
status bar and console; it does not block live controls. On an ordinary stop,
already accepted batches are drained asynchronously. Wait for **Recording
saved** before using the completed files. Files are kept aligned by rolling
back an incomplete batch after a write failure; a rollback failure is reported
explicitly and only metadata's committed prefix should be trusted. Metadata is
checkpointed about once per second and finalized as `complete` or `failed`.
An interrupted session can remain marked `recording`; checkpoints are not a
power-loss durability guarantee. On writer failure, metadata counts the
accepted but unwritten records. These counters cover the recorder queue, not
UDP loss before the data reaches the recorder.

Demod recording at four channels and 200 krecords/s needs about **45.6 MB/s**
(44.8 MB/s ziBin + 0.8 MB/s validity), plus raw ADC if enabled. Set an
appropriate recording rate for the disk. The **Rec
rate** field decimates before writing, cutting file size proportionally. It is an
editable combo: pick a preset (Full ~200 kHz down to ~200 Hz) **or type any rate**
— e.g. `5 kHz`, `7500`, `200 Hz`. The requested rate is rounded to the nearest
whole division of the ~200 kHz native rate; the status bar reports the actual
achieved rate on start (and `meta.json` records the decimation factor). A rate
above native clamps to full rate. Decimation is uniform and phase-continuous but
unfiltered — fine for the narrowband demod x/y, but the raw-ADC stream will alias
if decimated, so record ADC at full rate if you need it faithful.
