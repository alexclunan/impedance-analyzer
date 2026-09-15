# Operator Quick-Start

Get from a powered-off board to a live measurement, a recording, and an armed
trigger. Assumes the board is flashed and on the network at `192.168.0.80`, and
you have `petalinux_overlay/pc/` with Python 3 + `PySide6`/`pyqtgraph`/`numpy`.

## 1. Power on and connect
Power the board and confirm the link:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.0.80 'uptime'
```

`iza_replay` normally starts at boot; if not, start it on the board.

## 2. Initialize (required every startup)
The DAC and ADC output garbage until initialized after each power cycle. In the
GUI **Control** tab, click **① Initialize DAC + ADC**. Equivalent CLI:

```bash
cd petalinux_overlay/pc
python iza_ctrl.py --board 192.168.0.80 run       # release resets + run (also frees the DAC SPI)
python iza_ctrl.py --board 192.168.0.80 dac-init   # AD9122 (2x interp) — needs 'run' first
python iza_ctrl.py --board 192.168.0.80 adc-init   # AD9467
```

## 3. Set up the excitation and channels
Pick carrier(s) above 400 kHz on the 12.5 kHz grid, and enable channels. The
GUI's **Quick setup** / **Apply balanced setup** do this and keep the DAC from
clipping. CLI equivalent (single tone, 4 demod channels):

```bash
python iza_ctrl.py --board 192.168.0.80 carrier 1e6     # ch0 = 1 MHz
python iza_ctrl.py --board 192.168.0.80 channels 0xF     # enable 4 demod channels, auto-balance, size packets
python iza_ctrl.py --board 192.168.0.80 pga 12           # input gain (dB)
```

## 4. Measure
Launch the GUI and watch the **Scope** / **Numeric** tabs:

```bash
python -m iza_gui
```

Or use the CLI live plotter: `python iza_plotter.py --port 7100 --window 3`.

## 5. Record
Choose a **Rec rate** in the connection bar — pick a preset (Full ~200 kHz down
to ~200 Hz) or type any rate (e.g. `5 kHz`, `7500`) — and click **Record**. Files land in
`iza_<timestamp>/D1/Freq<N>.ziBin` with a `meta.json`. Record raw ADC at full
rate only (decimation aliases it). See `gui-user-guide.md`.

## 6. Trigger (optional)
Arm soft (no-pin) first to tune thresholds while watching the event log, then
switch to hardware. From the GUI **Triggering** tab, or CLI:

```bash
python iza_ctrl.py --board 192.168.0.80 trig-soft --ampch 0 --thr 0.02 --mindiff 0.03
python iza_ctrl.py --board 192.168.0.80 trig-off      # when done
```

Full detail: `triggering-guide.md`.

## Shutdown
Disarm triggering (`trig-off`), stop recording, then `reset` for a clean stop
(it drops `run` gracefully before asserting resets):

```bash
python iza_ctrl.py --board 192.168.0.80 reset
```

## Troubleshooting
- **Garbage / no signal:** re-run `dac-init`/`adc-init` (needed every power cycle;
  `dac-init` needs `run` first).
- **Dropped samples warning:** lower the Rec rate or reduce plotted channels; the
  GUI drops UDP under heavy draw load on slow PCs.
- **No response from board:** confirm `iza_replay` is running and the IP is right.
- **Nothing changed after an FPGA edit:** you may be on a stale bitstream — see
  `fpga-developer-guide.md`.
