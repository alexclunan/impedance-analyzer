"""trigger_panel.py — Plan 07 triggering tab.

A LabOne-style control column (amplitude detection, phase-window classification,
channel combine, fire timing) on the left, and a live event log + run statistics
on the right.  Settings are converted to wire units and pushed to the board via
ControlClient; trigger events stream back asynchronously (client.trigger_event)
and populate the log/stats and the scope markers.

The detection algorithm itself runs on the board (iza_replay.c), ported from the
HF2IS cell-sorter: rolling-baseline bipolar-peak amplitude detection + per-channel
phase-window classification, with fixed or flow-velocity-derived fire delay.
"""

import csv
import json
import math
import time

from pyqtgraph.Qt import QtCore, QtWidgets

import fir_design as fd
import iza_ctrl
from . import theme
from .filter_panel import current_output_hz   # live CIC output rate (200 MHz / R)
from .widgets import CollapsibleSection, labeled_row

# PS detection -> fire-register write; small and fairly constant (a non-RT kernel
# can add scheduling spikes on top — see LAT_ISSUES).
LAT_PS_S = 60e-6

LAT_ISSUES = (
    "Estimated WORST-CASE decision latency: from the ADC sample of the last "
    "critical part of an event to the PS writing the fire timestamp into the PL "
    "trigger engine. It does NOT include the intentional actuation delay (that is "
    "deterministic and separate).\n\n"
    "Assumptions & potential issues:\n"
    "• FIR group delay usually dominates. A quality-mode filter can be "
    "milliseconds; use a latency-mode design and keep the Filter tab's 'Total "
    "delay' small.\n"
    "• Grows with R: every per-record term scales with 200 MHz / R, so a higher R "
    "(lower record rate) inflates both the FIR and DMA terms. Use R=1000 for "
    "triggering.\n"
    "• The DMA term is worst-case (critical sample at the start of a buffer). "
    "Records/packet too small risks 2-buffer-ring overruns under Linux scheduling "
    "jitter (~100–200 µs); too large adds latency. RING_DEPTH is fixed at 2.\n"
    "• The PS term is an estimate; a non-PREEMPT_RT kernel can add scheduling "
    "spikes.\n"
    "• The FIR group delay is only known if a filter was designed + loaded this "
    "session; otherwise the running filter's delay is unknown and excluded.\n"
    "• The total must stay below your intended actuation delay for the fire to "
    "land on time; target < 5 ms."
)

TICK_HZ = iza_ctrl.PL_TICK_HZ
MAG_SCALE = float(iza_ctrl.TRIG_MAG_SCALE)
PH_SCALE = float(iza_ctrl.TRIG_PH_SCALE)

_COLS = ["#", "time (s)", "class", "chans", "peak", "trough",
         "Δt (ms)", "delay (ms)", "latency (ms)", "fire @ (s)"]

_COL_TIPS = [
    "Event index (sequence number).",
    "Absolute board time of the leading peak (PL timestamp ÷ 200 MHz).",
    "FIRE = passed phase classification (drives the output); "
    "cand = amplitude candidate that failed classification.",
    "Which demod channels were inside their phase window at detection "
    "(the matched set). “—” = none matched, or no phase classification.",
    "Baseline-subtracted magnitude of the leading peak (fraction of full scale).",
    "Baseline-subtracted magnitude of the trailing peak.",
    "Time between the two peaks — the transit across the detection window.",
    "Computed actuation delay added to the peak (fixed, or velocity-derived).",
    "Leading-peak → detection-decision, in the signal's own timeline. How long "
    "after the peak the detector had enough waveform to declare a trigger "
    "(≈ the bipolar-event duration). NOT the peak-to-output time.",
    "Absolute board time the output fires = peak time + delay "
    "(this is the real peak-to-trigger-output time).",
]


