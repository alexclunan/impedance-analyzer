"""numeric_panel.py — LabOne-style big live readouts per demod channel.

Per enabled demod channel: R (magnitude), Phase, X, Y as large SI-formatted
values.  Each has a persistence-histogram bar: every 10 Hz poll drops a thin
block at that value's position and the blocks fade over a couple of seconds, so
a steady value shows a bright stack and a noisy one spreads out — a live view of
where the value has been.  A bright marker shows the current value; the ends are
labelled Min / Max (recent extremes).

Magnitudes are dimensionless (fraction of full scale), shown with SI prefixes as
"µFS" etc. — deliberately not volts (the ADC input range isn't characterised).
ADC over-range is instrument-wide (shared input) and shown once in the top
connection bar, not per channel.
"""

import math
import time

import numpy as np
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

import iza_packet as izp
from . import data_stream as ds
from . import theme

AVG_SAMPLES = 512      # rolling window for the displayed average
_VALUE_PT = 45         # big value font size
_FADE_S = 2.5          # persistence-block disappear delay


def _si(v, base="FS"):
    """Format a value with an SI prefix -> (mantissa_str, unit_str)."""
    if v == 0 or not math.isfinite(v):
        return "0.00", base
    a = abs(v)
    p3 = int(math.floor(math.log10(a) / 3.0)) * 3
    p3 = max(-12, min(0, p3))                 # our values are <= ~1.6 (fraction)
    mant = v / (10.0 ** p3)
    prefix = {0: "", -3: "m", -6: "µ", -9: "n", -12: "p"}[p3]
    if abs(mant) >= 100:
        s = f"{mant:.1f}"
    elif abs(mant) >= 10:
        s = f"{mant:.2f}"
    else:
        s = f"{mant:.3f}"
    return s, prefix + base


def _fmt_fs(v):
    m, u = _si(v)
    return f"{m} {u}"


def _fmt_deg(v):
    return f"{v:.1f}°"


