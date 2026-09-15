"""scope_panel.py — live pyqtgraph scope with LabOne-style customization.

Ported from iza_plotter.py: a magnitude/value plot, a phase plot, and (when the
raw-ADC monitor is enabled) an ADC time series + live dBFS spectrum.  Adds:
  * value select — Magnitude / X (in-phase) / Y (quadrature)
  * per-channel show/hide, normalize, lin/log Y, adjustable time window + decimation
  * two draggable cursors with a delta readout
  * a math trace: chA {ratio, diff, dB} chB
"""

import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

import iza_packet as izp
from . import data_stream as ds
from . import theme
from .widgets import labeled_row

TARGET_PTS = 4000           # points per trace the auto-decimator aims for
                            # (a screen shows ~1-2k px wide; more just burns CPU)
SAFETY_PTS = 200000         # absolute per-trace cap (manual decimation only)
NFFT = 8192
ADC_FULLSCALE = 32768.0
FFT_PERIOD_S = 0.25         # recompute the spectrum at most this often


class _PlotPopout(QtWidgets.QWidget):
    """A standalone window that hosts one relocated PlotItem. The plot keeps
    updating live because redraw() writes to its curves regardless of which
    scene shows them. Closing the window returns the plot to the main stack."""
    closed = QtCore.Signal(str)

    def __init__(self, key, title):
        super().__init__()
        self._key = key
        self.setWindowTitle(title)
        self.resize(860, 480)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        self.glw = pg.GraphicsLayoutWidget()
        lay.addWidget(self.glw)

    def closeEvent(self, e):
        self.closed.emit(self._key)
        super().closeEvent(e)


