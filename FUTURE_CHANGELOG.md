# Future Changelog

Planned changes that are not released yet. Entries that are built but not yet
committed or bench-tested sit under **Implemented**. When an entry ships, move
it into the release notes and delete it here.

## Planned

### GUI: auto-initialize the converters on Start

**Status:** planned · **Area:** `pc/iza_gui/control_panel.py` · **Added:** 2026-09-30

When the DAC chip was held in reset, have **▶ Start** run `dac_init(2)` +
`adc_init()` automatically, with a setting to turn this off. This was the
optional item 4 of the re-initialization warning below. Only do it when
`SYS_CTRL0` bit 4 was 0 before `run()`: `run()` leaves the reset bits alone on a
board that is already running, so a blanket rule would re-initialize a working
DAC.

### GUI: kHz/MHz entry for the FIR cutoff

**Status:** planned · **Area:** `pc/iza_gui/filter_panel.py` · **Added:** 2026-09-30

Use `widgets.FreqSpinBox` (with `decimals=2`) for the Filter tab's
**Cutoff (-3 dB)** box, which is still a plain ` Hz` spin box. This was the
optional item of the frequency-entry change below. Check that the box's
`setMaximumWidth(130)` still fits the longest text.

## Implemented

### GUI: warn when the DAC needs re-initialization

**Status:** implemented 2026-09-30, not yet committed or bench-tested ·
**Area:** `pc/iza_gui` · **Added:** 2026-09-30

**Problem.** Whenever `SYS_CTRL0` (AXI reg 0) bit 4 (`dac_chip_nreset`) is 0,
the AD9122 is held in reset and its SPI registers return to power-on defaults.
`reset_all()` clears bits 0–5 but keeps the routing bits 6 and 8, so
`SYS_CTRL0` reaches `0x00` only if those bits were already 0. This happens on
**⏹ Stop / Reset** and `iza_ctrl.py reset`. A power cycle resets the DAC anyway,
because the chip loses power. A board reboot or an `iza_replay` restart
presumably does the same, but that can't be verified here: it depends on the PL
register file's reset value and on the firmware's `pl_configure`, and neither
source is in this repo. After the reset the DAC is in word mode instead of byte
mode, and its interpolation and FIFO alignment are lost. **▶ Start** releases the reset but
does not re-run `dac_init`, and nothing in the GUI showed that the DAC was now
unconfigured. The instrument read RUNNING while the TX output was wrong.

**Seen on 2026-09-30** (330 kΩ TX→RX bench test):
- Tone off: SMA1 sat at about +3.35 V DC (≈96 % of TX full scale) instead of 0 V.
- Tone on: the TX was a one-sided band, not a sine centred on ground.
- RX: near-continuous ADC over-range and incoherent demod output (ch0 ≈ 1e-3
  FS, random phase).

Everything cleared after **① Initialize DAC + ADC**: SMA1 at 0 V with the tone
off, ch0 steady at ≈ 0.005 FS at 100 % amplitude, and over-range off.

**Implemented as.**
- The 1 s status poll (`control_client.read_status`) also reads AD9122 reg
  `0x03` (Data format) whenever `SYS_CTRL0` bit 4 is 1, and emits it on a new
  `ControlClient.dac_format` signal. `0x01` = byte mode (init in place),
  `0x00` = power-on defaults, `0xFF` = not answering.
- `dac_state.DacInitTracker` (Qt-free) turns the polls and the GUI's own
  `reset` / `dac-init` results into a state:
  - **OK** after a clean init, or when the probe reads byte mode (this also
    covers an init done from the CLI);
  - **needs init: held** while bit 4 is 0, or after the GUI's Stop / Reset.
    The advice is "▶ Start, then ① Initialize";
  - **needs init: lost its setup** once the chip is released again without an
    init (the 0 → 1 edge), or when the probe reads word mode;
  - **needs init: not answering** for a `0xFF` probe;
  - **suspect** when an init fails on the board link (for example a lost reply)
    or its FIFO-alignment checks don't pass. An init refused because the chip
    is held in reset shows **held** instead. Byte-mode probes don't clear
    suspect, and nor does a not-answering spell. Within one connection it ends
    only with a clean init, or gives way to **held** (Stop / Reset, or bit 4 =
    0). A Disconnect / Connect forgets it, so the next byte-mode probe shows
    **OK** without an init.