class _HistBar(QtWidgets.QWidget):
    """Persistence histogram: fading blocks at each polled value + a current
    marker, auto-ranging to the recent span.  Exposes .hmin/.hmax."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._c = QtGui.QColor(*color)
        self.setFixedHeight(22)
        self.setMinimumWidth(80)
        self.samples = []          # (value, birth_monotonic)
        self.val = 0.0
        self.hmin = self.hmax = 0.0
        self.lo, self.hi = 0.0, 1.0
        self._has = False

    def set_value(self, v):
        now = time.monotonic()
        self.samples.append((v, now))
        self.samples = [(val, t) for (val, t) in self.samples if now - t < _FADE_S]
        vals = [val for val, _ in self.samples]
        self.val = v
        self.hmin, self.hmax = min(vals), max(vals)
        self._has = True
        span = self.hmax - self.hmin
        if span <= 0:                       # constant so far: frame ±10% of value
            m = max(abs(v), 1e-9)
            self.lo, self.hi = v - 0.1 * m, v + 0.1 * m
        else:
            pad = 0.12 * span
            self.lo, self.hi = self.hmin - pad, self.hmax + pad
        self.update()

    def clear(self):
        self.samples = []
        self._has = False
        self.val = self.hmin = self.hmax = 0.0
        self.update()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        span = self.hi - self.lo
        if span <= 0:
            span = 1.0

        def xof(v):
            return max(0.0, min(1.0, (v - self.lo) / span)) * w

        # track
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(theme.PLOT_BG))
        p.drawRoundedRect(QtCore.QRectF(0, 1, w, h - 2), 3, 3)
        if not self._has:
            p.end()
            return
        # fading persistence blocks
        now = time.monotonic()
        for val, t in self.samples:
            a = 1.0 - (now - t) / _FADE_S
            if a <= 0:
                continue
            c = QtGui.QColor(self._c)
            c.setAlpha(int(30 + 200 * a))
            p.setBrush(c)
            p.drawRect(QtCore.QRectF(xof(val) - 2.0, 2, 4.0, h - 4))
        # bright current-value marker
        p.setBrush(QtGui.QColor(self._c).lighter(160))
        p.drawRect(QtCore.QRectF(xof(self.val) - 1.0, 0, 2.0, h))
        p.end()


class _MetricCard(QtWidgets.QWidget):
    """One metric: name, big current value, a persistence histogram, Min/Max."""

    def __init__(self, name, color, fmt, parent=None):
        super().__init__(parent)
        self._fmt = fmt
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(1)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(6)
        self.name = QtWidgets.QLabel(name)
        self.name.setStyleSheet(f"color: rgb{tuple(color)};")
        nf = self.name.font(); nf.setPointSize(13); nf.setBold(True)
        self.name.setFont(nf)
        cur = QtWidgets.QLabel("current value")
        cur.setProperty("dim", True)
        big = QtGui.QFont("Consolas")
        big.setPointSize(_VALUE_PT)
        big.setStyleHint(QtGui.QFont.Monospace)
        self.val = QtWidgets.QLabel("—")
        self.val.setFont(big)
        self.val.setStyleSheet(f"color: rgb{tuple(color)};")
        self.val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.unit = QtWidgets.QLabel("")
        self.unit.setProperty("dim", True)
        self.unit.setMinimumWidth(48)
        top.addWidget(self.name)
        top.addStretch(1)
        top.addWidget(cur)
        top.addWidget(self.val)
        top.addWidget(self.unit)
        lay.addLayout(top)

        self.bar = _HistBar(color)
        lay.addWidget(self.bar)

        ends = QtWidgets.QHBoxLayout()
        ends.setContentsMargins(0, 0, 0, 0)
        self.lo_lbl = QtWidgets.QLabel("")
        self.hi_lbl = QtWidgets.QLabel("")
        for l in (self.lo_lbl, self.hi_lbl):
            l.setProperty("dim", True)
            f = l.font(); f.setPointSize(9); l.setFont(f)
        self.hi_lbl.setAlignment(QtCore.Qt.AlignRight)
        ends.addWidget(self.lo_lbl)
        ends.addStretch(1)
        ends.addWidget(self.hi_lbl)
        lay.addLayout(ends)

    def set(self, mant, unit, raw):
        self.val.setText(mant)
        self.unit.setText(unit)
        self.bar.set_value(raw)
        self.lo_lbl.setText("Min: " + self._fmt(self.bar.hmin))
        self.hi_lbl.setText("Max: " + self._fmt(self.bar.hmax))

    def clear(self):
        self.val.setText("—")
        self.unit.setText("")
        self.bar.clear()
        self.lo_lbl.setText("")
        self.hi_lbl.setText("")


class _ChannelCard(QtWidgets.QGroupBox):
    def __init__(self, ch, parent=None):
        super().__init__(f"Demod {ch}", parent)
        col = theme.channel_color(ch)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(6)

        self.cards = {}
        for key, label, fmt in [("r", "R", _fmt_fs), ("phase", "Phase", _fmt_deg),
                                 ("x", "X", _fmt_fs), ("y", "Y", _fmt_fs)]:
            c = _MetricCard(label, col, fmt)
            self.cards[key] = c
            lay.addWidget(c)
        lay.addStretch(1)                 # pack metrics to the top, no dead gaps

    def update_values(self, mag, phase_rad):
        x = mag * math.cos(phase_rad)
        y = mag * math.sin(phase_rad)
        deg = math.degrees(phase_rad)
        self.cards["r"].set(*_si(mag), mag)
        self.cards["phase"].set(f"{deg:+.2f}", "°", deg)
        self.cards["x"].set(*_si(x), x)
        self.cards["y"].set(*_si(y), y)

    def clear(self):
        for c in self.cards.values():
            c.clear()


class NumericPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chan_mask = None
        self.demod = []
        self.buf_sig = {}       # ch -> recent scaled magnitude
        self.buf_phr = {}       # ch -> recent phase (rad)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)
        legend = QtWidgets.QLabel(
            "R · X · Y are a fraction of full scale (µ = ×10⁻⁶, m = ×10⁻³);  "
            "Phase is in degrees.  The bar is a fading histogram of the last "
            f"~{_FADE_S:g} s of readings — the bright marker is the current "
            "value, blocks show where it has been, and the ends are the recent "
            "Min / Max.")
        legend.setWordWrap(True)
        legend.setProperty("dim", True)
        outer.addWidget(legend)

        gridw = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(gridw)
        self.grid.setSpacing(10)
        self.cards = {}
        self.placeholder = QtWidgets.QLabel("Connect and enable demod channels…")
        self.placeholder.setProperty("dim", True)
        self.placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.placeholder, 0, 0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(gridw)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(100)   # 10 Hz

    def _rebuild(self, chan_mask):
        for c in self.cards.values():
            c.setParent(None)
        self.cards = {}
        self.placeholder.setVisible(False)
        self.chan_mask = chan_mask
        self.demod = izp.demod_list(chan_mask)
        self.buf_sig = {ch: np.empty(0) for ch in self.demod}
        self.buf_phr = {ch: np.empty(0) for ch in self.demod}
        if not self.demod:
            self.placeholder.setVisible(True)
            return
        for i, ch in enumerate(self.demod):
            card = _ChannelCard(ch)
            self.cards[ch] = card
            self.grid.addWidget(card, i // 2, i % 2)

    def on_batch(self, b):
        if b["chan_mask"] != self.chan_mask:
            self._rebuild(b["chan_mask"])
        for ch in self.demod:
            self.buf_sig[ch] = _tail(np.concatenate(
                [self.buf_sig[ch], ds.scale_mag(b["sig"][ch])]), AVG_SAMPLES)
            self.buf_phr[ch] = _tail(np.concatenate(
                [self.buf_phr[ch], ds.scale_phase_rad(b["phase"][ch])]), AVG_SAMPLES)

    def _refresh(self):
        if not self.isVisible():
            return              # don't compute/repaint readouts on a hidden tab
        for ch, card in self.cards.items():
            if self.buf_sig[ch].size == 0:
                continue
            card.update_values(float(np.mean(self.buf_sig[ch])),
                               float(np.mean(self.buf_phr[ch])))

    def clear(self):
        for c in self.cards.values():
            c.clear()


def _tail(a, n):
    return a[-n:] if a.size > n else a
