"""control_client.py — GUI wrapper around iza_ctrl.IzaCtrl.

Every control call (a UDP request/response with a 1 s timeout on the board side)
runs on a single-thread QThreadPool worker, so a slow or missing board never
freezes the UI, and calls stay serialised (one shared control socket).  Results
and errors come back as Qt signals.  A periodic poller reads the run/channel
registers so the UI reflects the live board state and link health.
"""

import queue
import socket
import threading
from contextlib import contextmanager

from pyqtgraph.Qt import QtCore

import iza_ctrl

# Registers whose write-verification mismatch is expected because the chip
# clears the bit itself (handshake/commit registers): warn softly, not loudly.
_SELF_CLEARING = {
    ("dac", 0x00),   # Comm: software reset bit
    ("dac", 0x18),   # FIFO soft-align request/ack handshake
    ("dac", 0x36),   # NCO FTW update request/ack handshake
    ("adc", 0x00),   # chip_port_config: soft reset
    ("adc", 0xFF),   # device_update: SW transfer self-clears
}


class VerifyingCtrl(iza_ctrl.IzaCtrl):
    """IzaCtrl that (a) reads every written register back and compares it to
    the value sent, and (b) reports each command + response through a log
    callback (the GUI console).  `quiet` suppresses logging (status polls)."""

    def __init__(self, board, port, timeout, log_cb):
        super().__init__(board, port, timeout)
        self._log_cb = log_cb
        self._depth = 0          # >0 = inside a compound op: skip inner logs
        self.quiet = False

    # ---- logging helpers ----
    def _log(self, kind, text):
        if not self.quiet and self._depth == 0:
            self._log_cb(kind, text)

    @contextmanager
    def _nested(self):
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1

    # ---- FPGA AXI registers ----
    def reg_read(self, reg):
        try:
            val = super().reg_read(reg)
        except Exception as e:
            self._log("err", f"regread  {reg:<2}  FAILED: {e}")
            raise
        self._log("ok", f"regread  {reg:<2}  -> 0x{val:08X}")
        return val

    def reg_write(self, reg, value):
        value &= 0xFFFFFFFF
        try:
            super().reg_write(reg, value)
            with self._nested():
                rb = super().reg_read(reg)
        except Exception as e:
            self._log("err", f"regwrite {reg:<2} <- 0x{value:08X}  FAILED: {e}")
            raise
        if rb == value:
            self._log("ok", f"regwrite {reg:<2} <- 0x{value:08X}  verified")
        else:
            self._log("warn", f"regwrite {reg:<2} <- 0x{value:08X}  "
                              f"READBACK 0x{rb:08X} MISMATCH")
        return rb

    # ---- converter chips over SPI ----
    def spi(self, bus, data):
        name = "dac" if bus == iza_ctrl.SPI_DAC else "adc"
        try:
            rx = super().spi(bus, data)
        except Exception as e:
            self._log("err", f"spi {name}  tx "
                             + " ".join(f"{b:02X}" for b in data)
                             + f"  FAILED: {e}")
            raise
        self._log("ok", f"spi {name}  tx "
                        + " ".join(f"{b:02X}" for b in data)
                        + "  rx " + " ".join(f"{b:02X}" for b in bytes(rx)))
        return rx

    def _chip_write(self, chip, addr, val, write, read):
        try:
            with self._nested():
                write()
                rb = read()
        except Exception as e:
            self._log("err",
                      f"{chip}write 0x{addr:02X} <- 0x{val:02X}  FAILED: {e}")
            raise
        if rb == val & 0xFF:
            self._log("ok", f"{chip}write 0x{addr:02X} <- 0x{val:02X}  verified")
        elif (chip, addr) in _SELF_CLEARING:
            self._log("ok", f"{chip}write 0x{addr:02X} <- 0x{val:02X}  "
                            f"readback 0x{rb if rb is not None else 0:02X} "
                            f"(self-clearing register)")
        else:
            self._log("warn", f"{chip}write 0x{addr:02X} <- 0x{val:02X}  "
                              f"READBACK "
                              + (f"0x{rb:02X}" if rb is not None else "none")
                              + " MISMATCH")
        return rb

    def dac_write(self, addr, val):
        return self._chip_write("dac", addr, val & 0xFF,
                                lambda: super(VerifyingCtrl, self).dac_write(addr, val),
                                lambda: super(VerifyingCtrl, self).dac_read(addr))

    def dac_read(self, addr):
        with self._nested():
            v = super().dac_read(addr)
        self._log("ok", "dacread  0x%02X  -> " % addr
                  + (f"0x{v:02X}" if v is not None else "no reply"))
        return v

    def adc_write(self, addr, val, commit=True):
        return self._chip_write("adc", addr, val & 0xFF,
                                lambda: super(VerifyingCtrl, self).adc_write(addr, val, commit),
                                lambda: super(VerifyingCtrl, self).adc_read(addr))

    def adc_read(self, addr):
        with self._nested():
            v = super().adc_read(addr)
        self._log("ok", "adcread  0x%02X  -> " % addr
                  + (f"0x{v:02X}" if v is not None else "no reply"))
        return v


class _WorkerSignals(QtCore.QObject):
    done = QtCore.Signal(str, object)     # (label, return value)
    failed = QtCore.Signal(str, str)      # (label, message)


class _Task(QtCore.QRunnable):
    def __init__(self, label, fn, signals):
        super().__init__()
        self.label = label
        self.fn = fn
        self.signals = signals

    def run(self):
        try:
            result = self.fn()
        except Exception as e:                      # incl. iza_ctrl.CtrlError
            self.signals.failed.emit(self.label, str(e))
        else:
            self.signals.done.emit(self.label, result)


