"""data_stream.py — UDP 7100 ingest for the GUI.

A background daemon thread receives datagrams, parses them with iza_packet, and
pushes decoded record batches into a bounded drop-on-full queue (the canonical
pattern from iza_plotter.py so the GUI can't be swamped at the demod record rate).
A QTimer
on the GUI thread drains the queue and re-emits each batch as a Qt signal, so
every consumer (scope, numeric) receives it safely on the GUI thread.

Fixed-point scaling of the CORDIC polar output (from the modulator_chain IP:
magnitude = fix32_30, phase = fix32_29):
    magnitude = sig   / 2**30
    phase_rad = phase / 2**29
    X = mag*cos(phase_rad),  Y = mag*sin(phase_rad)
"""

import queue
import socket
import struct
import threading
import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

import iza_packet as izp

QUEUE_MAX = 2048     # raw-payload tuples are cheap; more headroom vs GUI stalls

MAG_SCALE = float(1 << 30)      # fix32_30
PHASE_SCALE = float(1 << 29)    # fix32_29
PHASE_TO_DEG = 180.0 / np.pi


def scale_mag(sig):
    """int32 magnitude -> float in DAC-normalised units."""
    return np.asarray(sig, dtype=np.float64) / MAG_SCALE


def scale_phase_rad(phase):
    return np.asarray(phase, dtype=np.float64) / PHASE_SCALE


_HDR = struct.Struct(izp.HDR_FMT)   # (magic,seq,first_ts,mask,stride,flags,plen,..)


def _recv_loop(sock, q, stop):
    """Keep the kernel socket buffer drained.  Do the ABSOLUTE MINIMUM here — a
    cheap header unpack + enqueue the raw payload bytes — and defer the numpy
    deinterleave to the drain, in bulk.  Per-packet numpy on this thread used to
    hold the GIL between recvfrom calls, starving the socket and dropping packets
    at the kernel under load; recvfrom itself releases the GIL, so a lightweight
    loop can keep up even while the GUI thread is busy drawing."""
    sock.settimeout(0.4)
    unpack = _HDR.unpack_from
    hlen = izp.HDR_LEN
    magic = izp.MAGIC
    while not stop.is_set():
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue
        except OSError:
            break
        if len(data) < hlen:
            continue
        h = unpack(data)
        if h[0] != magic:
            continue
        payload = data[hlen:hlen + h[6]]        # h[6] = payload_len
        try:                                     # (seq, mask, stride, payload, nbytes)
            q.put_nowait((h[1], h[3], h[4], payload, len(data)))
        except queue.Full:
            pass


def _batch_sane(rec):
    """Reject misframed transition packets.

    When the board's framing registers change live (channel enables /
    records-per-packet), one or two packets straddle the change: the header
    is fine but the payload record boundaries are wrong, so the 'timestamp'
    field is actually demod data.  Those garbage timestamps poison the plot
    buffers (non-monotonic X breaks pyqtgraph's clip-to-view — traces go
    invisible — and autorange blows out).  Real records tick monotonically
    at the PL rate (~1000 ticks/record); drop anything that doesn't.
    """
    ts = rec.get("ts")
    if ts is None or ts.size < 2:
        return True
    d = np.diff(ts.astype(np.int64))
    if (d <= 0).any():
        return False                    # non-monotonic: misparsed payload
    md = float(np.median(d))
    return 10.0 <= md <= izp.PL_CLK_HZ  # 50 ns .. 1 s per record


class DataStream(QtCore.QObject):
    """Owns the UDP data link.  Emits `batch` per decoded record group and
    `stats` (~2 Hz) with link health."""

    # object, not dict: PySide6 maps Signal(dict) to QVariantMap, which
    # cannot carry our int-keyed / numpy-valued payloads
    batch = QtCore.Signal(object)   # decoded record dict + chan_mask
    stats = QtCore.Signal(object)   # {records_per_s, mbps, alive, mask}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sock = None
        self._thread = None
        self._stop = threading.Event()
        self._q = queue.Queue(maxsize=QUEUE_MAX)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._drain)
        # stats accumulators
        self._rec_acc = 0
        self._byte_acc = 0
        self._last_stat = 0.0
        self._last_rx = 0.0
        self._mask = None
        self._over_acc = False       # any ADC over-range since last stats emit
        self._last_seq = None        # datagram seq, for drop detection
        self._drop_acc = 0           # datagrams missed (seq gaps) since last stat

    # ---- lifecycle ----
    def start(self, port=7100):
        self.stop()
        self._stop.clear()
        self._last_seq = None
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # a big kernel receive buffer absorbs bursts while the GUI thread draws;
        # the OS may clamp this (Linux net.core.rmem_max) — that's fine.
        for want in (32, 16, 8):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, want * 1024 * 1024)
                break
            except OSError:
                continue
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        self._sock = s
        self._thread = threading.Thread(target=_recv_loop,
                                        args=(s, self._q, self._stop),
                                        daemon=True)
        self._thread.start()
        self._last_stat = time.monotonic()
        self._timer.start(33)   # ~30 Hz GUI drain

    def stop(self):
        self._timer.stop()
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        # flush queue
        try:
            while True:
                self._q.get_nowait()
        except queue.Empty:
            pass

    def is_running(self):
        return self._sock is not None

    # ---- GUI-thread drain ----
    def _drain(self):
        # Pull every raw datagram queued this tick, group contiguous ones of the
        # same channel layout, concatenate their payload bytes, and run ONE numpy
        # deinterleave per group.  This replaces thousands of per-packet parses
        # (on the receive thread) with a handful of bulk parses here — far less
        # CPU and Python overhead — and emits ~one batch per tick per group.
        runs = []          # [ [mask, stride, [payload,...], nbytes], ... ]
        got = False
        try:
            while True:
                seq, mask, stride, payload, nbytes = self._q.get_nowait()
                got = True
                self._byte_acc += nbytes
                self._mask = mask
                if self._last_seq is not None:
                    gap = (seq - self._last_seq - 1) & 0xFFFFFFFF
                    if 0 < gap < 1_000_000:      # ignore resets/wraps
                        self._drop_acc += gap
                self._last_seq = seq
                if runs and runs[-1][0] == mask and runs[-1][1] == stride:
                    runs[-1][2].append(payload)
                    runs[-1][3] += nbytes
                else:
                    runs.append([mask, stride, [payload], nbytes])
        except queue.Empty:
            pass
        if got:
            self._last_rx = time.monotonic()

        for mask, stride, payloads, nbytes in runs:
            raw = payloads[0] if len(payloads) == 1 else b"".join(payloads)
            rec = izp.deinterleave(raw, mask, stride)
            if rec is None:
                continue
            rec["chan_mask"] = mask
            rec["nbytes"] = nbytes
            self._rec_acc += rec["n"]
            if not self._over_acc and rec["orf"].size and np.any(rec["orf"]):
                self._over_acc = True    # ADC-wide over-range flag (from ts bits)
            if _batch_sane(rec):
                self.batch.emit(rec)

        now = time.monotonic()
        dt = now - self._last_stat
        if dt >= 0.5:
            self.stats.emit(dict(
                records_per_s=self._rec_acc / dt,
                mbps=self._byte_acc * 8.0 / dt / 1e6,
                alive=(now - self._last_rx) < 1.0,
                mask=self._mask,
                over=self._over_acc,
                drops=self._drop_acc,
            ))
            self._rec_acc = 0
            self._byte_acc = 0
            self._over_acc = False
            self._drop_acc = 0
            self._last_stat = now