class ScopePanel(QtWidgets.QWidget):
    # plot stack, in display order: (key, checkbox label)
    _PLOT_KEYS = [("mag", "Magnitude"), ("phase", "Phase"),
                  ("adc", "Raw ADC"), ("fft", "Spectrum")]

    # a scope show-channel checkbox was toggled by the user
    channel_show_changed = QtCore.Signal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chan_mask = None
        self.demod = []
        self.have_adc = False
        self.decim = 10
        self.window_s = 3.0
        self.t0_ts = None
        self._last_fs = 1.0 / 5e-6
        self.paused = False
        self._prog_range = False    # guard: programmatic X-range changes

        # rolling buffers (decimated by "plot every")
        self.t = np.empty(0)
        self.orf = np.empty(0, dtype=np.uint8)
        self.mag = {}       # ch -> scaled magnitude
        self.phr = {}       # ch -> phase (rad)
        self.adc = np.empty(0)

        # spectrum path: UNdecimated ADC samples at the full record rate,
        # so the FFT always spans the true bandwidth regardless of the
        # plot-every setting.  Recomputed at most every FFT_PERIOD_S.
        self.adc_full = np.empty(0)
        self._fs_full = 200e3
        self._last_fft_t = 0.0

        # curve handles
        self.c_val = {}
        self.c_ph = {}
        self.c_adc = None
        self.c_math = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)
        root.addWidget(self._build_controls())

        self.glw = pg.GraphicsLayoutWidget()
        root.addWidget(self.glw, 1)

        self.p_val = self.glw.addPlot(row=0, col=0, title="Magnitude")
        self.p_val.showGrid(x=True, y=True, alpha=0.3)
        self.p_val.setDownsampling(auto=True)
        self.p_val.setClipToView(True)
        self.p_val.addLegend()
        self.c_or = pg.ScatterPlotItem(size=8, pen=None,
                                       brush=pg.mkBrush(*theme.BAD_RGB(), 220))
        self.p_val.addItem(self.c_or)
        # trigger-event markers (Plan 07): down-triangles at the leading-peak
        # time, bright for a fire (classification passed), dim for a candidate.
        self._trig_ev = []          # list of (peak_ts_counter, passed_bool)
        self.c_trig = pg.ScatterPlotItem(size=13, symbol="t1", pen=None)
        # ignoreBounds: markers are pinned to the top of the view, so they must
        # NOT feed the y-autorange (else the axis stretches to a floating marker
        # and crushes the real trace to an unreadable sliver).
        self.p_val.addItem(self.c_trig, ignoreBounds=True)
        # trigger-threshold overlay: baseline and baseline±arm-threshold on the
        # amplitude channel, so the user can see which peaks would arm a trigger.
        self._trig_overlay = {"ch": 0, "thr": 0, "mindiff": 0, "show": False}
        self.thr_base = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen(theme.TEXT_DIM, style=QtCore.Qt.DotLine))
        self.thr_hi = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen(theme.WARN, style=QtCore.Qt.DashLine))
        self.thr_lo = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen(theme.WARN, style=QtCore.Qt.DashLine))
        for _l in (self.thr_base, self.thr_hi, self.thr_lo):
            _l.setVisible(False)
            self.p_val.addItem(_l, ignoreBounds=True)
        self.cur1 = pg.InfiniteLine(angle=90, movable=True,
                                    pen=pg.mkPen(theme.ACCENT, style=QtCore.Qt.DashLine))
        self.cur2 = pg.InfiniteLine(angle=90, movable=True,
                                    pen=pg.mkPen(theme.WARN, style=QtCore.Qt.DashLine))
        for c in (self.cur1, self.cur2):
            c.setVisible(False)
            c.sigPositionChanged.connect(self._update_cursor_readout)
            self.p_val.addItem(c)

        self.p_ph = self.glw.addPlot(row=1, col=0, title="Phase (deg)")
        self.p_ph.showGrid(x=True, y=True, alpha=0.3)
        self.p_ph.setDownsampling(auto=True)
        self.p_ph.setClipToView(True)
        self.p_ph.setXLink(self.p_val)

        self.p_adc = self.glw.addPlot(row=2, col=0,
                                      title="Raw input samples (ADC)")
        self.p_adc.showGrid(x=True, y=True, alpha=0.3)
        self.p_adc.setDownsampling(auto=True)
        self.p_adc.setClipToView(True)
        self.p_adc.setXLink(self.p_val)

        self.p_fft = self.glw.addPlot(row=3, col=0,
                                      title="Input spectrum (dBFS)")
        self.p_fft.showGrid(x=True, y=True, alpha=0.3)
        self.p_fft.setLabel("bottom", "frequency", units="Hz")
        self.p_fft.setLabel("left", "dBFS")
        self.p_fft.setYRange(-140, 5)
        self.c_fft = self.p_fft.plot(pen=pg.mkPen(theme.FFT_COLOR, width=1))

        # registry for show/hide + pop-out (keys match self._PLOT_KEYS)
        self._plotdefs = [("mag", self.p_val, "Magnitude"),
                          ("phase", self.p_ph, "Phase (deg)"),
                          ("adc", self.p_adc, "Raw input samples (ADC)"),
                          ("fft", self.p_fft, "Input spectrum")]
        self._popouts = {}
        self._relayout()            # apply the default visible set (mag + phase)

        # default mouse mode: wheel/drag zooms time only, Y stays automatic
        self._apply_mouse_mode()
        self.p_val.getViewBox().sigXRangeChanged.connect(self._on_xrange)

    def _build_controls(self):
        bar = QtWidgets.QWidget()
        rows = QtWidgets.QVBoxLayout(bar)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(2)
        lay = QtWidgets.QHBoxLayout()
        lay.setSpacing(10)
        lay2 = QtWidgets.QHBoxLayout()
        lay2.setSpacing(10)
        rows.addLayout(lay)
        rows.addLayout(lay2)

        # ---- row 1: run/pause, what to plot, time base, channels ----
        self.btn_pause = QtWidgets.QPushButton("⏸ Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setToolTip(
            "Freeze the plots (incoming data is discarded while paused; "
            "the board keeps running)")
        self.btn_pause.toggled.connect(self._on_pause)
        lay.addWidget(self.btn_pause)

        self.cmb_content = QtWidgets.QComboBox()
        self.cmb_content.addItems(["Magnitude", "X (in-phase)", "Y (quadrature)"])
        self.cmb_content.setToolTip(
            "What the top plot shows for each measurement channel:\n"
            "• Magnitude — signal strength |R|\n"
            "• X — the in-phase (real) component, |R|·cos(phase)\n"
            "• Y — the quadrature (imaginary) component, |R|·sin(phase)")
        self.cmb_content.currentIndexChanged.connect(self._retitle)
        lay.addWidget(QtWidgets.QLabel("Plot value:"))
        lay.addWidget(self.cmb_content)

        self.chk_norm = QtWidgets.QCheckBox("Normalize")
        self.chk_norm.setToolTip("Rescale each trace to fill 0…1 so traces "
                                 "with very different levels are comparable")
        lay.addWidget(self.chk_norm)
        self.chk_log = QtWidgets.QCheckBox("Log Y")
        self.chk_log.setToolTip("Logarithmic vertical axis on the top plot")
        self.chk_log.toggled.connect(
            lambda on: self.p_val.setLogMode(False, on))
        lay.addWidget(self.chk_log)

        self.chk_counts = QtWidgets.QCheckBox("Counts")
        self.chk_counts.setToolTip(
            "Show the magnitude in raw 32-bit demodulator counts (the same "
            "number the trigger threshold uses) instead of a fraction of full "
            "scale. Full scale = 2³⁰ = 1,073,741,824 counts.")
        self.chk_counts.toggled.connect(self._on_counts_toggle)
        lay.addWidget(self.chk_counts)

        self.spin_win = QtWidgets.QDoubleSpinBox()
        self.spin_win.setRange(0.1, 60.0)
        self.spin_win.setValue(3.0)
        self.spin_win.setSuffix(" s")
        self.spin_win.setToolTip(
            "How many seconds of history the plots hold and show. The "
            "buffers always cover this span; decimation adapts to keep the "
            "point count manageable.")
        self.spin_win.valueChanged.connect(self._on_window_changed)
        lay.addWidget(QtWidgets.QLabel("Time window:"))
        lay.addWidget(self.spin_win)

        self.chk_dec_auto = QtWidgets.QCheckBox("Auto")
        self.chk_dec_auto.setChecked(True)
        self.chk_dec_auto.setToolTip(
            "Automatically pick the decimation from the time window so each "
            "trace holds ~%d points. Uncheck to set it manually." % TARGET_PTS)
        self.chk_dec_auto.toggled.connect(self._on_dec_auto)
        self.spin_dec = QtWidgets.QSpinBox()
        self.spin_dec.setRange(1, 1000)
        self.spin_dec.setValue(10)
        self.spin_dec.setEnabled(False)     # auto by default
        self.spin_dec.setToolTip(
            "Plot every Nth record (1 = plot everything). With manual "
            "decimation, very low values on long windows are capped at "
            "%d points per trace — the held span shrinks." % SAFETY_PTS)
        self.spin_dec.valueChanged.connect(self._on_dec_changed)
        lay.addWidget(QtWidgets.QLabel("Plot every:"))
        lay.addWidget(self.spin_dec)
        lay.addWidget(self.chk_dec_auto)

        lay.addWidget(QtWidgets.QLabel("Show channels:"))
        self.ch_show = []
        for ch in range(4):
            chk = QtWidgets.QCheckBox(str(ch))
            chk.setChecked(True)
            chk.setToolTip(
                f"Show measurement channel {ch} — also enables/disables "
                f"receiving this channel from the board (saves bandwidth "
                f"when unchecked)")
            chk.toggled.connect(self._apply_visibility)
            chk.toggled.connect(
                lambda on, ch=ch: self.channel_show_changed.emit(ch, on))
            self.ch_show.append(chk)
            lay.addWidget(chk)
        lay.addStretch(1)

        # ---- row 2: zoom behaviour, cursors, math ----
        lay2.addWidget(QtWidgets.QLabel("Mouse zoom:"))
        self.chk_zoom_x = QtWidgets.QCheckBox("X (time)")
        self.chk_zoom_x.setChecked(True)
        self.chk_zoom_x.setToolTip(
            "Let the mouse wheel / drag zoom the time axis. Zooming the "
            "time axis also updates the time-window setting.")
        self.chk_zoom_y = QtWidgets.QCheckBox("Y (value)")
        self.chk_zoom_y.setChecked(False)
        self.chk_zoom_y.setToolTip(
            "Let the mouse wheel / drag zoom the value axis. Leave off to "
            "keep the value axis on automatic scaling. Tip: the wheel over "
            "an axis' numbers always zooms just that axis.")
        self.chk_zoom_x.toggled.connect(self._apply_mouse_mode)
        self.chk_zoom_y.toggled.connect(self._apply_mouse_mode)
        lay2.addWidget(self.chk_zoom_x)
        lay2.addWidget(self.chk_zoom_y)

        btn_fit = QtWidgets.QPushButton("Fit Y")
        btn_fit.setToolTip("Re-enable automatic vertical scaling on all "
                           "plots (after a manual Y zoom)")
        btn_fit.clicked.connect(self._fit_y)
        lay2.addWidget(btn_fit)

        btn_flush = QtWidgets.QPushButton("Clear data")
        btn_flush.setToolTip(
            "Discard all buffered trace history (useful after a channel or "
            "carrier change leaves stale/garbage points in the window)")
        btn_flush.clicked.connect(self._clear_data)
        lay2.addWidget(btn_flush)

        self.chk_follow = QtWidgets.QCheckBox("Follow")
        self.chk_follow.setChecked(True)
        self.chk_follow.setToolTip(
            "Keep the view scrolled to the newest data. Dragging back in "
            "time releases it; re-check to snap back to live.")
        lay2.addWidget(self.chk_follow)

        self.chk_cursors = QtWidgets.QCheckBox("Cursors")
        self.chk_cursors.setToolTip(
            "Show two draggable time cursors on the top plot with a "
            "time-difference readout")
        self.chk_cursors.toggled.connect(self._toggle_cursors)
        lay2.addWidget(self.chk_cursors)

        # math
        math_lbl = QtWidgets.QLabel("Math trace:")
        math_lbl.setToolTip(
            "Add an extra trace computed from two channels' magnitudes:\n"
            "• ratio — A ÷ B\n• diff — A − B\n• dB — 20·log10(A ÷ B)")
        lay2.addWidget(math_lbl)
        self.math_a = QtWidgets.QComboBox()
        self.math_a.setToolTip("Channel A of the math trace")
        self.math_op = QtWidgets.QComboBox()
        self.math_op.addItems(["ratio", "diff", "dB"])
        self.math_op.setToolTip(math_lbl.toolTip())
        self.math_b = QtWidgets.QComboBox()
        self.math_b.setToolTip("Channel B of the math trace")
        for cb in (self.math_a, self.math_b):
            cb.addItems(["0", "1", "2", "3"])
        btn_add = QtWidgets.QPushButton("Add")
        btn_add.setToolTip("Add/update the math trace on the top plot")
        btn_add.clicked.connect(self._set_math)
        btn_clr = QtWidgets.QPushButton("Clear")
        btn_clr.setToolTip("Remove the math trace")
        btn_clr.clicked.connect(self._clear_math)
        for w in (self.math_a, self.math_op, self.math_b, btn_add, btn_clr):
            lay2.addWidget(w)

        self.cursor_lbl = QtWidgets.QLabel("")
        self.cursor_lbl.setProperty("dim", True)
        lay2.addStretch(1)
        lay2.addWidget(self.cursor_lbl)

        # ---- row 3: which plots to show + pop-out ----
        lay3 = QtWidgets.QHBoxLayout()
        lay3.setSpacing(10)
        rows.addLayout(lay3)
        lbl = QtWidgets.QLabel("Show plots:")
        lbl.setToolTip("Only show the plots you're using — the ADC and "
                       "spectrum plots appear automatically when the raw-input "
                       "monitor is on.")
        lay3.addWidget(lbl)
        self.plot_chk = {}
        for key, label in self._PLOT_KEYS:
            chk = QtWidgets.QCheckBox(label)
            chk.setChecked(key in ("mag", "phase"))
            if key in ("adc", "fft"):
                chk.setEnabled(False)       # enabled once raw ADC is streaming
            chk.toggled.connect(self._relayout)
            self.plot_chk[key] = chk
            lay3.addWidget(chk)

        lay3.addSpacing(16)
        lay3.addWidget(QtWidgets.QLabel("Expand:"))
        self.cmb_expand = QtWidgets.QComboBox()
        self.cmb_expand.addItems([label for _, label in self._PLOT_KEYS])
        self.cmb_expand.setToolTip("Choose a plot to open in its own window")
        lay3.addWidget(self.cmb_expand)
        btn_pop = QtWidgets.QPushButton("Pop out ⧉")
        btn_pop.setToolTip(
            "Open the selected plot in its own resizable window (it keeps "
            "updating live). Close that window to dock it back here.")
        btn_pop.clicked.connect(self._popout_selected)
        lay3.addWidget(btn_pop)
        lay3.addStretch(1)

        self.math_cfg = None
        self._auto_decim()      # initial decimation from the default window
        return bar

    # --------------------------------------------------- time base / decim
    def _on_window_changed(self, v):
        self.window_s = v
        self._auto_decim()

    def _on_dec_changed(self, v):
        if not self.chk_dec_auto.isChecked():
            self.decim = v

    def _on_dec_auto(self, on):
        self.spin_dec.setEnabled(not on)
        if on:
            self._auto_decim()
        else:
            self.decim = self.spin_dec.value()

    def _auto_decim(self):
        """Pick 'plot every Nth' so one time window holds ~TARGET_PTS points
        at the measured record rate."""
        if not self.chk_dec_auto.isChecked():
            return
        d = max(1, int(np.ceil(self.window_s * self._fs_full / TARGET_PTS)))
        d = min(d, 1000)
        if d != self.decim:
            self.decim = d
            self.spin_dec.blockSignals(True)
            self.spin_dec.setValue(d)
            self.spin_dec.blockSignals(False)

    # ------------------------------------------------------- run/pause/zoom
    def _on_pause(self, on):
        self.paused = on
        self.btn_pause.setText("▶ Resume" if on else "⏸ Pause")

    def _apply_mouse_mode(self):
        zx = self.chk_zoom_x.isChecked()
        zy = self.chk_zoom_y.isChecked()
        for p in (self.p_val, self.p_ph, self.p_adc):
            p.getViewBox().setMouseEnabled(x=zx, y=zy)
        self.p_fft.getViewBox().setMouseEnabled(x=zx, y=zy)

    def _fit_y(self):
        for p in (self.p_val, self.p_ph, self.p_adc, self.p_fft):
            p.enableAutoRange(axis="y")

    def _clear_data(self):
        """Flush all rolling buffers (keeps the layout/channel setup)."""
        self.t = np.empty(0)
        self.orf = np.empty(0, dtype=np.uint8)
        self.adc = np.empty(0)
        self.adc_full = np.empty(0)
        for ch in self.demod:
            self.mag[ch] = np.empty(0)
            self.phr[ch] = np.empty(0)
        self.t0_ts = None
        for ch, c in self.c_val.items():
            c.setData([], [])
        for c in self.c_ph.values():
            c.setData([], [])
        if self.c_adc is not None:
            self.c_adc.setData([], [])
        self.c_fft.setData([], [])
        self.c_or.setData([], [])
        self._trig_ev = []
        self.c_trig.setData([], [])
        if self.c_math is not None:
            self.c_math.setData([], [])
        self._fit_y()

    def _on_xrange(self, _vb, rng):
        """User changed the time axis: a zoom updates the time window (and we
        keep following); a pan back in history releases Follow."""
        if self._prog_range:
            return
        span = float(rng[1] - rng[0])
        if span <= 0:
            return
        if abs(span - self.window_s) / self.window_s > 0.01:
            # zoom: adopt the new span as the time window
            self.window_s = max(0.1, min(60.0, span))
            self.spin_win.blockSignals(True)
            self.spin_win.setValue(self.window_s)
            self.spin_win.blockSignals(False)
            self._auto_decim()
        elif self.t.size and rng[1] < self.t[-1] - 0.05 * span:
            # pan away from the live edge: stop following
            self.chk_follow.setChecked(False)

    def set_show(self, ch, on):
        """Reflect the board's channel state without emitting a command."""
        if self.ch_show[ch].isChecked() == on:
            return
        self.ch_show[ch].blockSignals(True)
        self.ch_show[ch].setChecked(on)
        self.ch_show[ch].blockSignals(False)
        self._apply_visibility()

    # --------------------------------------------------------------- layout
    def _content_name(self):
        return ["Magnitude", "X", "Y"][self.cmb_content.currentIndex()]

    def _retitle(self):
        self.p_val.setTitle(self._content_name()
                            + (" (normalized)" if self.chk_norm.isChecked() else ""))

    # ------------------------------------------------------ plot show/pop-out
    def _relayout(self, *_):
        """Re-pack the plot stack with only the checked, non-popped plots."""
        if not hasattr(self, "_plotdefs"):
            return
        self.glw.clear()
        r = 0
        for key, plot, _title in self._plotdefs:
            if key in self._popouts or not self.plot_chk[key].isChecked():
                continue
            self.glw.addItem(plot, row=r, col=0)
            r += 1

    def _plot_by_key(self, key):
        for k, plot, title in self._plotdefs:
            if k == key:
                return plot, title
        return None, None

    def _popout_selected(self, *_):
        key = self._PLOT_KEYS[self.cmb_expand.currentIndex()][0]
        if key in self._popouts:
            self._popouts[key].raise_()
            self._popouts[key].activateWindow()
            return
        plot, title = self._plot_by_key(key)
        if plot is None:
            return
        win = _PlotPopout(key, f"iza — {title}")
        win.closed.connect(self._reclaim_popout)
        self._popouts[key] = win
        self._relayout()                 # remove it from the docked stack
        win.glw.addItem(plot, row=0, col=0)
        win.show()

    def _reclaim_popout(self, key):
        win = self._popouts.pop(key, None)
        if win is None:
            return
        plot, _title = self._plot_by_key(key)
        try:
            win.glw.removeItem(plot)
        except Exception:
            pass
        self._relayout()                 # dock it back into the stack

    def _reset_layout(self, chan_mask):
        # drop old curves
        for d in (self.c_val, self.c_ph):
            for c in d.values():
                self.p_val.removeItem(c) if d is self.c_val else self.p_ph.removeItem(c)
        self.c_val, self.c_ph = {}, {}
        if self.c_adc is not None:
            self.p_adc.removeItem(self.c_adc)
            self.c_adc = None
        self._clear_math()

        self.chan_mask = chan_mask
        self.demod = izp.demod_list(chan_mask)
        self.have_adc = izp.adc_enabled(chan_mask)
        self.t = np.empty(0)
        self.orf = np.empty(0, dtype=np.uint8)
        self.adc = np.empty(0)
        self.adc_full = np.empty(0)
        self.mag, self.phr = {}, {}
        self.t0_ts = None

        for ch in self.demod:
            col = theme.channel_color(ch)
            self.c_val[ch] = self.p_val.plot(pen=pg.mkPen(col, width=1), name=f"ch{ch}")
            self.c_ph[ch] = self.p_ph.plot(pen=pg.mkPen(col, width=1))
            self.mag[ch] = np.empty(0)
            self.phr[ch] = np.empty(0)
        if self.have_adc:
            self.c_adc = self.p_adc.plot(pen=pg.mkPen(theme.ADC_COLOR, width=1))
            self.p_adc.setTitle("Raw input samples (ADC)")
            self.p_fft.setTitle("Input spectrum (dBFS)")
        else:
            self.p_adc.setTitle("Raw input samples — enable “stream raw input "
                                "samples” in Signal Input to see this")
            self.p_fft.setTitle("Input spectrum — enable “stream raw input "
                                "samples” in Signal Input to see this")

        # the ADC + spectrum plots only make sense when raw input is streaming:
        # enable/auto-show them with the ADC monitor, hide them otherwise.
        for key in ("adc", "fft"):
            chk = self.plot_chk[key]
            chk.blockSignals(True)
            chk.setEnabled(self.have_adc)
            chk.setChecked(self.have_adc)
            chk.blockSignals(False)
        self._relayout()
        self._apply_visibility()
        self._retitle()

    def _apply_visibility(self):
        for ch in self.demod:
            vis = self.ch_show[ch].isChecked()
            if ch in self.c_val:
                self.c_val[ch].setVisible(vis)
                self.c_ph[ch].setVisible(vis)

    # ---------------------------------------------------------------- ingest
    def on_batch(self, b):
        if self.paused:
            return
        if b["chan_mask"] != self.chan_mask:
            self._reset_layout(b["chan_mask"])

        # measure the true record rate from timestamps (drives the FFT axis
        # and the auto-decimator)
        ts_all = b["ts"]
        if ts_all.size >= 2:
            d_ts = float(np.median(np.diff(ts_all[:min(64, ts_all.size)])))
            if d_ts > 0:
                fs = izp.PL_CLK_HZ / d_ts
                if abs(fs - self._fs_full) / self._fs_full > 0.01:
                    self._fs_full = fs
                    self._auto_decim()

        # spectrum path: undecimated samples at the true record rate
        if self.have_adc and b["adc"] is not None and b["adc"].size:
            self.adc_full = np.concatenate(
                [self.adc_full, b["adc"].astype(np.float64)])[-NFFT:]

        d = max(1, self.decim)
        sl = slice(None, None, d)
        ts = b["ts"][sl]
        if ts.size == 0:
            return
        if self.t0_ts is None:
            self.t0_ts = int(ts[0])
        t = (ts.astype(np.float64) - float(self.t0_ts)) / ds.izp.PL_CLK_HZ
        self.t = np.concatenate([self.t, t])
        self.orf = np.concatenate([self.orf, b["orf"][sl]])
        for ch in self.demod:
            self.mag[ch] = np.concatenate(
                [self.mag[ch], ds.scale_mag(b["sig"][ch][sl])])
            self.phr[ch] = np.concatenate(
                [self.phr[ch], ds.scale_phase_rad(b["phase"][ch][sl])])
        if self.have_adc and b["adc"] is not None:
            self.adc = np.concatenate([self.adc, b["adc"][sl].astype(np.float64)])

    def on_trigger(self, evt):
        """Record a trigger event so redraw() can mark it on the timeline."""
        import iza_ctrl
        passed = bool(evt.get("flags", 0) & iza_ctrl.EVF_PASS)
        self._trig_ev.append((int(evt.get("peak_ts", 0)), passed))
        if len(self._trig_ev) > 1000:
            self._trig_ev = self._trig_ev[-1000:]

    def _draw_triggers(self, t_now):
        if not self._trig_ev or self.t0_ts is None:
            self.c_trig.setData([], [])
            return
        fs = izp.PL_CLK_HZ
        t0 = float(self.t0_ts)
        t_min = t_now - self.window_s
        vr = self.p_val.getViewBox().viewRange()[1]
        y_top = vr[1] - 0.03 * (vr[1] - vr[0])
        # prune events older than the retained window
        self._trig_ev = [(ts, p) for (ts, p) in self._trig_ev
                         if (ts - t0) / fs >= t_min - 1.0]
        spots = []
        for ts, passed in self._trig_ev:
            te = (ts - t0) / fs
            if te < t_min or te > t_now + 1e-6:
                continue
            color = theme.ACCENT if passed else theme.TEXT_DIM
            spots.append({"pos": (te, y_top), "brush": pg.mkBrush(color),
                          "pen": None})
        self.c_trig.setData(spots)

    def _on_counts_toggle(self, _on):
        unit = ("counts (int32)" if self.chk_counts.isChecked()
                else "fraction of full scale")
        self.p_val.getAxis("left").setLabel(unit)
        self._fit_y()

    def set_trigger_overlay(self, ch, thr_counts, mindiff_counts, show):
        """Called by the TriggerPanel: draw baseline±threshold guide lines on
        the amplitude channel so the user can see what would trigger."""
        self._trig_overlay = {"ch": int(ch), "thr": int(thr_counts),
                              "mindiff": int(mindiff_counts), "show": bool(show)}

    def _draw_overlay(self):
        ov = self._trig_overlay
        ch = ov["ch"]
        # a raw-value guide only makes sense on the linear magnitude view
        show = (ov["show"] and self._content_name() == "Magnitude"
                and not self.chk_norm.isChecked() and not self.chk_log.isChecked()
                and ch in self.mag and self.mag[ch].size
                and ch < len(self.ch_show) and self.ch_show[ch].isChecked())
        for l in (self.thr_base, self.thr_hi, self.thr_lo):
            l.setVisible(show)
        if not show:
            return
        f = self._mag_factor()
        base = float(np.mean(self.mag[ch])) * f            # window-mean baseline
        thr = ov["thr"] / ds.MAG_SCALE * f
        self.thr_base.setPos(base)
        self.thr_hi.setPos(base + thr)
        self.thr_lo.setPos(base - thr)

    def redraw(self):
        if self.t.size == 0:
            self.c_trig.setData([], [])
            return
        # retention follows the time window: keep exactly one window's worth
        # of history (auto-decimation keeps the point count near TARGET_PTS);
        # SAFETY_PTS only bites with manual decimation set aggressively low
        t_now = self.t[-1]
        keep = self.t >= (t_now - self.window_s)
        self._apply_keep(keep)
        if self.t.size > SAFETY_PTS:
            self._apply_keep(slice(-SAFETY_PTS, None))

        # Buffers are now trimmed; if this tab isn't showing, skip all the
        # pyqtgraph setData/render work (the expensive part) until it is.
        if not self.isVisible():
            return

        content = self._content_name()
        for ch in self.demod:
            y = self._value(ch, content)
            if self.chk_norm.isChecked():
                y = _normalize(y)
            self.c_val[ch].setData(self.t, y)
            self.c_ph[ch].setData(self.t, np.degrees(self.phr[ch]))

        over = self.orf != 0
        if self.demod and over.any():
            y0 = self._value(self.demod[0], content)
            if self.chk_norm.isChecked():
                y0 = _normalize(y0)
            self.c_or.setData(self.t[over], y0[over])
        else:
            self.c_or.setData([], [])

        self._draw_math(content)
        self._draw_adc()
        self._draw_triggers(t_now)
        self._draw_overlay()
        self._update_cursor_readout()

        # follow mode: keep the linked time axes glued to the newest data
        if self.chk_follow.isChecked() and not self.paused:
            self._prog_range = True
            try:
                self.p_val.setXRange(t_now - self.window_s, t_now, padding=0)
            finally:
                self._prog_range = False

    def _apply_keep(self, keep):
        self.t = self.t[keep]
        self.orf = self.orf[keep]
        for ch in self.demod:
            self.mag[ch] = self.mag[ch][keep]
            self.phr[ch] = self.phr[ch][keep]
        if self.have_adc:
            self.adc = self.adc[keep]

    def _mag_factor(self):
        """Display scale for magnitude/X/Y: 1 for fraction-of-FS, 2^30 for raw
        32-bit counts (matches the trigger threshold's units)."""
        return ds.MAG_SCALE if self.chk_counts.isChecked() else 1.0

    def _value(self, ch, content):
        f = self._mag_factor()
        if content == "Magnitude":
            return self.mag[ch] * f
        if content == "X":
            return self.mag[ch] * np.cos(self.phr[ch]) * f
        return self.mag[ch] * np.sin(self.phr[ch]) * f

    # ----------------------------------------------------------------- math
    def _set_math(self):
        a = int(self.math_a.currentText())
        b = int(self.math_b.currentText())
        op = self.math_op.currentText()
        self.math_cfg = (a, op, b)
        if self.c_math is None:
            self.c_math = self.p_val.plot(pen=pg.mkPen(theme.MATH_COLOR, width=1,
                                                       style=QtCore.Qt.DotLine),
                                          name="math")

    def _clear_math(self):
        self.math_cfg = None
        if self.c_math is not None:
            self.p_val.removeItem(self.c_math)
            self.c_math = None

    def _draw_math(self, content):
        if self.math_cfg is None or self.c_math is None:
            return
        a, op, b = self.math_cfg
        if a not in self.mag or b not in self.mag:
            self.c_math.setData([], [])
            return
        ma, mb = self.mag[a], self.mag[b]
        with np.errstate(divide="ignore", invalid="ignore"):
            if op == "ratio":
                y = np.where(mb != 0, ma / mb, 0.0)
            elif op == "diff":
                y = ma - mb
            else:  # dB
                y = 20.0 * np.log10(np.abs(np.where(mb != 0, ma / mb, 1e-12)))
        # a near-zero denominator makes ratio/dB explode and drags the plot's
        # autorange to +-thousands, crushing the real traces to a flat line
        y = np.clip(np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0),
                    -1e3, 1e3)
        self.c_math.setData(self.t, y)

    # -------------------------------------------------------------- ADC/FFT
    def _draw_adc(self):
        if not self.have_adc:
            return
        if self.adc.size:
            self.c_adc.setData(self.t, self.adc)   # time plot: decimated
        # spectrum: undecimated buffer at the true record rate (~200 kHz),
        # throttled — a full-resolution FFT a few times a second is plenty
        now = time.monotonic()
        if self.adc_full.size < 256 or now - self._last_fft_t < FFT_PERIOD_S:
            return
        self._last_fft_t = now
        n = int(self.adc_full.size)
        seg = self.adc_full - self.adc_full.mean()
        fs = self._fs_full
        w = np.hanning(n)
        amp = 2.0 * np.abs(np.fft.rfft(seg * w)) / np.sum(w)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        dbfs = 20.0 * np.log10(np.maximum(amp, 1e-6) / ADC_FULLSCALE)
        self.c_fft.setData(freqs, dbfs)
        pk = int(np.argmax(amp))
        self.p_fft.setTitle("Input spectrum — peak %.1f kHz @ %.1f dBFS "
                            "(fs %.1f kHz, %d-pt FFT)"
                            % (freqs[pk]/1e3, dbfs[pk], fs/1e3, n))

    # -------------------------------------------------------------- cursors
    def _toggle_cursors(self, on):
        if on and self.t.size:
            span = self.t[-1] - self.t[0]
            self.cur1.setPos(self.t[0] + span * 0.33)
            self.cur2.setPos(self.t[0] + span * 0.66)
        self.cur1.setVisible(on)
        self.cur2.setVisible(on)
        self._update_cursor_readout()

    def _update_cursor_readout(self):
        if not self.chk_cursors.isChecked():
            self.cursor_lbl.setText("")
            return
        x1, x2 = self.cur1.value(), self.cur2.value()
        self.cursor_lbl.setText(
            f"c1={x1*1e3:.2f} ms  c2={x2*1e3:.2f} ms  Δ={abs(x2-x1)*1e3:.2f} ms"
            + (f"  (1/Δ={1.0/abs(x2-x1):.1f} Hz)" if x2 != x1 else ""))


def _normalize(a):
    if a.size == 0:
        return a
    span = np.ptp(a)
    return (a - a.min()) / (span if span else 1.0)