class ControlClient(QtCore.QObject):
    """Async control front-end.  Connect signals, then call submit()/connect_board()."""

    connected = QtCore.Signal(bool)
    result = QtCore.Signal(str, object)     # (label, value) for user-visible ops
    error = QtCore.Signal(str, str)         # (label, message)
    # NOTE: object, not dict — PySide6 converts Signal(dict) to QVariantMap,
    # which silently rejects int-keyed dicts like our register maps.
    status = QtCore.Signal(object)          # polled register readback
    log = QtCore.Signal(str, str)           # (kind: cmd/ok/warn/err, text)
    trigger_event = QtCore.Signal(object)   # decoded trigger-event dict (async)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctrl = None
        self.log_polling = False            # console checkbox: log 1 Hz polls?
        self._pending = 0                   # tasks queued/running on the worker
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(1)     # serialise: single shared socket
        self._sig = _WorkerSignals()
        self._sig.done.connect(self._on_done)
        self._sig.failed.connect(self._on_failed)
        self._poll = QtCore.QTimer(self)
        self._poll.timeout.connect(self._poll_status)
        # async trigger-event receiver (board -> PC, UDP EVT_PORT)
        self._evt_sock = None
        self._evt_thread = None
        self._evt_run = False
        self._evt_q = queue.Queue(512)
        self._evt_timer = QtCore.QTimer(self)
        self._evt_timer.timeout.connect(self._drain_events)

    # ---- connection ----
    def connect_board(self, ip, port=iza_ctrl.CTRL_PORT):
        # emitting a signal from the worker thread is thread-safe (queued)
        self.ctrl = VerifyingCtrl(ip, port, timeout=1.0, log_cb=self.log.emit)
        self.log.emit("cmd", f"connect {ip}:{port}")
        self.connected.emit(True)
        self._start_events()
        self._poll_status()
        self._poll.start(1000)

    def disconnect_board(self):
        self._poll.stop()
        self._stop_events()
        if self.ctrl is not None:
            self.log.emit("cmd", "disconnect")
        self.ctrl = None
        self.connected.emit(False)

    def is_connected(self):
        return self.ctrl is not None

    # ---- async trigger-event receiver ----
    def _start_events(self):
        if self._evt_sock is not None:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", iza_ctrl.EVT_PORT))
            s.settimeout(0.3)
        except OSError as e:
            self.log.emit("warn", f"trigger events: cannot bind UDP "
                                  f"{iza_ctrl.EVT_PORT}: {e}")
            return
        self._evt_sock = s
        self._evt_run = True
        self._evt_thread = threading.Thread(target=self._evt_loop, daemon=True)
        self._evt_thread.start()
        self._evt_timer.start(50)

    def _stop_events(self):
        self._evt_run = False
        self._evt_timer.stop()
        s, self._evt_sock = self._evt_sock, None
        if s is not None:
            try:
                s.close()
            except OSError:
                pass
        self._evt_thread = None

    def _evt_loop(self):
        sock = self._evt_sock
        while self._evt_run and sock is not None:
            try:
                buf, _ = sock.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break
            evt = iza_ctrl.parse_trig_evt(buf)
            if evt is None:
                continue
            try:
                self._evt_q.put_nowait(evt)
            except queue.Full:
                pass                       # drop-on-full: UI can't keep up

    def _drain_events(self):
        while True:
            try:
                evt = self._evt_q.get_nowait()
            except queue.Empty:
                break
            self.trigger_event.emit(evt)

    # ---- dispatch ----
    def submit(self, label, fn):
        """Run fn(ctrl) on the worker thread. `label` is echoed in result/error.
        Silently ignored if not connected (except surfaced as an error)."""
        if self.ctrl is None:
            self.error.emit(label, "not connected")
            return
        ctrl = self.ctrl
        if not label.startswith("__"):
            self.log.emit("cmd", label)
        self._pending += 1
        self._pool.start(_Task(label, lambda: fn(ctrl), self._sig))

    # ---- status poll ----
    def _poll_status(self):
        if self.ctrl is None:
            return
        # Skip this tick if work is already queued: commands in flight both
        # prove the link is alive and would delay the poll past its own
        # timeout window (a UDP poll racing a busy queue looks like a dead
        # link when it is merely a slow one).
        if self._pending > 0:
            return
        ctrl = self.ctrl
        log_poll = self.log_polling

        def read():
            # suppress console logging for the periodic poll unless enabled
            ctrl.quiet = not log_poll
            regs = {}
            try:
                for i in range(16):     # 0..10 core + 11..15 trigger/spare regs
                    try:
                        regs[i] = ctrl.reg_read(i)
                    except Exception:
                        # UDP has no retransmit: one lost/late datagram must
                        # not declare the link dead — retry once, and only a
                        # back-to-back failure aborts the poll
                        regs[i] = ctrl.reg_read(i)
            finally:
                ctrl.quiet = False
            return regs

        self._pending += 1
        self._pool.start(_Task("__status__", read, self._sig))

    # ---- worker callbacks (GUI thread) ----
    def _on_done(self, label, value):
        self._pending = max(0, self._pending - 1)
        if label == "__status__":
            self.status.emit(value)
        else:
            self.result.emit(label, value)

    def _on_failed(self, label, msg):
        self._pending = max(0, self._pending - 1)
        if label == "__status__":
            # a failed poll means the link is down; report as a status with no regs
            self.status.emit({})
        else:
            self.error.emit(label, msg)
