#!/usr/bin/env python3
"""
iza_plotter.py — near-real-time plot of recovered magnitude/phase.

Binds the return port (7100), parses the self-describing demod records streamed
back by iza_replay, and plots recovered magnitude + phase live (PyQtGraph), one
trace per enabled demod channel. If the raw-ADC monitor channel is enabled it is
plotted with a live spectrum (dBFS). An injected reference envelope can be
overlaid on channel 0's magnitude (--ref), per-trace normalized (compare SHAPE,
not amplitude); nudge it with Left/Right (Shift = x10) or --lag-ms.

Usage:
  python iza_plotter.py [--port 7100] [--ref <stem>_adc_int16.bin]
                        [--ref-rate 312500] [--lag-ms 0] [--window 3]
"""

import argparse
import json
import os
import queue
import socket
import sys
import threading
import time

import numpy as np

try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtCore, QtWidgets
except ImportError:
    sys.exit("needs pyqtgraph + a Qt binding:  pip install pyqtgraph pyqt5")

import iza_packet as izp

PL_CLK_HZ = izp.PL_CLK_HZ
NFFT = 8192
ADC_FULLSCALE = 32768.0
CH_COLORS = ["y", "c", "m", (120, 220, 120)]   # per demod channel
MAX_PTS = 20000        # hard cap on points kept per trace (bounds memory/redraw)
QUEUE_MAX = 512        # bounded ingest queue; drop when the GUI falls behind


def _decimate(rec, d):
    if d <= 1:
        return rec
    sl = slice(None, None, d)
    rec["ts"] = rec["ts"][sl]
    rec["orf"] = rec["orf"][sl]
    for ch in rec["sig"]:
        rec["sig"][ch] = rec["sig"][ch][sl]
        rec["phase"][ch] = rec["phase"][ch][sl]
    if rec["adc"] is not None:
        rec["adc"] = rec["adc"][sl]
    rec["n"] = rec["ts"].size
    return rec


def recv_thread(sock, q, stop, decim):
    sock.settimeout(0.5)
    while not stop.is_set():
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue
        if len(data) < izp.HDR_LEN:
            continue
        h = izp.parse_header(data)
        if h["magic"] != izp.MAGIC:
            continue
        payload = data[izp.HDR_LEN:izp.HDR_LEN + h["payload_len"]]
        rec = izp.deinterleave(payload, h["chan_mask"], h["stride_words"])
        if rec:
            rec = _decimate(rec, decim)
            rec["chan_mask"] = h["chan_mask"]
            try:
                q.put_nowait(rec)          # drop-on-full: never grow unbounded
            except queue.Full:
                pass


def ref_native_rate(path, override):
    if override and override > 0:
        return float(override)
    for cand in (path + ".json", os.path.splitext(path)[0] + ".json"):
        if os.path.exists(cand):
            try:
                meta = json.load(open(cand))
                r = meta.get("zi_meta", {}).get("estimated_sample_rate_hz")
                if r:
                    return float(r)
            except Exception:
                pass
    return 0.0


def normalize(a):
    if a.size == 0:
        return a
    span = np.ptp(a)
    return (a - a.min()) / (span if span else 1.0)


