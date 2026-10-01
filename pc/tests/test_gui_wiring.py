"""Run from pc/: python -B -m unittest discover -s tests -v

How the DAC re-init warning is wired: the status-poll probe, stale-result
dropping in ControlClient, and the panel / status bar / command log through a
real (offscreen, never shown) MainWindow.  Skipped if no Qt binding."""

import os
import threading
import unittest
from unittest import mock

import iza_ctrl

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from pyqtgraph.Qt import QtWidgets
    from iza_gui import control_client as cc
    from iza_gui import dac_state as ds
    from iza_gui.app import MainWindow
    from iza_gui.control_client import ControlClient, read_status
    from iza_gui.control_panel import _fmt_actual
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
except Exception as e:                       # no Qt binding: skip
    _QT_ERROR = e
else:
    _QT_ERROR = None

RUNNING = iza_ctrl.SYS_RUN
GOOD_INIT = {"align_ack": True, "level_ok": True, "warnings_clear": True}
HELD_MSG = ("DAC chip held in reset (SYS_CTRL0 bit4=0) — run 'run' before "
            "dac-init or the SPI path is dead")


def fake_ctrl(r0, fmt=0x01):
    ctrl = mock.Mock()
    ctrl.reg_read.side_effect = lambda i: r0 if i == 0 else 0
    ctrl.dac_read.return_value = fmt
    return ctrl


@unittest.skipIf(_QT_ERROR is not None, f"Qt unavailable: {_QT_ERROR}")
class ReadStatusTests(unittest.TestCase):
    def test_probes_dac_format_only_when_chip_released(self):
        ctrl = fake_ctrl(RUNNING, 0x01)
        regs, fmt = read_status(ctrl)
        self.assertEqual((regs[0], len(regs), fmt), (RUNNING, 16, 0x01))
        ctrl.dac_read.assert_called_once_with(ds.FORMAT_REG)

        ctrl = fake_ctrl(0x00)
        regs, fmt = read_status(ctrl)
        self.assertIsNone(fmt)
        ctrl.dac_read.assert_not_called()       # SPI is dead in reset: don't ask

    def test_lost_probe_does_not_fail_the_poll(self):
        ctrl = fake_ctrl(RUNNING)
        ctrl.dac_read.side_effect = iza_ctrl.CtrlError("no response")
        regs, fmt = read_status(ctrl)
        self.assertEqual((regs[0], fmt), (RUNNING, None))
        self.assertFalse(ctrl.quiet)

    def test_register_read_retried_once(self):
        ctrl = fake_ctrl(RUNNING)
        calls = {"n": 0}

        def flaky(i):
            calls["n"] += 1
            if calls["n"] == 1:
                raise iza_ctrl.CtrlError("lost")
            return RUNNING if i == 0 else 0
        ctrl.reg_read.side_effect = flaky
        regs, _ = read_status(ctrl)
        self.assertEqual(regs[0], RUNNING)


@unittest.skipIf(_QT_ERROR is not None, f"Qt unavailable: {_QT_ERROR}")
class StaleResultTests(unittest.TestCase):
    def setUp(self):
        self.c = ControlClient()
        self.seen = []
        self.c.status.connect(lambda r: self.seen.append(("status", r[0])))
        self.c.dac_format.connect(lambda f: self.seen.append(("fmt", f)))
        self.c.result.connect(lambda l, v: self.seen.append(("result", l)))
        self.c.error.connect(lambda l, m: self.seen.append(("error", l)))

    def test_current_status_emits_status_then_format(self):
        self.c._pending = 1
        self.c._on_done("__status__", self.c._gen, ({0: RUNNING}, 0x01))
        self.assertEqual(self.seen, [("status", RUNNING), ("fmt", 0x01)])
        self.assertEqual(self.c._pending, 0)

    def test_results_from_a_closed_connection_are_dropped(self):
        old = self.c._gen
        self.c.disconnect_board()               # bumps the generation
        self.c._pending = 3
        self.c._on_done("__status__", old, ({0: 0}, None))
        self.c._on_done("reset", old, 0)
        self.c._on_failed("dac-init", old, "no response")
        self.assertEqual(self.seen, [])
        self.assertEqual(self.c._pending, 0)    # still accounted for