class TriggerPanel(QtWidgets.QWidget):
    # {ch, thr, mindiff, show} for the scope threshold overlay
    overlay_changed = QtCore.Signal(object)

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._filters = None     # FilterPanel, set via set_filter_source (FIR delay)

        # run statistics
        self._fires = 0
        self._cands = 0
        self._run_t0 = None
        self._lat_ms = []
        self._delay_ms = []
        self._rows = []          # kept for CSV export

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(split, 1)

        # ---- left: controls (scrollable) ----
        col = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(col)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(8)
        cl.addWidget(self._build_mode())
        cl.addWidget(self._build_amplitude())
        cl.addWidget(self._build_phase())
        cl.addWidget(self._build_timing())
        cl.addWidget(self._build_latency())
        cl.addStretch(1)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(col)
        scroll.setMinimumWidth(360)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        split.addWidget(scroll)

        # ---- right: event log + stats ----
        split.addWidget(self._build_log())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([380, 640])

        client.trigger_event.connect(self.on_event)
        self._update_ratio()
        self._update_thr_hints()
        self._emit_overlay()

    # =====================================================================
    # helpers
    # =====================================================================
    def _dspin(self, lo, hi, step, val, suffix="", dec=3):
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setDecimals(dec)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        s.valueChanged.connect(self._apply_if_armed)
        return s

    def _ispin(self, lo, hi, val, suffix=""):
        s = QtWidgets.QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        s.valueChanged.connect(self._apply_if_armed)
        return s

    def _cspin(self, val):
        """A raw-counts spinbox (0 … 2^31-1)."""
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(0, 2**31 - 1)
        s.setDecimals(0)
        s.setSingleStep(100000)
        s.setSuffix(" cnt")
        s.setGroupSeparatorShown(True)
        s.setValue(val)
        s.valueChanged.connect(self._apply_if_armed)
        return s

    def _on_thr_changed(self, *_):
        self._update_thr_hints()
        self._emit_overlay()

    def _update_thr_hints(self):
        self.lbl_thr.setText(f"≈ {self.spin_thr.value() / MAG_SCALE * 100:.2f} %FS")
        self.lbl_mindiff.setText(
            f"≈ {self.spin_mindiff.value() / MAG_SCALE * 100:.2f} %FS")

    def _emit_overlay(self, *_):
        self.overlay_changed.emit({
            "ch": self.cmb_ampch.currentIndex(),
            "thr": int(self.spin_thr.value()),
            "mindiff": int(self.spin_mindiff.value()),
            "show": self.chk_overlay.isChecked(),
        })

    # =====================================================================
    # control sections
    # =====================================================================
    def _build_mode(self):
        sec = CollapsibleSection("Trigger — mode & arming")

        self.chk_arm = QtWidgets.QPushButton("● Arm trigger")
        self.chk_arm.setCheckable(True)
        self.chk_arm.setProperty("accent", True)
        self.chk_arm.setToolTip(
            "Arm the detector. While armed, every setting change is pushed to "
            "the board live. Disarm to stop firing.")
        self.chk_arm.toggled.connect(self._on_arm)
        btn_apply = QtWidgets.QPushButton("Apply settings")
        btn_apply.setToolTip("Push the current settings to the board without "
                             "changing the armed state.")
        btn_apply.clicked.connect(self._apply)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.chk_arm)
        row.addWidget(btn_apply)
        row.addStretch(1)
        rw = QtWidgets.QWidget(); rw.setLayout(row)
        sec.add(rw)

        self.chk_hw = QtWidgets.QCheckBox(
            "Drive hardware output pin (requires Stage-2 bitstream)")
        self.chk_hw.setToolTip(
            "Off = soft mode: the board detects and reports events but drives "
            "no pin (Stage 1). On = load the PL fire engine to drive the "
            "physical actuation pin (Stage 2).")
        self.chk_hw.toggled.connect(self._apply_if_armed)
        sec.add(self.chk_hw)

        self.cmb_ampch = QtWidgets.QComboBox()
        self.cmb_ampch.addItems([f"Channel {i}" for i in range(4)])
        self.cmb_ampch.setToolTip("Demodulator channel whose magnitude drives "
                                  "amplitude (size) detection.")
        self.cmb_ampch.activated.connect(self._apply_if_armed)
        self.cmb_ampch.activated.connect(self._emit_overlay)
        sec.add(labeled_row("Amplitude channel", self.cmb_ampch))

        self.cmb_pol = QtWidgets.QComboBox()
        self.cmb_pol.addItems(["Peak then trough (normal)",
                               "Trough then peak (flipped)"])
        self.cmb_pol.setToolTip("Order of the bipolar excursion a passing "
                                "bead/cell produces.")
        self.cmb_pol.activated.connect(self._apply_if_armed)
        sec.add(labeled_row("Polarity", self.cmb_pol))

        self.chk_emit = QtWidgets.QCheckBox(
            "Log candidates that fail classification")
        self.chk_emit.setChecked(True)
        self.chk_emit.setToolTip(
            "Stream an event for every amplitude detection, even when the "
            "phase-window classification does not pass (useful for tuning).")
        self.chk_emit.toggled.connect(self._apply_if_armed)
        sec.add(self.chk_emit)

        self.spin_wdog = self._dspin(0.0, 60.0, 0.5, 3.0, " s", 1)
        self.spin_wdog.setToolTip(
            "Safety watchdog: the board auto-disarms if the PC stops responding "
            "for this long (app crash, cable pull, control-link loss), so the "
            "actuators can't keep firing unattended. 0 = never.")
        sec.add(labeled_row("Safety timeout", self.spin_wdog))

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Test fire:"))
        for label, mask in [("Out 0", 0b01), ("Out 1", 0b10), ("Both", 0b11)]:
            b = QtWidgets.QPushButton(label)
            b.setToolTip("Manually pulse the actuation output(s) ~5 ms from now "
                         "to check wiring/timing. Works even while disarmed; "
                         "needs the Stage-2 bitstream.")
            b.clicked.connect(lambda _=False, m=mask: self._test_fire(m))
            row.addWidget(b)
        row.addStretch(1)
        rw = QtWidgets.QWidget(); rw.setLayout(row)
        sec.add(rw)
        return sec

    def _build_amplitude(self):
        sec = CollapsibleSection("Amplitude detection")

        self.spin_thr = self._cspin(21000000)
        self.spin_thr.setToolTip(
            "Excursion from the rolling baseline that arms an event, in raw "
            "demodulator magnitude counts (32-bit). Full scale = 2³⁰. Read the "
            "value off the Scope tag (enable its “Counts” view — the dashed "
            "lines show this level).")
        self.lbl_thr = QtWidgets.QLabel("")
        self.lbl_thr.setProperty("dim", True)
        self.spin_thr.valueChanged.connect(self._on_thr_changed)
        sec.add(labeled_row("Arm threshold", self.spin_thr, self.lbl_thr))

        self.spin_mindiff = self._cspin(32000000)
        self.spin_mindiff.setToolTip("Minimum peak-to-trough amplitude "
                                     "required to fire, in raw counts (32-bit).")
        self.lbl_mindiff = QtWidgets.QLabel("")
        self.lbl_mindiff.setProperty("dim", True)
        self.spin_mindiff.valueChanged.connect(self._on_thr_changed)
        sec.add(labeled_row("Min peak-trough", self.spin_mindiff, self.lbl_mindiff))

        self.chk_overlay = QtWidgets.QCheckBox("Show threshold on Scope")
        self.chk_overlay.setChecked(True)
        self.chk_overlay.setToolTip(
            "Draw baseline and baseline±threshold guide lines on the Scope's "
            "magnitude plot for the amplitude channel, so you can see which "
            "peaks would arm a trigger.")
        self.chk_overlay.toggled.connect(self._emit_overlay)
        sec.add(self.chk_overlay)
        self._update_thr_hints()

        self.spin_shift = self._ispin(1, 24, 12)
        self.spin_shift.setToolTip("Baseline smoothing = 2^n records; the time "
                                   "constant depends on the current record rate "
                                   "(200 MHz / R). Larger = slower baseline.")
        self.spin_shift.valueChanged.connect(self._update_baseline_hint)
        self.lbl_base = QtWidgets.QLabel("")
        self.lbl_base.setProperty("dim", True)
        sec.add(labeled_row("Baseline smoothing (2ⁿ)", self.spin_shift,
                            self.lbl_base))
        self._update_baseline_hint()

        self.spin_event = self._dspin(0.1, 200.0, 0.5, 30.0, " ms", 2)
        self.spin_event.setToolTip("Maximum time a single bipolar event may "
                                   "span before the detector resets.")
        sec.add(labeled_row("Max event span", self.spin_event))

        self.spin_holdoff = self._dspin(0.0, 1000.0, 1.0, 50.0, " ms", 2)
        self.spin_holdoff.setToolTip("Debounce: minimum time between fires.")
        sec.add(labeled_row("Hold-off", self.spin_holdoff))
        return sec

    def _build_phase(self):
        sec = CollapsibleSection("Phase classification")
        self.cmb_comb = QtWidgets.QComboBox()
        self.cmb_comb.addItems(["AND (all enabled channels in window)",
                                "OR (any enabled channel in window)"])
        self.cmb_comb.setToolTip("How per-channel phase windows combine into a "
                                 "fire decision.")
        self.cmb_comb.activated.connect(self._apply_if_armed)
        sec.add(labeled_row("Combine", self.cmb_comb))

        self.ph_en, self.ph_mean, self.ph_lo, self.ph_hi = [], [], [], []
        hdr = QtWidgets.QLabel("Per channel:  enable · mean · window low … high")
        hdr.setProperty("dim", True)
        sec.add(hdr)
        for ch in range(4):
            en = QtWidgets.QCheckBox(str(ch))
            en.setToolTip(f"Include channel {ch} in phase classification.")
            en.toggled.connect(self._apply_if_armed)
            mean = self._dspin(-180.0, 180.0, 1.0, 0.0, "°", 1)
            lo = self._dspin(-180.0, 180.0, 1.0, -30.0, "°", 1)
            hi = self._dspin(-180.0, 180.0, 1.0, 30.0, "°", 1)
            for w in (mean, lo, hi):
                w.setMinimumWidth(96)   # fit "-180.0°" + the spin arrows
            self.ph_en.append(en); self.ph_mean.append(mean)
            self.ph_lo.append(lo); self.ph_hi.append(hi)
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            for w in (en, mean, lo, hi):
                row.addWidget(w)
            row.addStretch(1)
            rw = QtWidgets.QWidget(); rw.setLayout(row)
            sec.add(rw)

        row = QtWidgets.QHBoxLayout()
        b_load = QtWidgets.QPushButton("Load calibration…")
        b_load.setToolTip("Load phase means/windows from a calibration JSON "
                          "(accepts the HF2IS calibration.json layout too).")
        b_load.clicked.connect(self._load_calib)
        b_save = QtWidgets.QPushButton("Save calibration…")
        b_save.clicked.connect(self._save_calib)
        row.addWidget(b_load); row.addWidget(b_save); row.addStretch(1)
        rw = QtWidgets.QWidget(); rw.setLayout(row)
        sec.add(rw)
        return sec

    def _build_timing(self):
        sec = CollapsibleSection("Fire timing")
        self.cmb_delay = QtWidgets.QComboBox()
        self.cmb_delay.addItems(["Fixed delay", "Velocity-based delay"])
        self.cmb_delay.setToolTip("Fixed = fire a set time after detection. "
                                  "Velocity = derive the delay from the bead's "
                                  "measured transit time.")
        self.cmb_delay.activated.connect(self._apply_if_armed)
        sec.add(labeled_row("Delay mode", self.cmb_delay))

        self.spin_fixed = self._dspin(0.0, 5000.0, 0.1, 0.0, " ms", 3)
        self.spin_fixed.setToolTip("Fixed delay from detection to firing.")
        sec.add(labeled_row("Fixed delay", self.spin_fixed))

        self.spin_dact = self._dspin(1.0, 1e6, 10.0, 5450.0, " µm", 1)
        self.spin_dwin = self._dspin(1.0, 1e6, 10.0, 200.0, " µm", 1)
        self.spin_dact.setToolTip("Distance from detection to actuation.")
        self.spin_dwin.setToolTip("Length of the detection window.")
        self.spin_dact.valueChanged.connect(self._update_ratio)
        self.spin_dwin.valueChanged.connect(self._update_ratio)
        sec.add(labeled_row("Detect→actuate", self.spin_dact))
        sec.add(labeled_row("Detection window", self.spin_dwin))
        self.lbl_ratio = QtWidgets.QLabel("")
        self.lbl_ratio.setProperty("dim", True)
        sec.add(labeled_row("Distance ratio", self.lbl_ratio))

        self.spin_lead = self._dspin(-1000.0, 1000.0, 0.1, 0.0, " ms", 3)
        self.spin_lead.setToolTip("Fixed correction added to the velocity "
                                  "delay (cabling / mechanical lag).")
        sec.add(labeled_row("Lead offset", self.spin_lead))

        self.spin_pw1 = self._dspin(0.0, 1000.0, 0.1, 1.0, " ms", 3)
        self.spin_pw1.setToolTip("Output 0 pulse width.")
        sec.add(labeled_row("Pulse width (out 0)", self.spin_pw1))
        self.spin_pw2 = self._dspin(0.0, 1000.0, 0.1, 0.0, " ms", 3)
        self.spin_pw2.setToolTip("Output 1 pulse width (0 = single output).")
        sec.add(labeled_row("Pulse width (out 1)", self.spin_pw2))
        self.spin_pair = self._dspin(0.0, 1000.0, 0.1, 0.0, " ms", 3)
        self.spin_pair.setToolTip("Delay of output 1 after output 0.")
        sec.add(labeled_row("Pair delay", self.spin_pair))
        return sec

    def _build_log(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # run summary
        self.lbl_total = QtWidgets.QLabel("0")
        self.lbl_rate = QtWidgets.QLabel("0.0 /s")
        self.lbl_lat = QtWidgets.QLabel("— / — / — ms")
        self.lbl_dly = QtWidgets.QLabel("— / — / — ms")
        for l in (self.lbl_total, self.lbl_rate, self.lbl_lat, self.lbl_dly):
            l.setProperty("heading", True)
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Total fires:"), 0, 0)
        grid.addWidget(self.lbl_total, 0, 1)
        grid.addWidget(QtWidgets.QLabel("Rate:"), 0, 2)
        grid.addWidget(self.lbl_rate, 0, 3)
        grid.addWidget(QtWidgets.QLabel("Latency min/mean/max:"), 1, 0)
        grid.addWidget(self.lbl_lat, 1, 1, 1, 3)
        grid.addWidget(QtWidgets.QLabel("Delay min/mean/max:"), 2, 0)
        grid.addWidget(self.lbl_dly, 2, 1, 1, 3)
        lay.addLayout(grid)

        row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Trigger event log")
        title.setProperty("heading", True)
        row.addWidget(title)
        row.addStretch(1)
        b_clear = QtWidgets.QPushButton("Clear")
        b_clear.clicked.connect(self._clear_log)
        b_csv = QtWidgets.QPushButton("Export CSV…")
        b_csv.clicked.connect(self._export_csv)
        row.addWidget(b_clear); row.addWidget(b_csv)
        lay.addLayout(row)

        self.table = QtWidgets.QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        for i, tip in enumerate(_COL_TIPS):
            self.table.horizontalHeaderItem(i).setToolTip(tip)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        lay.addWidget(self.table, 1)
        return w

    # =====================================================================
    # apply / build config
    # =====================================================================
    def _build_cfg(self, armed):
        c = iza_ctrl.TrigCfg()
        c.mode = iza_ctrl.TRIG_HW if self.chk_hw.isChecked() else iza_ctrl.TRIG_SOFT
        c.arm = 1 if armed else 0
        c.amp_channel = self.cmb_ampch.currentIndex()
        c.polarity = self.cmb_pol.currentIndex()
        c.combine = iza_ctrl.COMB_OR if self.cmb_comb.currentIndex() == 1 \
            else iza_ctrl.COMB_AND
        c.emit_candidates = 1 if self.chk_emit.isChecked() else 0
        mask = 0
        for ch in range(4):
            if self.ph_en[ch].isChecked():
                mask |= (1 << ch)
        c.phase_mask = mask
        c.amp_threshold = int(self.spin_thr.value())      # raw fix32_30 counts
        c.min_peak_diff = int(self.spin_mindiff.value())
        c.baseline_shift = self.spin_shift.value()
        c.holdoff_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_holdoff.value() / 1e3)
        c.event_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_event.value() / 1e3)
        c.watchdog_ms = int(self.spin_wdog.value() * 1000)
        c.delay_mode = iza_ctrl.DLY_VELOCITY if self.cmb_delay.currentIndex() == 1 \
            else iza_ctrl.DLY_FIXED
        c.fixed_delay_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_fixed.value() / 1e3)
        c.lead_offset_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_lead.value() / 1e3)
        c.distance_ratio = self.spin_dact.value() / max(1e-9, self.spin_dwin.value())
        c.pulse_width_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_pw1.value() / 1e3)
        c.pulse_width2_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_pw2.value() / 1e3)
        c.pair_delay_ticks = iza_ctrl.IzaCtrl.sec_to_ticks(self.spin_pair.value() / 1e3)
        c.phase_mean = [math.radians(s.value()) for s in self.ph_mean]
        c.phase_lo = [math.radians(s.value()) for s in self.ph_lo]
        c.phase_hi = [math.radians(s.value()) for s in self.ph_hi]
        return c

    def set_filter_source(self, filters):
        """Give the panel the FilterPanel so the latency estimate can read the
        loaded filter's group delay. Called once from app after construction."""
        self._filters = filters
        self._update_latency()

    @staticmethod
    def _fmt_s(s):
        return f"{s*1e6:.0f} µs" if s < 1e-3 else f"{s*1e3:.3f} ms"

    def _build_latency(self):
        sec = CollapsibleSection("Latency")
        self.spin_rpp = QtWidgets.QSpinBox()
        self.spin_rpp.setRange(1, 255)
        self.spin_rpp.setValue(32)
        self.spin_rpp.setToolTip(
            "Records per DMA packet/buffer (reg4). This is the dominant DMA "
            "latency term: the PS can't see an event until its buffer fills, so "
            "worst-case DMA latency ≈ records/packet ÷ record rate.\n\n"
            "Trade-off (2-buffer ring, RING_DEPTH fixed at 2):\n"
            "• Too small → the buffer fills faster than the PS can be scheduled "
            "to collect it (Linux jitter ~100–200 µs on a non-RT kernel) → ring "
            "overrun / dropped buffers.\n"
            "• Too large → more latency.\n"
            "Sweet spot at R=1000 (200 kHz) is ~32 (≈160 µs buffer). Shared with "
            "the Control tab's Network Packets control (same reg4).")
        self.spin_rpp.valueChanged.connect(self._apply_rpp)
        sec.add(labeled_row("Records per packet", self.spin_rpp))

        # ---- live estimate: ADC -> trigger engine ----
        self.lbl_lat_ctx = QtWidgets.QLabel("")
        self.lbl_lat_ctx.setProperty("dim", True)
        self.lbl_lat_ctx.setToolTip(LAT_ISSUES)
        sec.add(self.lbl_lat_ctx)
        self.lbl_lat_break = QtWidgets.QLabel("")
        self.lbl_lat_break.setProperty("dim", True)
        self.lbl_lat_break.setWordWrap(True)
        self.lbl_lat_break.setToolTip(LAT_ISSUES)
        sec.add(self.lbl_lat_break)
        self.lbl_lat_total = QtWidgets.QLabel("")
        self.lbl_lat_total.setToolTip(LAT_ISSUES)
        sec.add(self.lbl_lat_total)

        self._lat_timer = QtCore.QTimer(self)
        self._lat_timer.timeout.connect(self._update_latency)
        self._lat_timer.start(500)
        self._update_latency()
        return sec

    def _update_latency(self, *_):
        """Estimate ADC → trigger-engine decision latency (CIC+FIR+DMA+PS)."""
        native = current_output_hz()                        # 200 MHz / R
        R = int(round(fd.FS_IN_DEFAULT / native))
        cic = fd.cic_delay_s(R)
        f = getattr(self._filters, "loaded", None)
        if f is not None:
            fir = float(f.metrics.get("group_delay_s", 0.0))
            demod = float(f.metrics.get("total_delay_s", cic + fir))
            fir_txt = self._fmt_s(fir)
        else:
            demod, fir_txt = cic, "unknown"
        rpp = self.spin_rpp.value()
        dma = rpp / native
        total = demod + dma + LAT_PS_S

        self.lbl_lat_ctx.setText(
            f"R={R}  {native/1e3:g} kHz  ·  buffer fill {self._fmt_s(dma)}")
        self.lbl_lat_break.setText(
            f"CIC {self._fmt_s(cic)} · FIR {fir_txt} · "
            f"DMA {self._fmt_s(dma)} · PS {self._fmt_s(LAT_PS_S)}")
        col = theme.GOOD if total < 5e-3 else theme.BAD
        extra = "" if f is not None else "  (+ FIR unknown — load a filter)"
        self.lbl_lat_total.setText(f"Est. ADC→engine: {self._fmt_s(total)}{extra}")
        self.lbl_lat_total.setStyleSheet(f"font-weight:700; color:{col};")

    def _apply_rpp(self, *_):
        self._update_latency()
        n = self.spin_rpp.value()
        self.client.submit(f"records/packet {n}", lambda c: c.set_pkt_cfg(n))

    def _apply(self):
        cfg = self._build_cfg(self.chk_arm.isChecked())
        self.client.submit("trigger", lambda c: c.trig_send(cfg))

    def _apply_if_armed(self, *_):
        if self.chk_arm.isChecked():
            self._apply()

    def _on_arm(self, on):
        self.chk_arm.setText("■ Disarm trigger" if on else "● Arm trigger")
        if on and self._run_t0 is None:
            self._run_t0 = time.time()
        if on:
            self._apply_rpp()          # ensure the configured DMA size is applied
        self._apply()

    def _test_fire(self, mask):
        self.client.submit(f"test-fire {mask:02b}", lambda c: c.trig_test(mask))

    def disarm(self):
        """External disarm request (sends trig_off if connected)."""
        if self.chk_arm.isChecked():
            self.chk_arm.setChecked(False)   # _on_arm -> _apply sends disarm

    def reflect_disarmed(self):
        """Show disarmed WITHOUT sending — used when the link is down and the
        board has (or will) auto-disarm itself via its watchdog."""
        if self.chk_arm.isChecked():
            self.chk_arm.blockSignals(True)
            self.chk_arm.setChecked(False)
            self.chk_arm.setText("● Arm trigger")
            self.chk_arm.blockSignals(False)

    def _update_ratio(self, *_):
        r = self.spin_dact.value() / max(1e-9, self.spin_dwin.value())
        self.lbl_ratio.setText(f"{r:.2f}×")
        self._apply_if_armed()

    def _update_baseline_hint(self, *_):
        n = self.spin_shift.value()
        fs = current_output_hz()            # CIC output = 200 MHz / R (record rate)
        ms = (1 << n) / fs * 1e3            # 2^n records at the current record rate
        self.lbl_base.setText(f"≈ {ms:.2f} ms")

    # =====================================================================
    # events
    # =====================================================================
    def on_event(self, evt):
        passed = bool(evt.get("flags", 0) & iza_ctrl.EVF_PASS)
        self._cands += 1
        if passed:
            self._fires += 1
        peak_s = evt["peak_ts"] / TICK_HZ
        fire_s = evt["fire_ts"] / TICK_HZ
        dt_ms = evt["dt_ticks"] / TICK_HZ * 1e3
        delay_ms = evt["delay_ticks"] / TICK_HZ * 1e3
        lat_ms = evt["latency_ticks"] / TICK_HZ * 1e3
        peak = evt["peak_mag"] / MAG_SCALE
        trough = evt["trough_mag"] / MAG_SCALE
        chans = "".join(str(ch) for ch in range(4)
                        if evt["matched"] & (1 << ch)) or "—"

        if passed:
            self._lat_ms.append(lat_ms)
            self._delay_ms.append(delay_ms)

        cells = [str(evt["seq"]), f"{peak_s:.6f}",
                 "FIRE" if passed else "cand", chans,
                 f"{peak:+.4f}", f"{trough:+.4f}", f"{dt_ms:.3f}",
                 f"{delay_ms:.3f}", f"{lat_ms:.3f}", f"{fire_s:.6f}"]
        self._rows.append(cells)
        self._add_row(cells, passed)
        self._refresh_stats()

    def _add_row(self, cells, passed):
        r = self.table.rowCount()
        self.table.insertRow(r)
        color = theme.ACCENT if passed else theme.TEXT_DIM
        for c, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            if c == 2:
                it.setForeground(QtCore.Qt.GlobalColor.gray if not passed
                                 else QtCore.Qt.GlobalColor.cyan)
            self.table.setItem(r, c, it)
        # cap the visible table (full history stays in self._rows for CSV)
        while self.table.rowCount() > 2000:
            self.table.removeRow(0)
        self.table.scrollToBottom()

    def _refresh_stats(self):
        self.lbl_total.setText(str(self._fires))
        if self._run_t0:
            el = max(1e-6, time.time() - self._run_t0)
            self.lbl_rate.setText(f"{self._fires / el:.2f} /s")
        self.lbl_lat.setText(self._mmm(self._lat_ms))
        self.lbl_dly.setText(self._mmm(self._delay_ms))

    @staticmethod
    def _mmm(vals):
        if not vals:
            return "— / — / — ms"
        return (f"{min(vals):.3f} / {sum(vals)/len(vals):.3f} / "
                f"{max(vals):.3f} ms")

    def _clear_log(self):
        self.table.setRowCount(0)
        self._rows.clear()
        self._fires = self._cands = 0
        self._lat_ms.clear()
        self._delay_ms.clear()
        self._run_t0 = time.time() if self.chk_arm.isChecked() else None
        self._refresh_stats()

    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export trigger event log", "trigger_events.csv",
            "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(_COLS)
                w.writerows(self._rows)
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(e))

    # =====================================================================
    # calibration JSON
    # =====================================================================
    def _save_calib(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save phase calibration", "trigger_calibration.json",
            "JSON files (*.json)")
        if not path:
            return
        data = {
            "combine": "or" if self.cmb_comb.currentIndex() == 1 else "and",
            "channels": [
                {"enabled": self.ph_en[ch].isChecked(),
                 "phase_mean_deg": self.ph_mean[ch].value(),
                 "window_lo_deg": self.ph_lo[ch].value(),
                 "window_hi_deg": self.ph_hi[ch].value()}
                for ch in range(4)],
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(e))

    def _load_calib(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load phase calibration", "", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            QtWidgets.QMessageBox.warning(self, "Load failed", str(e))
            return
        if "channels" in data:                       # our native schema
            for ch, cd in enumerate(data["channels"][:4]):
                self.ph_en[ch].setChecked(bool(cd.get("enabled")))
                self.ph_mean[ch].setValue(cd.get("phase_mean_deg", 0.0))
                self.ph_lo[ch].setValue(cd.get("window_lo_deg", -30.0))
                self.ph_hi[ch].setValue(cd.get("window_hi_deg", 30.0))
            self.cmb_comb.setCurrentIndex(
                1 if str(data.get("combine", "and")).lower() == "or" else 0)
        else:                                         # HF2IS calibration.json
            self._import_hf2is(data)
        self._apply_if_armed()

    # =====================================================================
    # persistence (QSettings) — everything EXCEPT the arm state, which always
    # starts disarmed so reconnecting never fires the actuators unattended
    # =====================================================================
    def _setting_widgets(self):
        combos = [self.cmb_ampch, self.cmb_pol, self.cmb_comb, self.cmb_delay]
        checks = [self.chk_hw, self.chk_emit, self.chk_overlay]
        spins = [self.spin_thr, self.spin_mindiff, self.spin_shift,
                 self.spin_event, self.spin_holdoff, self.spin_fixed,
                 self.spin_dact, self.spin_dwin, self.spin_lead,
                 self.spin_pw1, self.spin_pw2, self.spin_pair, self.spin_wdog,
                 self.spin_rpp]
        per_ch = self.ph_en + self.ph_mean + self.ph_lo + self.ph_hi
        return combos, checks, spins, per_ch

    def save_settings(self, s):
        s.beginGroup("trigger")
        s.setValue("hw", self.chk_hw.isChecked())
        s.setValue("emit", self.chk_emit.isChecked())
        s.setValue("overlay", self.chk_overlay.isChecked())
        s.setValue("ampch", self.cmb_ampch.currentIndex())
        s.setValue("pol", self.cmb_pol.currentIndex())
        s.setValue("combine", self.cmb_comb.currentIndex())
        s.setValue("delay_mode", self.cmb_delay.currentIndex())
        for name, sp in [("thr", self.spin_thr), ("mindiff", self.spin_mindiff),
                         ("shift", self.spin_shift), ("event", self.spin_event),
                         ("holdoff", self.spin_holdoff), ("fixed", self.spin_fixed),
                         ("dact", self.spin_dact), ("dwin", self.spin_dwin),
                         ("lead", self.spin_lead), ("pw1", self.spin_pw1),
                         ("pw2", self.spin_pw2), ("pair", self.spin_pair),
                         ("wdog", self.spin_wdog)]:
            s.setValue(name, sp.value())
        s.setValue("rpp", self.spin_rpp.value())
        for ch in range(4):
            s.setValue(f"ph_en{ch}", self.ph_en[ch].isChecked())
            s.setValue(f"ph_mean{ch}", self.ph_mean[ch].value())
            s.setValue(f"ph_lo{ch}", self.ph_lo[ch].value())
            s.setValue(f"ph_hi{ch}", self.ph_hi[ch].value())
        s.endGroup()

    def load_settings(self, s):
        s.beginGroup("trigger")
        if s.value("thr") is None:          # nothing saved yet
            s.endGroup()
            return
        combos, checks, spins, per_ch = self._setting_widgets()
        for w in combos + checks + spins + per_ch:
            w.blockSignals(True)
        try:
            self.chk_hw.setChecked(s.value("hw", False, type=bool))
            self.chk_emit.setChecked(s.value("emit", True, type=bool))
            self.chk_overlay.setChecked(s.value("overlay", True, type=bool))
            self.cmb_ampch.setCurrentIndex(s.value("ampch", 0, type=int))
            self.cmb_pol.setCurrentIndex(s.value("pol", 0, type=int))
            self.cmb_comb.setCurrentIndex(s.value("combine", 0, type=int))
            self.cmb_delay.setCurrentIndex(s.value("delay_mode", 0, type=int))
            for name, sp in [("thr", self.spin_thr), ("mindiff", self.spin_mindiff),
                             ("shift", self.spin_shift), ("event", self.spin_event),
                             ("holdoff", self.spin_holdoff), ("fixed", self.spin_fixed),
                             ("dact", self.spin_dact), ("dwin", self.spin_dwin),
                             ("lead", self.spin_lead), ("pw1", self.spin_pw1),
                             ("pw2", self.spin_pw2), ("pair", self.spin_pair),
                         ("wdog", self.spin_wdog)]:
                sp.setValue(s.value(name, sp.value(), type=float))
            for ch in range(4):
                self.ph_en[ch].setChecked(s.value(f"ph_en{ch}", False, type=bool))
                self.ph_mean[ch].setValue(s.value(f"ph_mean{ch}", 0.0, type=float))
                self.ph_lo[ch].setValue(s.value(f"ph_lo{ch}", -30.0, type=float))
                self.ph_hi[ch].setValue(s.value(f"ph_hi{ch}", 30.0, type=float))
            self.spin_rpp.setValue(s.value("rpp", 32, type=int))
        finally:
            for w in combos + checks + spins + per_ch:
                w.blockSignals(False)
        # refresh derived UI (hints/ratio/overlay) once, without arming
        self._update_thr_hints()
        self._update_ratio()
        self._update_latency()
        self._emit_overlay()
        s.endGroup()

    def _import_hf2is(self, data):
        """Map the reference calibration.json (lf->ch0, hf->ch1; phase in rad,
        window as a +/- box) onto channels 0 and 1."""
        pairs = [("low_frequency_lf", 0), ("high_frequency_hf", 1)]
        for key, ch in pairs:
            d = data.get(key)
            if not isinstance(d, dict):
                continue
            mean = math.degrees(d.get("bead_phase_mean", 0.0))
            box = d.get("phase_range_box", [0.0, 0.0])
            if isinstance(box, (list, tuple)) and len(box) >= 2:
                lo = math.degrees(box[0]); hi = math.degrees(box[1])
            else:
                half = math.degrees(box if isinstance(box, (int, float)) else 0.0)
                lo, hi = -half, half
            self.ph_en[ch].setChecked(True)
            self.ph_mean[ch].setValue(mean)
            self.ph_lo[ch].setValue(lo)
            self.ph_hi[ch].setValue(hi)