class Plotter(QtWidgets.QWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.q = queue.Queue(maxsize=QUEUE_MAX)
        self.stop = threading.Event()

        self.ref = None
        self.ref_rate = 0.0
        if args.ref:
            self.ref = np.fromfile(args.ref, dtype="<i2").astype(np.float64)
            if self.ref.size == 0:
                self.ref = None
                print("WARNING: empty --ref file; no overlay", file=sys.stderr)
            else:
                self.ref_rate = ref_native_rate(args.ref, args.ref_rate)
                if self.ref_rate <= 0:
                    sys.exit("could not determine the --ref file's sample rate; "
                             "pass --ref-rate <Hz>")
                print(f"ref overlay: {args.ref} @ {self.ref_rate:.1f} Hz native")
        self.lag_ms = float(args.lag_ms)
        self.sync_path = args.sync
        self.base_pos = 0.0

        # rolling buffers (one shared time axis; per-channel value buffers)
        self.chan_mask = None
        self.demod = []
        self.have_adc = False
        self.t = np.empty(0)
        self.mag = {}      # ch -> array
        self.ph = {}       # ch -> array
        self.orf = np.empty(0, dtype=np.uint8)
        self.adc = np.empty(0)
        self.t0_ts = None
        self.or_total = 0
        self._last_fs = 1.0 / 5e-6

        # curve handles (created lazily once the mask is known)
        self.c_mag = {}
        self.c_ph = {}
        self.c_ref = None
        self.c_adc = None

        # --- UI ---
        self.setWindowTitle("iza_plotter — recovered magnitude / phase")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        lay = QtWidgets.QVBoxLayout(self)
        self.glw = pg.GraphicsLayoutWidget()
        lay.addWidget(self.glw)
        self.status = QtWidgets.QLabel("waiting for data…")
        lay.addWidget(self.status)

        self.p_mag = self.glw.addPlot(row=0, col=0,
                                      title="magnitude (normalized) per channel")
        self.p_mag.showGrid(x=True, y=True, alpha=0.3)
        self.p_mag.setDownsampling(auto=True)
        self.p_mag.setClipToView(True)
        self.p_mag.addLegend()
        self.c_or = pg.ScatterPlotItem(size=8, pen=None,
                                       brush=pg.mkBrush(255, 40, 40, 220))
        self.p_mag.addItem(self.c_or)

        self.p_ph = self.glw.addPlot(row=1, col=0, title="recovered phase (raw)")
        self.p_ph.showGrid(x=True, y=True, alpha=0.3)
        self.p_ph.setDownsampling(auto=True)
        self.p_ph.setClipToView(True)
        self.p_ph.setXLink(self.p_mag)

        self.p_adc = self.glw.addPlot(row=2, col=0, title="raw ADC (signed)")
        self.p_adc.showGrid(x=True, y=True, alpha=0.3)
        self.p_adc.setDownsampling(auto=True)
        self.p_adc.setClipToView(True)
        self.p_adc.setXLink(self.p_mag)

        self.p_fft = self.glw.addPlot(row=3, col=0, title="raw ADC spectrum (dBFS)")
        self.p_fft.showGrid(x=True, y=True, alpha=0.3)
        self.p_fft.setLabel("bottom", "frequency", units="Hz")
        self.p_fft.setLabel("left", "dBFS")
        self.p_fft.setYRange(-140, 5)
        self.c_fft = self.p_fft.plot(pen=pg.mkPen((80, 200, 255), width=1))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        self.sock.bind(("0.0.0.0", args.port))
        self.rx = threading.Thread(target=recv_thread,
                                   args=(self.sock, self.q, self.stop, args.decimate),
                                   daemon=True)
        self.rx.start()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(33)

    def _build_curves(self, chan_mask):
        """Create per-channel curves once the stream layout is known."""
        self.chan_mask = chan_mask
        self.demod = izp.demod_list(chan_mask)
        self.have_adc = izp.adc_enabled(chan_mask)
        for k, ch in enumerate(self.demod):
            col = CH_COLORS[ch % len(CH_COLORS)]
            self.c_mag[ch] = self.p_mag.plot(pen=pg.mkPen(col, width=1),
                                             name=f"ch{ch}")
            self.c_ph[ch] = self.p_ph.plot(pen=pg.mkPen(col, width=1))
            self.mag[ch] = np.empty(0)
            self.ph[ch] = np.empty(0)
        if self.ref is not None and self.demod:
            self.c_ref = self.p_mag.plot(pen=pg.mkPen("w", width=1), name="ref")
        if self.have_adc:
            self.c_adc = self.p_adc.plot(pen=pg.mkPen("m", width=1))
        else:
            self.p_adc.setTitle("raw ADC (channel not enabled)")
            self.p_fft.setTitle("raw ADC spectrum (channel not enabled)")
        print(f"stream layout: demod={self.demod} adc={self.have_adc}")

    def keyPressEvent(self, e):
        step = 10.0 if (e.modifiers() & QtCore.Qt.ShiftModifier) else 1.0
        if e.key() == QtCore.Qt.Key_Left:
            self.lag_ms -= step
        elif e.key() == QtCore.Qt.Key_Right:
            self.lag_ms += step
        else:
            super().keyPressEvent(e)

    def update(self):
        batches = []
        try:
            while True:
                batches.append(self.q.get_nowait())
        except queue.Empty:
            pass

        for b in batches:
            if self.chan_mask is None:
                self._build_curves(b["chan_mask"])
            if b["chan_mask"] != self.chan_mask:
                continue   # layout changed mid-run; ignore until restart

            ts = b["ts"]
            if self.t0_ts is None:
                self.t0_ts = int(ts[0])
                if self.sync_path and self.ref is not None:
                    try:
                        t0w = float(json.load(open(self.sync_path))["t0_wall"])
                        self.base_pos = (time.time() - t0w) * self.ref_rate
                        print(f"sync: base_pos={self.base_pos:.0f} samples")
                    except Exception as e:
                        print(f"WARNING: --sync read failed ({e})", file=sys.stderr)
                        self.sync_path = None
            t = (ts.astype(np.float64) - float(self.t0_ts)) / PL_CLK_HZ
            self.t = np.concatenate([self.t, t])
            self.orf = np.concatenate([self.orf, b["orf"]])
            self.or_total += int(np.count_nonzero(b["orf"]))
            for ch in self.demod:
                self.mag[ch] = np.concatenate([self.mag[ch],
                                               b["sig"][ch].astype(np.float64)])
                self.ph[ch] = np.concatenate([self.ph[ch],
                                              b["phase"][ch].astype(np.float64)])
            if self.have_adc and b["adc"] is not None:
                self.adc = np.concatenate([self.adc, b["adc"].astype(np.float64)])

        if self.t.size == 0:
            return

        # trim to the visible window (adc is appended every batch when enabled,
        # so it stays the same length as t)
        t_now = self.t[-1]
        keep = self.t >= (t_now - self.args.window)
        self.t = self.t[keep]
        self.orf = self.orf[keep]
        for ch in self.demod:
            self.mag[ch] = self.mag[ch][keep]
            self.ph[ch] = self.ph[ch][keep]
        if self.have_adc:
            self.adc = self.adc[keep]

        # hard point cap — bounds memory + redraw even if window*rate is huge
        if self.t.size > MAX_PTS:
            self.t = self.t[-MAX_PTS:]
            self.orf = self.orf[-MAX_PTS:]
            for ch in self.demod:
                self.mag[ch] = self.mag[ch][-MAX_PTS:]
                self.ph[ch] = self.ph[ch][-MAX_PTS:]
            if self.have_adc:
                self.adc = self.adc[-MAX_PTS:]

        over = self.orf != 0
        for ch in self.demod:
            magn = normalize(self.mag[ch])
            self.c_mag[ch].setData(self.t, magn)
            self.c_ph[ch].setData(self.t, self.ph[ch])
        # OR markers on channel 0's magnitude trace
        if self.demod:
            m0 = normalize(self.mag[self.demod[0]])
            self.c_or.setData(self.t[over], m0[over])

        # --- live raw-ADC spectrum ---
        if self.have_adc and self.adc.size >= 256:
            n = int(min(NFFT, self.adc.size))
            seg = self.adc[-n:] - self.adc[-n:].mean()
            dt = np.diff(self.t[-n:]) if self.t.size >= n else np.array([])
            med = np.median(dt) if dt.size else 0.0
            fs = (1.0 / med) if med > 0 else self._last_fs
            self._last_fs = fs
            w = np.hanning(n)
            amp = 2.0 * np.abs(np.fft.rfft(seg * w)) / np.sum(w)
            freqs = np.fft.rfftfreq(n, d=1.0 / fs)
            dbfs = 20.0 * np.log10(np.maximum(amp, 1e-6) / ADC_FULLSCALE)
            self.c_adc.setData(self.t, self.adc)
            self.c_fft.setData(freqs, dbfs)
            pk = int(np.argmax(amp))
            self.p_fft.setTitle("raw ADC spectrum — peak %.1f kHz @ %.1f dBFS "
                                "(fs=%.1f kHz)"
                                % (freqs[pk] / 1e3, dbfs[pk], fs / 1e3))

        lost_note = ""
        if self.c_ref is not None:
            n = self.ref.size
            idx = ((self.base_pos
                    + (self.t - self.lag_ms / 1000.0) * self.ref_rate)
                   .astype(np.int64)) % n
            self.c_ref.setData(self.t, normalize(self.ref[idx]))
            anchor = "sync" if self.sync_path else "manual"
            lost_note = f"  lag={self.lag_ms:+.0f} ms ({anchor}; ←/→, Shift=x10)"

        n_or = int(np.count_nonzero(self.orf))
        or_note = (f"   OR: {n_or}/{self.orf.size} in window (total {self.or_total})"
                   + ("  ⚠ OVER-RANGE — reduce PGA / input" if n_or else ""))
        self.status.setText(
            f"records in window: {self.t.size}   span: {self.args.window:.1f}s"
            f"   demod={self.demod}{or_note}{lost_note}")

    def closeEvent(self, e):
        self.stop.set()
        super().closeEvent(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7100)
    ap.add_argument("--ref", help="<stem>_adc_int16.bin to overlay on ch0")
    ap.add_argument("--ref-rate", type=float, default=0.0,
                    help="samples/real-second of the --ref file")
    ap.add_argument("--sync",
                    help="sync file from iza_sender --sync-file; anchors the "
                         "overlay to the sender position via the shared wall clock")
    ap.add_argument("--lag-ms", type=float, default=0.0,
                    help="reference time shift (live: arrow keys)")
    ap.add_argument("--window", type=float, default=3.0,
                    help="scrolling window length in seconds")
    ap.add_argument("--decimate", type=int, default=10,
                    help="keep every Nth record for display (cuts the demod "
                         "record rate down to a plottable rate; raise if the GUI "
                         "still lags). NOTE: also decimates the ADC spectrum.")
    args = ap.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = Plotter(args)
    w.resize(1100, 760)
    w.show()
    print(f"listening on UDP {args.port}; close the window to quit")
    sys.exit(app.exec_() if hasattr(app, "exec_") else app.exec())


if __name__ == "__main__":
    main()