- Shown in three places: an LED and text under **① Initialize**, a permanent
  status-bar warning that names the next step, and one command-log line per
  change. An "ok" line is logged when the warning clears.
- While the control link is down (for example a board reboot), an OK indicator
  greys to "unknown (no control link)". Warnings stay up.
- Results that arrive after Disconnect, or from an older connection, are now
  dropped (`ControlClient` connection generation). This also stops a late poll
  from turning the link LED green after Disconnect.

**Differences from the original proposal.**
- The state lives in `ControlPanel` + `dac_state`, not in `ControlClient`.
- "Needs init after the GUI's own `run`" is done only as the held → lost
  transition above, never on every `run`: `run()` leaves a running board's DAC
  alone, so a blanket rule would raise false warnings.
- A `0xFF` probe is reported as "not answering" rather than "still held in
  reset". Bit 4 is already 1 whenever the probe runs.
- Item 4 (auto-initialize on Start) moved to **Planned**.

**Tests.** `pc/tests/test_dac_state.py` (tracker),
`pc/tests/test_gui_wiring.py` (probe with a mocked controller, stale-result
dropping, the panel / status bar / log through an offscreen `MainWindow`, and
the real worker thread end to end against a simulated board).

### GUI: enter tone frequencies in Hz, kHz or MHz

**Status:** implemented 2026-09-30, not yet committed or bench-tested ·
**Area:** `pc/iza_gui` · **Added:** 2026-09-30

**Problem.** The Tone 0–3 **Frequency** boxes were plain `QDoubleSpinBox`es with
a fixed ` Hz` suffix, so 1 MHz had to be typed as `1000000`. The snapped
readout beside each box also stayed in kHz above 1 MHz (`→ 1000.0 kHz`).

**Implemented as.**
- `widgets.FreqSpinBox` replaces the four boxes. It accepts `750000`, `500k`,
  `500 kHz`, `1.5M`, `1.5 MHz` or `2e6`, case-insensitive. A bare number is Hz,
  and `m` means mega.
- It shows the value in the most readable unit (`500 kHz`, `1.0125 MHz`), exact
  on the 12.5 kHz grid.
- Unchanged: the 0–8 MHz range, one 12.5 kHz step per arrow click or scroll,
  snapping on `editingFinished`, and the values loaded back from the board.
- Out-of-range entries clamp to the range. Text that isn't a frequency (`2e`,
  `abc`, empty) reverts to the value from before the edit. A half-typed unit
  (`500 kH`) is completed.
- Only the finished text is committed (keyboard tracking off), so the `2` of
  `2e6` is never sent along the way.
- In a comma-decimal locale, `,` is the decimal mark (`1,5 MHz`), matching the
  other spin boxes. `.` grouping is understood there too (`1.000,5 kHz`,
  `1.000.000`). A lone `.` still reads as a decimal point.
- The arrows step from the typed text even before it is committed, including
  away from the 0 Hz and 8 MHz ends of the range.
- The snapped readout switches to MHz from 1 MHz up (`→ 1.0000 MHz`).
- One shared parser, `units.py`, serves both these boxes and the **Rec rate**
  box (`search_hz`, which reads the presets such as `100 kHz  (÷2)` as
  before). It never raises: an absurd exponent becomes infinity, which then
  clamps.

**Differences from the original proposal.** The parser lives in `units.py`
rather than `widgets.py`. The FIR cutoff item moved to **Planned**.

**Tests.** `pc/tests/test_units.py`: the parser and formatter, plus the widget
driven by real key clicks, including the comma locale.
