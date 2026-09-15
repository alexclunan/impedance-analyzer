"""Filter tab — design the CIC + FIR demod decimation filter and load it.

Wraps fir_design.make_filter(): you give a -3 dB cutoff and the designer picks
the CIC rate, tap count and method, or you pin any of them. The response, group
delay and step response are plotted, every number the loader and the PC need is
shown, and "Design + Load" streams the coefficients to the board over REG3.

HARDWARE PROFILE
----------------
The knobs are clamped to what the built bitstream can actually accept, so the
panel cannot design something that would load wrong. Edit HW_PROFILE after an
FPGA rebuild - it is the single place the GUI's idea of the hardware lives.

Two entries in it are worth understanding:

  frame / symmetric   The FIR Compiler's tap count and whether it folds. A
                      folded (C_SYMMETRY=1) build cannot take a latency-mode
                      design: that design is a short symmetric block
                      left-justified in the frame, symmetric about its own
                      centre but not the frame's, which is exactly what makes
                      its delay (M-1)/2 instead of (frame-1)/2.

  ncoef               fir_coeff_loader's buffer depth. It streams exactly NCOEF
                      values per commit and its write pointer SATURATES past the
                      end, so pushing the wrong count is not an error on the
                      board - it silently loads a different filter. The panel
                      always sends the full padded frame for this reason.

  rate_settable       There is no CIC rate register yet, so R cannot be applied
                      from here. Designs at a different R are allowed (they are
                      what the rate register will enable) but loading one warns,
                      because only the coefficients reach the board.
"""

import os

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

import fir_design as fd

from . import theme
from .widgets import labeled_row

# --------------------------------------------------------------------------
# What the built bitstream can accept. Update after an FPGA rebuild.
# --------------------------------------------------------------------------
HW_PROFILE = {
    "frame": fd.TAPS_DEFAULT,       # FIR Compiler NUM_TAPS
    "symmetric": False,             # C_SYMMETRY (False -> latency mode allowed)
    # HARDCODED 999: fir_coeff_loader.v NCOEF, fir_design.LOADER_NCOEF and
    # iza_ctrl.FIR_NCOEF all carry this same number and must agree.
    "ncoef": 999,
    "width": fd.WIDTH,              # coefficient width
    "rate_current": 1000,           # the R the bitstream is running
    "rates_supported": list(fd.RATES),
    # The rate now rides REG3[30:18] on the commit, so a design at any
    # supported R can be applied from here.
    "rate_settable": True,
    "channels": 4,                  # the loader broadcasts to all demod chains
}


def current_output_hz():
    """CIC output rate (= native record rate) for the R the bitstream runs.

    The demod stream leaves the board at 200 MHz / R, so nothing downstream can
    be recorded faster than this. fir_load() applies the rate on the commit, so
    _load() keeps HW_PROFILE['rate_current'] in step and this stays accurate."""
    return fd.fs_for_rate(HW_PROFILE["rate_current"])


CUTOFF_MIN, CUTOFF_MAX = 11.0, 10000.0


class _DesignWorker(QtCore.QThread):
    """Run make_filter() off the UI thread - a latency search can take ~10 s."""

    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, kwargs, parent=None):
        super().__init__(parent)
        self._kwargs = kwargs

    def run(self):
        try:
            self.done.emit(fd.make_filter(**self._kwargs))
        except Exception as e:                      # noqa: BLE001 - report to UI
            self.failed.emit(str(e))