@unittest.skipIf(_QT_ERROR is not None, f"Qt unavailable: {_QT_ERROR}")
class WarningWiringTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow()                   # offscreen, never shown or closed
        self.cp, self.cl = self.w.control, self.w.client
        self.logs = []
        self.cl.log.connect(lambda k, t: self.logs.append((k, t)))

    def tearDown(self):
        self.w.deleteLater()

    def connect(self):
        """What connect_board does, minus the network."""
        self.cl.ctrl = mock.Mock()
        self.cl._gen += 1
        self.cl.connected.emit(True)

    def poll(self, r0, fmt):
        regs = {i: 0 for i in range(16)}
        regs[0] = r0
        self.cl._on_done("__status__", self.cl._gen, (regs, fmt))

    def shown(self):
        # isVisibleTo: would it show? (isVisible() is always False here
        # because the window itself is never shown)
        return (self.cp.dac_lbl.text(), self.w.dac_warn.isVisibleTo(self.w),
                self.w.dac_warn.text())

    def test_stop_start_init_cycle(self):
        self.connect()
        self.poll(RUNNING, 0x01)
        self.assertEqual(self.shown(), ("DAC initialized", False, ""))

        self.cl.result.emit("reset", 0)          # ⏹ Stop / Reset
        lbl, vis, sb = self.shown()
        self.assertIn("held in reset", lbl)
        self.assertEqual((vis, sb), (True, "⚠ DAC in reset: ▶ Start, then ① Initialize"))

        self.poll(RUNNING, 0x00)                 # ▶ Start, DAC at defaults
        self.assertEqual(self.shown()[1:], (True, "⚠ DAC needs ① Initialize"))
        self.assertIn("lost its setup", self.shown()[0])

        self.cl.result.emit("dac-init", GOOD_INIT)
        self.assertEqual(self.shown(), ("DAC initialized", False, ""))
        warns = [t for k, t in self.logs if k == "warn"]
        self.assertEqual(warns, [ds.HELD, ds.LOST])
        self.assertIn(("ok", "DAC initialized — warning cleared"), self.logs)

    def test_repeated_polls_do_not_spam_the_log(self):
        self.connect()
        for _ in range(5):
            self.poll(RUNNING, 0x00)
        self.assertEqual([t for k, t in self.logs if k == "warn"], [ds.LOST])

    def test_initialize_before_connect_is_not_latched(self):
        self.cp._init_converters()               # clicked while disconnected
        self.connect()
        self.poll(RUNNING, 0x01)
        self.assertEqual(self.shown(), ("DAC initialized", False, ""))

    def test_init_refused_while_held_keeps_start_advice(self):
        self.connect()
        self.poll(0x00, None)
        self.cl.error.emit("dac-init", HELD_MSG)
        self.assertEqual(self.w.dac_warn.text(),
                         "⚠ DAC in reset: ▶ Start, then ① Initialize")

    def test_link_down_greys_ok_indicator(self):
        self.connect()
        self.poll(RUNNING, 0x01)
        self.w._on_status({})
        self.w._on_status({})                    # two misses = link down
        self.assertEqual(self.shown(),
                         ("DAC setup: unknown (no control link)", False, ""))

    def test_disconnect_forgets_and_hides_the_warning(self):
        self.connect()
        self.poll(RUNNING, 0x00)
        self.cl.disconnect_board()
        self.assertEqual(self.shown(), ("DAC setup: not checked yet", False, ""))

    def test_tone_boxes_span_0_to_50_mhz(self):
        for box in self.cp.freq_spin:
            self.assertEqual((box.minimum(), box.maximum(), box.singleStep()),
                             (0, 50e6, 12500))
        box = self.cp.freq_spin[0]
        box.setValue(50e6)
        self.assertEqual(box.text(), "50 MHz")

    def test_snapped_readout_switches_to_mhz(self):
        self.assertEqual(_fmt_actual(987500), "→ 987.5 kHz")
        self.assertEqual(_fmt_actual(1e6), "→ 1.0000 MHz")
        self.assertEqual(_fmt_actual(1012500), "→ 1.0125 MHz")

    def test_rec_rate_never_raises(self):
        for text in ("1e-310", "5e-324", "1e9999999", "0"):
            with self.subTest(text=text):
                self.w.cmb_recrate.setEditText(text)
                decim, _actual, _capped = self.w._recrate_decim()
                self.assertTrue(1 <= decim <= 1_000_000)


class FakeBoard:
    """Answers IzaCtrl._xact like a running, initialized board. Clearing
    `gate` holds every transaction until it is set again."""

    def __init__(self):
        self.regs = [0] * 16
        self.regs[0] = RUNNING
        self.gate = threading.Event()
        self.gate.set()

    def xact(self, op, target=0, reg=0, value=0, data=b""):
        self.gate.wait(5)
        if op == iza_ctrl.OP_REG_READ:
            return self.regs[reg], b""
        if op == iza_ctrl.OP_SPI_XFER:
            d = bytes(data)
            if target == iza_ctrl.SPI_DAC and d[0] & 0x80:    # DAC register read
                return 0, bytes([0, 0x01 if (d[0] & 0x7F) == ds.FORMAT_REG else 0])
            return 0, b"\x00" * len(d)
        return 0, b""


@unittest.skipIf(_QT_ERROR is not None, f"Qt unavailable: {_QT_ERROR}")
class RealWorkerTests(unittest.TestCase):
    """The production path end to end: connect_board, the worker thread, the
    connection generation stamped by submit/_poll_status, and _on_done."""

    def setUp(self):
        self.board = FakeBoard()
        self.ctrls = []                 # to close their (unused) UDP sockets
        real_ctrl = cc.VerifyingCtrl

        def make_ctrl(*a, **k):
            self.ctrls.append(real_ctrl(*a, **k))
            return self.ctrls[-1]
        for p in (mock.patch.object(iza_ctrl.IzaCtrl, "_xact",
                                    lambda s, *a, **k: self.board.xact(*a, **k)),
                  mock.patch.object(cc.ControlClient, "_start_events", lambda s: None),
                  mock.patch.object(cc, "VerifyingCtrl", make_ctrl)):
            p.start()
            self.addCleanup(p.stop)
        self.w = MainWindow()
        self.w.data.start = lambda *a: None
        self.w.data.stop = lambda *a: None
        self.cl = self.w.client

    def tearDown(self):
        self.board.gate.set()
        self.cl._poll.stop()
        self.cl.ctrl = None
        self.pump()
        for c in self.ctrls:
            c.sock.close()
        self.w.deleteLater()

    def pump(self):
        for _ in range(200):
            self.cl._pool.waitForDone(50)
            _APP.processEvents()
            if self.cl._pending == 0 and self.cl._pool.activeThreadCount() == 0:
                _APP.processEvents()
                return

    def test_connect_and_poll_reach_the_panel(self):
        got = []
        self.cl.result.connect(lambda label, v: got.append(label))
        self.w.ip_edit.setText("10.0.0.1")
        self.w._connect()
        self.cl._poll.stop()
        self.assertTrue(self.w.btn_disc.isEnabled())   # connected(True) was emitted
        self.pump()                    # Registers tab's initial read; first poll skipped
        self.assertTrue(any(label.startswith("__regall__") for label in got), got)
        self.cl._poll_status()
        self.pump()
        self.assertEqual(self.w.control.run_state.text(), "RUNNING")
        self.assertEqual(self.w.control.dac_lbl.text(), "DAC initialized")

    def test_result_in_flight_at_disconnect_is_dropped(self):
        self.cl.connect_board("10.0.0.1")
        self.cl._poll.stop()
        self.pump()
        seen = []
        self.cl.status.connect(lambda r: seen.append("status"))
        self.cl.result.connect(lambda label, v: seen.append(label))
        self.cl.submit("fast", lambda c: c.reg_read(0))
        self.pump()
        self.assertEqual(seen, ["fast"])               # current connection: delivered
        seen.clear()
        self.board.gate.clear()
        self.cl.submit("slow", lambda c: c.reg_read(0))
        self.cl.disconnect_board()
        self.board.gate.set()
        self.pump()
        self.assertEqual(seen, [])
        self.assertEqual(self.cl._pending, 0)


if __name__ == "__main__":
    unittest.main()