class FilterPanel(QtWidgets.QWidget):
    """Design, inspect and load the demod decimation filter."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.filter = None          # the last successful design
        self.loaded = None          # the design actually on the board
        self._worker = None
        self._build_ui()
        self._on_mode_changed()
        self.design()               # show something useful immediately

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        left = QtWidgets.QVBoxLayout()
        left.setSpacing(8)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self._build_spec())
        left.addWidget(self._build_structure())
        left.addWidget(self._build_actions())
        left.addWidget(self._build_readout(), 1)
        inner = QtWidgets.QWidget()
        inner.setLayout(left)
        # The column is taller than a short window: scroll it rather than
        # crushing the readout, which is the part you actually read off.
        holder = QtWidgets.QScrollArea()
        holder.setWidgetResizable(True)
        holder.setWidget(inner)
        holder.setFrameShape(QtWidgets.QFrame.NoFrame)
        holder.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        holder.setMinimumWidth(348)
        holder.setMaximumWidth(400)
        root.addWidget(holder)

        root.addWidget(self._build_plots(), 1)

    def _spin(self, lo, hi, val, step, suffix="", decimals=0):
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSingleStep(step)
        s.setDecimals(decimals)
        if suffix:
            s.setSuffix(suffix)
        s.setMaximumWidth(130)
        return s

    def _build_spec(self):
        box = QtWidgets.QGroupBox("Specification")
        lay = QtWidgets.QVBoxLayout(box)
        lay.setSpacing(6)

        self.cutoff = self._spin(CUTOFF_MIN, CUTOFF_MAX, 250, 10, " Hz", 2)
        self.cutoff.setToolTip(
            "The -3 dB point of the finished filter. The designer solves for "
            "whatever design cutoff lands -3 dB here, so this is what you "
            "measure, not a nominal value.")
        lay.addWidget(labeled_row("Cutoff (-3 dB)", self.cutoff))

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["Quality (sharpest)", "Latency (fastest)"])
        self.mode.setToolTip(
            "Quality uses the whole tap frame for the sharpest transition; "
            "group delay is then fixed by the frame.\n"
            "Latency uses the fewest taps meeting the shape spec and "
            "left-justifies them, so the delay drops in proportion.")
        self.mode.currentIndexChanged.connect(self._on_mode_changed)
        lay.addWidget(labeled_row("Mode", self.mode))

        self.shape = self._spin(1.5, 20.0, 3.0, 0.5, " : 1", 2)
        self.shape.setToolTip(
            "Latency mode only: required f_stop / f_3dB. This is the latency "
            "knob - delay is set by the transition width, so a looser shape is "
            "a faster filter. 3:1 is a reasonable default.")
        self.shape_row = labeled_row("Shape", self.shape)
        lay.addWidget(self.shape_row)

        self.atten = self._spin(20, 100, 80, 5, " dB", 0)
        self.atten.setToolTip(
            "Stopband attenuation target. Cheapest knob you have: the "
            "transition width scales with (atten - 8), so dropping 80 -> 60 dB "
            "buys ~27% narrower transition or a lower reachable cutoff.")
        lay.addWidget(labeled_row("Stopband", self.atten))

        self.cic_comp = QtWidgets.QCheckBox("Compensate CIC droop")
        self.cic_comp.setToolTip(
            "Pre-emphasize the passband by 1/sinc^4 to flatten the CIC's droop. "
            "Worth it above ~1 kHz (0.09 dB across a 10 kHz passband, ~1% "
            "amplitude); below that the droop is under 0.001 dB and this only "
            "costs transition width.")
        lay.addWidget(self.cic_comp)
        return box

    def _build_structure(self):
        box = QtWidgets.QGroupBox("Structure")
        lay = QtWidgets.QVBoxLayout(box)
        lay.setSpacing(6)

        self.rate = QtWidgets.QComboBox()
        self.rate.addItem("Auto", None)
        for r in HW_PROFILE["rates_supported"]:
            self.rate.addItem(f"{r}  ({fd.fs_for_rate(r)/1e3:g} kHz out)", r)
        self.rate.setToolTip(
            "CIC decimation R. Lower R is lower latency and a higher output "
            "rate; higher R reaches lower cutoffs with the same taps.\n"
            "Auto picks the lowest R that meets the spec.")
        lay.addWidget(labeled_row("CIC rate", self.rate))

        self.taps = QtWidgets.QComboBox()
        self.taps.addItem("Auto", None)
        n = HW_PROFILE["frame"]
        for t in sorted({n, 501, 255, 127, 63, 31}):
            if t <= n:
                self.taps.addItem(str(t), t)
        self.taps.setToolTip(
            f"Tap count. The frame is {n}; a shorter design is left-justified "
            f"with trailing zeros so it runs at lower delay.")
        lay.addWidget(labeled_row("Taps", self.taps))

        self.method = QtWidgets.QComboBox()
        self.method.addItem("Auto (better of the two)", None)
        self.method.addItem("Equiripple (remez)", "remez")
        self.method.addItem("Windowed sinc (Kaiser)", "kaiser")
        self.method.setToolTip(
            "Equiripple reaches a narrower transition for the same taps; the "
            "window design is more predictable. Both are Type-I symmetric, so "
            "phase stays exactly linear either way.")
        lay.addWidget(labeled_row("Method", self.method))

        prof = (f"frame {HW_PROFILE['frame']} · "
                f"{'folded' if HW_PROFILE['symmetric'] else 'non-symmetric'} · "
                f"loader {HW_PROFILE['ncoef']} · R={HW_PROFILE['rate_current']}"
                f"{'' if HW_PROFILE['rate_settable'] else ' (fixed)'}")
        lbl = QtWidgets.QLabel("Hardware: " + prof)
        lbl.setProperty("dim", True)
        lbl.setWordWrap(True)
        lbl.setToolTip(
            "What the built bitstream accepts. The knobs above are limited to "
            "this. Edit HW_PROFILE in filter_panel.py after an FPGA rebuild.")
        lay.addWidget(lbl)
        return box

    def _build_actions(self):
        box = QtWidgets.QGroupBox("Actions")
        lay = QtWidgets.QVBoxLayout(box)
        lay.setSpacing(6)

        row1 = QtWidgets.QHBoxLayout()
        self.btn_design = QtWidgets.QPushButton("Design")
        self.btn_design.setToolTip("Design and plot it, without touching the board.")
        self.btn_design.clicked.connect(self.design)
        self.btn_load = QtWidgets.QPushButton("Design + Load")
        self.btn_load.setProperty("accent", True)
        self.btn_load.setToolTip(
            "Design it and stream the coefficients to the FPGA over REG3.")
        self.btn_load.clicked.connect(self._design_and_load)
        row1.addWidget(self.btn_design)
        row1.addWidget(self.btn_load)
        lay.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_coe = QtWidgets.QPushButton("Save .coe…")
        self.btn_coe.clicked.connect(self._save_coe)
        self.btn_cfg = QtWidgets.QPushButton("Save config…")
        self.btn_cfg.setToolTip(
            "Write the loader payload as JSON: CIC rate, gain shift, delay. The "
            "delay especially - the PC must subtract it from measured phase, "
            "and it changes with every design.")
        self.btn_cfg.clicked.connect(self._save_config)
        row2.addWidget(self.btn_coe)
        row2.addWidget(self.btn_cfg)
        lay.addLayout(row2)

        self.btn_open = QtWidgets.QPushButton("Load .coe…")
        self.btn_open.setToolTip(
            "Load coefficients from an existing .coe and send them to the board.")
        self.btn_open.clicked.connect(self._open_coe)
        lay.addWidget(self.btn_open)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        return box

    def _build_readout(self):
        box = QtWidgets.QGroupBox("Result")
        lay = QtWidgets.QVBoxLayout(box)
        self.readout = QtWidgets.QTreeWidget()
        self.readout.setColumnCount(2)
        self.readout.setHeaderLabels(["", ""])
        self.readout.setRootIsDecorated(False)
        self.readout.setHeaderHidden(True)
        self.readout.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents)
        self.readout.setAlternatingRowColors(True)
        self.readout.setMinimumHeight(330)
        self.readout.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        lay.addWidget(self.readout)
        return box

    def _build_plots(self):
        tabs = QtWidgets.QTabWidget()

        self.p_mag = pg.PlotWidget()
        self.p_mag.showGrid(x=True, y=True, alpha=0.3)
        self.p_mag.setLabel("bottom", "Frequency", units="Hz")
        self.p_mag.setLabel("left", "Magnitude", units="dB")
        self.p_mag.addLegend()
        self.c_fir = self.p_mag.plot(pen=pg.mkPen(theme.ACCENT, width=2),
                                     name="FIR")
        self.c_cic = self.p_mag.plot(
            pen=pg.mkPen(theme.WARN, style=QtCore.Qt.DashLine), name="CIC")
        self.c_tot = self.p_mag.plot(pen=pg.mkPen(theme.TEXT, width=1),
                                     name="CIC x FIR")
        self.l_f3 = pg.InfiniteLine(angle=90, movable=False,
                                    pen=pg.mkPen(theme.GOOD,
                                                 style=QtCore.Qt.DotLine))
        self.p_mag.addItem(self.l_f3)
        tabs.addTab(self.p_mag, "Response")

        self.p_gd = pg.PlotWidget()
        self.p_gd.showGrid(x=True, y=True, alpha=0.3)
        self.p_gd.setLabel("bottom", "Frequency", units="Hz")
        self.p_gd.setLabel("left", "Group delay", units="s")
        self.c_gd = self.p_gd.plot(pen=pg.mkPen(theme.ACCENT, width=2))
        tabs.addTab(self.p_gd, "Group delay")

        self.p_step = pg.PlotWidget()
        self.p_step.showGrid(x=True, y=True, alpha=0.3)
        self.p_step.setLabel("bottom", "Time", units="s")
        self.p_step.setLabel("left", "Normalised step")
        self.c_step = self.p_step.plot(pen=pg.mkPen(theme.ACCENT, width=2))
        self.c_imp = self.p_step.plot(
            pen=pg.mkPen(theme.TEXT_DIM, style=QtCore.Qt.DotLine))
        tabs.addTab(self.p_step, "Step / impulse")

        tabs.setTabToolTip(0, "FIR, CIC droop and the cascade")
        tabs.setTabToolTip(
            1, "Flat group delay is the linear-phase guarantee; spikes sit at "
               "stopband nulls where phase is undefined")
        tabs.setTabToolTip(2, "Settling time of the filter you designed")
        return tabs

    # ------------------------------------------------------------- helpers
    def _on_mode_changed(self):
        latency = self.mode.currentIndex() == 1
        self.shape_row.setVisible(latency)
        if latency and HW_PROFILE["symmetric"]:
            self.status.setText(
                "⚠ Latency mode needs the FIR built non-symmetric "
                "(C_SYMMETRY=0); this bitstream folds its taps.")
            self.btn_load.setEnabled(False)
        else:
            self.status.setText("")
            self.btn_load.setEnabled(True)

    def _kwargs(self):
        return dict(
            cutoff_hz=self.cutoff.value(),
            mode="latency" if self.mode.currentIndex() == 1 else "quality",
            shape=self.shape.value(),
            atten_db=self.atten.value(),
            rate=self.rate.currentData(),
            taps=self.taps.currentData(),
            method=self.method.currentData(),
            cic_comp=self.cic_comp.isChecked(),
            frame=HW_PROFILE["frame"],
            width=HW_PROFILE["width"],
            rates=tuple(HW_PROFILE["rates_supported"]),
        )

    def _busy(self, on, msg=""):
        for w in (self.btn_design, self.btn_load, self.btn_coe, self.btn_cfg,
                  self.btn_open):
            w.setEnabled(not on)
        if msg:
            self.status.setText(msg)

    # -------------------------------------------------------------- design
    def design(self, then_load=False):
        if self._worker is not None and self._worker.isRunning():
            return
        self._then_load = then_load
        self._busy(True, "Designing…")
        self._worker = _DesignWorker(self._kwargs(), self)
        self._worker.done.connect(self._on_designed)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _design_and_load(self):
        self.design(then_load=True)

    def _on_failed(self, msg):
        self._busy(False)
        self.status.setText("✗ " + msg.replace("\n", " "))
        self.client.log.emit("err", f"filter design: {msg}")

    def _on_designed(self, f):
        self._busy(False)
        self.filter = f
        self._update_readout(f)
        self._update_plots(f)
        warn = self._loadability(f)
        self.status.setText(warn if warn else
                            f"✓ {f.metrics['f3_hz']:.4g} Hz, {len(f.ints)} taps, "
                            f"{f.metrics['group_delay_s']*1e6:.0f} us delay")
        if self._then_load:
            self._then_load = False
            self._load(f)

    def _loadability(self, f):
        """Why this design cannot be loaded as-is, or "" if it can."""
        if f.left_justified and HW_PROFILE["symmetric"]:
            return ("⚠ Left-justified design needs C_SYMMETRY=0; this bitstream "
                    "folds its taps.")
        if len(f.framed_ints()) > HW_PROFILE["ncoef"]:
            return (f"⚠ {len(f.framed_ints())} coefficients but the loader holds "
                    f"{HW_PROFILE['ncoef']}.")
        if f.rate != HW_PROFILE["rate_current"] and not HW_PROFILE["rate_settable"]:
            return (f"⚠ Designed for R={f.rate} but the bitstream runs "
                    f"R={HW_PROFILE['rate_current']} and there is no rate "
                    f"register — loading sends coefficients only.")
        return ""

    # ------------------------------------------------------------- readout
    def _update_readout(self, f):
        m, i = f.metrics, f.info
        rows = [
            ("Achieved -3 dB", f"{m['f3_hz']:.4g} Hz"),
            ("-60 dB", f"{m['f60_hz']:.4g} Hz"),
            ("Transition", f"{m['transition_hz']:.4g} Hz  ({m['shape']:.2f}:1)"),
            ("Stopband", f"{m['stopband_db']:.1f} dB"),
            ("Passband ripple", f"{m['ripple_db']:.5f} dB"),
            ("ENBW", f"{m['enbw_hz']:.4g} Hz"),
            ("CIC droop at f3", f"{m.get('cic_droop_db', float('nan')):.5f} dB"),
            ("", ""),
            ("CIC rate R", f"{f.rate}   ({f.fs/1e3:g} kHz out)"),
            ("CIC gain shift", f"{fd.cic_gain_shift(f.rate)} bits vs R=1000"),
            ("Method", f.method),
            ("Taps", f"{len(f.ints)} of {f.frame}"
                     + ("  left-justified" if f.left_justified else "")),
            ("Group delay", f"{m['group_delay_samples']:.0f} samples = "
                            f"{m['group_delay_s']*1e6:.1f} us"),
            ("Total delay", f"{m.get('total_delay_s', 0)*1e6:.1f} us  "
                            f"(incl. CIC)"),
            ("", ""),
            ("DC gain", f"{i['dc_sum']} = 2^{i['shift']}"),
            ("Datapath shift", f"{i['shift']} bits"),
            ("Peak tap", f"{i['peak']} of ±{(1 << (HW_PROFILE['width']-1))-1}"),
            ("Reload values", f"{len(f.reload_values(HW_PROFILE['ncoef']))}"
                              f"  (full frame)"),
        ]
        self.readout.clear()
        for k, v in rows:
            it = QtWidgets.QTreeWidgetItem([k, v])
            if not k:
                it.setDisabled(True)
            self.readout.addTopLevelItem(it)

    def _update_plots(self, f):
        fs = f.fs
        h = f.framed_ints().astype(float)
        h = h / h.sum()
        n = np.arange(len(h))

        hi = min(fs / 2, max(8 * f.metrics["f3_hz"], 2 * f.metrics.get(
            "f60_hz", f.metrics["f3_hz"]) or 0))
        freq = np.linspace(0.0, hi, 2000)
        H = np.exp(-2j * np.pi * np.outer(freq / fs, n)) @ h
        fir_db = 20 * np.log10(np.abs(H) + 1e-300)
        cic = fd.cic_droop_db(freq, fs)
        self.c_fir.setData(freq, fir_db)
        self.c_cic.setData(freq, cic)
        self.c_tot.setData(freq, fir_db + cic)
        self.p_mag.setYRange(-max(self.atten.value() + 40, 100), 5)
        self.l_f3.setValue(f.metrics["f3_hz"])

        # group delay: Re{ sum(n h e^-jwn) / sum(h e^-jwn) }
        E = np.exp(-2j * np.pi * np.outer(freq / fs, n))
        with np.errstate(divide="ignore", invalid="ignore"):
            gd = np.real((E @ (n * h)) / (E @ h)) / fs
        self.c_gd.setData(freq, gd)
        flat = f.metrics["group_delay_s"]
        self.p_gd.setYRange(flat * 0.9, flat * 1.1)

        active = len(f.ints)
        t = np.arange(active) / fs
        step = np.cumsum(h[:active]) / h[:active].sum()
        self.c_step.setData(t, step)
        self.c_imp.setData(t, h[:active] / np.abs(h[:active]).max())

    # ---------------------------------------------------------------- board
    def _load(self, f):
        if not self.client.is_connected():
            self.status.setText("✗ Not connected to the board.")
            return
        try:
            payload = f.reload_values(HW_PROFILE["ncoef"])
        except ValueError as e:
            self.status.setText("✗ " + str(e))
            self.client.log.emit("err", f"filter load: {e}")
            return
        self.loaded = f
        # The commit carries this filter's CIC rate (REG3[30:18]), so the board's
        # output rate becomes 200 MHz / f.rate. Track it so the record-rate cap
        # (app.current_output_hz) follows; optimistic — no readback exists.
        if f.rate:
            HW_PROFILE["rate_current"] = f.rate
        self.client.submit(
            f"fir load {f.metrics['f3_hz']:.4g} Hz, {len(payload)} coeffs",
            lambda c, p=payload, r=f.rate: c.fir_load(p, rate=r))
        self.status.setText(
            f"→ loading {len(payload)} coefficients "
            f"(shift {f.info['shift']} bits, delay "
            f"{f.metrics['group_delay_s']*1e6:.0f} us)")

    def _save_coe(self):
        if self.filter is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save coefficients", f"fir_{self.filter.metrics['f3_hz']:.0f}Hz"
            f"_R{self.filter.rate}.coe", "Coefficient files (*.coe)")
        if path:
            self.filter.write_coe(path)
            self.client.log.emit("ok", f"wrote {path}")

    def _save_config(self):
        if self.filter is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save loader config",
            f"fir_{self.filter.metrics['f3_hz']:.0f}Hz_R{self.filter.rate}.json",
            "JSON files (*.json)")
        if path:
            self.filter.write_config(path)
            self.client.log.emit("ok", f"wrote {path}")

    def _open_coe(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a FIR coefficient file", "",
            "Coefficient files (*.coe);;All files (*)")
        if not path:
            return
        try:
            taps, _w = fd.read_coe(path)
            payload = fd.loader_payload(taps, HW_PROFILE["ncoef"])
        except Exception as e:                      # noqa: BLE001
            self.client.log.emit("err", f"FIR .coe load failed: {e}")
            self.status.setText("✗ " + str(e))
            return
        if not self.client.is_connected():
            self.status.setText("✗ Not connected to the board.")
            return
        name = os.path.basename(path)
        self.client.submit(f"fir load {name} ({len(payload)} coeffs)",
                           lambda c, p=payload: c.fir_load(p))
        self.status.setText(f"→ loading {name}, {len(payload)} coefficients")
