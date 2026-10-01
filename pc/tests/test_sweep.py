"""Run from pc/: python -B -m unittest discover -s tests -v (NumPy only).

iza_sweep against a simulated board (register file + DAC 0x03) and a simulated
data stream on a virtual clock: records queued before a drain() and records
from before a tone change has settled come out at the old value, so removing
the drain or the settle sleep gives wrong results. The plant model covers ADC
clipping, an optional pre-ADC compression, drift and an uninitialized ADC.
UdpSource is tested with real datagrams over localhost."""

import math
import os
import socket
import struct
import tempfile
import time
import unittest
from unittest import mock

import numpy as np

import iza_ctrl
import iza_packet as izp
import iza_sweep as sw

RUNNING = iza_ctrl.SYS_RUN
TICKS = 1000                                  # R = 1000 -> 200 kHz records
RATE = izp.PL_CLK_HZ / TICKS
LOG = dict(log=lambda *a, **k: None)
USER_CH_EN, USER_PKT = 0x011, 0x15A           # a user setup the sweep must restore


class FakeBoard:
    def __init__(self, dac_fmt=0x01, r0=RUNNING):
        self.regs = [0] * 16
        self.regs[0] = r0
        self.regs[iza_ctrl.R_CH_EN] = USER_CH_EN
        self.regs[iza_ctrl.R_PKT_CFG] = USER_PKT
        for c in range(4):
            self.regs[iza_ctrl.R_CH_FA[c]] = (0x8000 << 16) | 40   # 100 % at 500 kHz
        self.dac_fmt = dac_fmt
        self.on_write = []                     # callbacks(reg, old, new)
        self.fail = None                       # fn(op, reg, value) -> raise or not

    def xact(self, op, target=0, reg=0, value=0, data=b""):
        if self.fail:
            self.fail(op, reg, value)
        if op == iza_ctrl.OP_REG_READ:
            return self.regs[reg], b""
        if op == iza_ctrl.OP_REG_WRITE:
            old = self.regs[reg]
            self.regs[reg] = value & 0xFFFFFFFF
            for cb in self.on_write:
                cb(reg, old, self.regs[reg])
            return 0, b""
        if op == iza_ctrl.OP_SPI_XFER:
            d = bytes(data)
            if target == iza_ctrl.SPI_DAC and d[0] & 0x80:
                return 0, bytes([0, self.dac_fmt if (d[0] & 0x7F) == 0x03 else 0])
            return 0, b"\x00" * len(d)
        return 0, b""


class FakeSource:
    """What the board would stream, on a virtual clock (sleep() advances it).

    plant(f) -> complex demod output per unit DAC amplitude. The raw-ADC peak
    is k_adc * |demod| (fraction of full scale): above 1 the ADC clips, the
    over-range flag is set on clipped samples and the demod output saturates.
    compress_above: the demod gain drops for amplitudes above it (a pre-ADC
    compression the ADC monitor cannot see). settle_needed: after a tone
    change, records keep the old value for this long. ramp: relative drift
    across every window; ramp_below: only for amplitude codes below it.
    offset_binary: the ADC reads as an uninitialized (offset-binary) part."""

    def __init__(self, board, plant, k_adc=40.0, noise=2e-5, compress_above=None,
                 theta0=0.3, settle_needed=0.05, ramp=0.0, ramp_below=None,
                 offset_binary=False, fail_after=None, fail_exc=None):
        self.b, self.plant, self.k_adc = board, plant, k_adc
        self.noise, self.compress_above, self.theta0 = noise, compress_above, theta0
        self.settle_needed, self.ramp, self.ramp_below = settle_needed, ramp, ramp_below
        self.offset_binary = offset_binary
        self.fail_after, self.fail_exc = fail_after, fail_exc
        self.rng = np.random.default_rng(1)
        self.clock = 0.0
        self.t_drain = -1e9
        self.change = {}                       # ch -> (time, old register value)
        self.collects = 0
        self.drops = 0
        board.on_write.append(self._written)

    def sleep(self, s):
        self.clock += s

    def _written(self, reg, old, new):
        if reg in iza_ctrl.R_CH_FA and new != old:
            self.change[iza_ctrl.R_CH_FA.index(reg)] = (self.clock, old)

    def drain(self):
        self.t_drain = self.clock

    def close(self):
        pass

    def _demod(self, fa, ch_en, ch):
        fcw, a = fa & 0x3FFF, ((fa >> 16) & 0xFFFF) / sw.UNITY
        if not ch_en & (1 << ch):
            a = 0.0
        f = fcw * sw.RASTER
        d = a * self.plant(f)
        if self.compress_above and a > self.compress_above:
            d *= self.compress_above / a
        return f, d, self.k_adc * abs(d), (fa >> 16) & 0xFFFF

    def collect(self, seconds, mask):
        self.collects += 1
        if self.fail_after is not None and self.collects > self.fail_after:
            raise self.fail_exc
        ch_en = self.b.regs[iza_ctrl.R_CH_EN]
        live = ((ch_en >> 4) & 0xF) | (0x10 if ch_en & 0x100 else 0)
        n = min(int(seconds * RATE), 4000) if live == mask else 0
        k = np.arange(n)
        out = dict(n=n, ts=(k * TICKS).astype(np.uint64), orf=np.zeros(n, np.uint8), sig={}, phase={},
                   adc=np.zeros(n, np.int32))
        adc_wave = np.zeros(n)
        for c in [i for i in range(4) if mask & (1 << i)]:
            fa = self.b.regs[iza_ctrl.R_CH_FA[c]]
            f, d, amp_adc, code = self._demod(fa, ch_en, c)
            t = k / RATE
            adc_wave += amp_adc * np.cos(2 * math.pi * f * t + self.theta0 + np.angle(d))
            if amp_adc > 1:
                d /= amp_adc                # ADC clipping saturates the fundamental
            z = np.full(n, d, complex)
            ramp = self.ramp if (self.ramp_below is None or code < self.ramp_below) else 0
            z *= 1 + ramp * np.linspace(-1, 1, n)
            # old values: still queued (no drain since the change) or not settled
            t_chg, old = self.change.get(c, (-1e9, fa))
            old_time = 0.0
            if self.t_drain < t_chg:
                old_time += min(self.clock - self.t_drain, 0.05)
            old_time += max(0.0, t_chg + self.settle_needed - self.clock)
            n_old = min(n, int(round(n * old_time / seconds)))
            if n_old:
                z[:n_old] = self._demod(old, ch_en, c)[1]
            z = z + self.noise * (self.rng.standard_normal(n)
                                  + 1j * self.rng.standard_normal(n))
            out["sig"][c] = np.round(np.abs(z) * sw.MAG_SCALE).astype(np.int32)
            out["phase"][c] = np.round(np.angle(z) * sw.PHASE_SCALE).astype(np.int32)
        self.clock += seconds
        out["orf"] = np.where(np.abs(adc_wave) >= 1, 3, 0).astype(np.uint8)
        adc = np.clip(np.round(adc_wave * 32767), -32768, 32767).astype(np.int64)
        adc += self.rng.integers(-3, 4, n)               # a few LSB of noise
        if self.offset_binary:          # pins carry x + 32768; read as int16
            code = (adc + 32768) & 0xFFFF
            adc = np.where(code >= 32768, code - 65536, code)
        out["adc"] = np.clip(adc, -32768, 32767).astype(np.int32)
        return out


def delay_plant(mag=0.05, tau=150e-9):
    return lambda f: mag * np.exp(-2j * math.pi * f * tau)


def cap_plant(c=1e-8, tau=120e-9):           # capacitive coupling: rises with f
    return lambda f: 2j * math.pi * f * c * np.exp(-2j * math.pi * f * tau)


def rel_err(row, plant):
    h = plant(row["freq_hz"])
    return abs((row["re"] + 1j * row["im"]) - h) / abs(h)


class SweepHarness(unittest.TestCase):
    def setUp(self):
        self.board = FakeBoard()
        for p in (mock.patch.object(iza_ctrl.IzaCtrl, "_xact",
                                    lambda s, *a, **k: self.board.xact(*a, **k)),
                  mock.patch.object(iza_ctrl.IzaCtrl, "trig_off")):
            self.trig_off = p.start()
            self.addCleanup(p.stop)
        self.ctrl = iza_ctrl.IzaCtrl("127.0.0.1")
        self.addCleanup(self.ctrl.sock.close)
        self.saved = list(self.board.regs)

    def source(self, plant, **kw):
        self.src = FakeSource(self.board, plant, **kw)
        return self.src

    def sweep(self, plant, **kw):
        src_keys = ("k_adc", "noise", "compress_above", "theta0", "settle_needed",
                    "ramp", "ramp_below", "offset_binary", "fail_after", "fail_exc")
        src = self.source(plant, **{k: kw.pop(k) for k in list(kw) if k in src_keys})
        cfg = sw.Config(**{"points": 12, **kw})
        return sw.run_sweep(self.ctrl, src, cfg, sleep=src.sleep, **LOG)

    def assert_restored(self):
        self.assertEqual(self.board.regs, self.saved)


class FrequencyPlanTests(unittest.TestCase):
    def test_coverage(self):
        self.assertEqual(sw.coverage(2000, TICKS), 1)     # 25 MHz: same point every record
        self.assertEqual(sw.coverage(1200, TICKS), 1)     # 15 MHz
        self.assertEqual(sw.coverage(40, TICKS), 2)       # 500 kHz: two points
        self.assertEqual(sw.coverage(2001, TICKS), 16)
        self.assertEqual(sw.max_coverage(1000), 16)
        self.assertEqual(sw.max_coverage(2000), 8)
        self.assertEqual(sw.max_coverage(8000), 2)

    def test_plan_is_log_spaced_covered_and_inside_the_range(self):
        for start, stop, n in ((500e3, 40e6, 40), (400e3, 40e6, 40), (39.8e6, 40e6, 5),
                               (1e6, 10e6, 25)):
            with self.subTest(start=start, stop=stop):
                notes = []
                fcws = sw.plan_frequencies(start, stop, n, TICKS, notes=notes)
                f = np.array(fcws) * sw.RASTER
                self.assertEqual(len(fcws), n)
                self.assertEqual(fcws, sorted(set(fcws)))
                self.assertTrue(all(sw.coverage(k, TICKS) == 16 for k in fcws))
                self.assertTrue(np.all((f >= start) & (f <= stop)), f)
                self.assertTrue(all(k >= sw.FCW_HPF for k in fcws))
                self.assertEqual(notes, [])
        targets = np.geomspace(500e3, 40e6, 40) / sw.RASTER
        fcws = sw.plan_frequencies(500e3, 40e6, 40, TICKS)
        self.assertTrue(np.all(np.abs(np.array(fcws) - targets) <= 1.5))

    def test_a_point_with_no_covered_grid_inside_moves_with_a_note(self):
        notes = []
        fcws = sw.plan_frequencies(25e6, 25e6, 1, TICKS, notes=notes)
        self.assertNotEqual(fcws, [2000])
        self.assertIn(abs(fcws[0] - 2000), (1,))
        self.assertEqual(len(notes), 1)
        notes = []                             # 5 points, 2 covered grid points
        fcws = sw.plan_frequencies(39.95e6, 40e6, 5, TICKS, notes=notes)
        self.assertEqual((len(fcws), len(notes)), (5, 3))

    def test_fallback_stays_above_the_high_pass(self):
        notes = []
        self.assertEqual(sw.plan_frequencies(400e3, 400e3, 1, TICKS, notes=notes), [33])
        self.assertEqual(len(notes), 1)

    def test_too_many_points_is_refused_quickly(self):
        t0 = time.perf_counter()
        with self.assertRaises(sw.SweepError):
            sw.plan_frequencies(500e3, 40e6, 2001, TICKS)
        self.assertLess(time.perf_counter() - t0, 0.5)
        self.assertEqual(len(sw.plan_frequencies(500e3, 40e6, 2000, TICKS)), 2000)

    def test_plan_adapts_to_slower_record_rates_and_limits(self):
        fcws = sw.plan_frequencies(1e6, 10e6, 10, 2000)
        self.assertTrue(all(sw.coverage(k, 2000) == 8 for k in fcws))
        for bad in ((1e6, 60e6, 10), (1e6, 2e6, 0), (2e6, 1e6, 3), (float("nan"), 1e6, 3)):
            with self.subTest(bad=bad), self.assertRaises(sw.SweepError):
                sw.plan_frequencies(*bad, TICKS)

    def test_why_coverage_matters(self):
        """At 25 MHz (fcw 2000) every record samples the same point of the
        cycle: with that point at a zero crossing a clipping tone reads as
        silent. One grid step away the snapshot walks the whole cycle."""
        board = FakeBoard()
        board.regs[iza_ctrl.R_CH_EN] = 0x111
        src = FakeSource(board, delay_plant(0.5, 0), k_adc=40, theta0=math.pi / 2)
        for fcw, blind in ((2000, True), (2001, False)):
            board.regs[iza_ctrl.R_CH_FA[0]] = (0x8000 << 16) | fcw
            src.t_drain = src.clock = src.clock + 1
            peak, _ = sw.adc_stats(src.collect(0.02, 0x11))
            self.assertLess(peak, 0.01) if blind else self.assertGreater(peak, 0.95)


class ConfigTests(unittest.TestCase):
    def test_bad_arguments_are_refused_before_the_board(self):
        for kw in (dict(start=2e6, stop=1e6), dict(points=0), dict(stop=60e6),
                   dict(settle=-1), dict(settle=float("nan")), dict(avg=0),
                   dict(amp_pct=150), dict(ch=4), dict(max_peak=1.2), dict(lin_tol=0)):
            with self.subTest(kw=kw), self.assertRaises(sw.SweepError):
                sw.Config(**kw)


class SweepTests(SweepHarness):
    def test_linear_plant_measured_exactly_and_board_restored(self):
        rows, meta = self.sweep(delay_plant(0.05), k_adc=40)
        self.assertEqual(meta["record_ticks"], TICKS)
        self.assertNotIn("aborted", meta)
        for r in rows:
            self.assertEqual(r["flags"], "")
            self.assertAlmostEqual(r["amp_pct"], 5.0, places=2)
            self.assertLess(rel_err(r, delay_plant(0.05)), 0.005)
            self.assertLessEqual(r["adc_peak"], 0.5)
            self.assertLess(r["lin_err_pct"], 1.0)
        self.trig_off.assert_called_once()
        self.assert_restored()

    def test_drain_and_settle_are_both_needed(self):
        """Without the drain, queued old-frequency records leak into each
        point; without the settle, the window starts before the change has
        settled. Either way the result is wrong, so each step matters."""
        with mock.patch.object(FakeSource, "drain", lambda self: None):
            rows, _ = self.sweep(delay_plant(0.05), linearity=False, points=6)
        self.assertGreater(max(rel_err(r, delay_plant(0.05)) for r in rows[1:]), 0.05)
        # the default 0.1 s settle covers a 0.08 s settling time: one window per
        # point (plus the start-up probe), no re-measurements
        rows, _ = self.sweep(delay_plant(0.05), linearity=False, points=6,
                             settle_needed=0.08)
        self.assertEqual(self.src.collects, 1 + 6)
        self.assertTrue(all(rel_err(r, delay_plant(0.05)) < 0.005 for r in rows))

    def test_slow_settling_is_detected_and_waited_out(self):
        rows, _ = self.sweep(delay_plant(0.05), k_adc=40, settle_needed=0.15,
                             linearity=False)
        for r in rows:
            self.assertNotIn("unsettled", r["flags"])
            self.assertLess(rel_err(r, delay_plant(0.05)), 0.005)

    def test_signal_that_never_settles_is_flagged(self):
        rows, _ = self.sweep(delay_plant(0.05), k_adc=40, ramp=0.05, points=3,
                             linearity=False)
        self.assertTrue(all("unsettled" in r["flags"] for r in rows))

    def test_amplitude_lowered_where_the_signal_would_clip(self):
        plant = cap_plant()
        rows, _ = self.sweep(plant, k_adc=40)
        self.assertTrue(any(r["amp_pct"] < 5.0 for r in rows))
        self.assertLess(rows[0]["amp_pct"] - 5.0, 1e-9)
        for r in rows:
            self.assertEqual(r["flags"], "")
            self.assertLessEqual(r["adc_peak"], 0.5)
            self.assertEqual(r["or_frac"], 0)
            self.assertLess(rel_err(r, plant), 0.01)
        self.assert_restored()

    def test_headroom_search_reaches_the_amplitude_it_reports(self):
        # needs ~9 halvings from 100 %: the search must not stop early and
        # then normalize by an amplitude it never measured
        plant = delay_plant(0.95 * 128 / 40)
        rows, _ = self.sweep(plant, k_adc=40, amp_pct=100, max_peak=0.9, points=3)
        for r in rows:
            self.assertNotIn("headroom", r["flags"])
            self.assertLess(r["amp_pct"], 1.0)
            self.assertLess(rel_err(r, plant), 0.01)

    def test_headroom_flag_when_even_the_minimum_amplitude_clips(self):
        # at the 0.25 % minimum the ADC peak is 40 * 0.0025 * 10 = 1.0 FS
        rows, _ = self.sweep(delay_plant(10.0), k_adc=40, points=3)
        self.assertTrue(all("headroom" in r["flags"] for r in rows))
        self.assertTrue(all(abs(r["amp_pct"] - 0.25) < 0.01 for r in rows))

    def test_hidden_compression_is_caught_by_the_linearity_check(self):
        rows, _ = self.sweep(delay_plant(0.05), k_adc=5, compress_above=0.03)
        self.assertTrue(all("nonlinear" in r["flags"] for r in rows))
        rows, _ = self.sweep(delay_plant(0.05), k_adc=5, compress_above=0.03,
                             linearity=False)
        self.assertTrue(all("nonlinear" not in r["flags"] for r in rows))

    def test_unsettled_half_amplitude_window_gives_no_linearity_verdict(self):
        half_code = sw.Config.code(5.0) // 2 + 1
        rows, _ = self.sweep(delay_plant(0.05), ramp=0.05, ramp_below=half_code,
                             points=3)
        for r in rows:
            self.assertIn("unsettled", r["flags"])
            self.assertNotIn("nonlinear", r["flags"])
            self.assertTrue(math.isnan(r["lin_err_pct"]))

    def test_out_of_band_points_are_flagged(self):
        rows, _ = self.sweep(delay_plant(0.01), start=300e3, stop=45e6, points=4,
                             linearity=False)
        self.assertIn("below-hpf", rows[0]["flags"])
        self.assertIn("dac-filter", rows[-1]["flags"])


class SafetyTests(SweepHarness):
    def expect_refusal(self, words, dac_fmt=None, r0=None, **src):
        if dac_fmt is not None:
            self.board.dac_fmt = dac_fmt
        if r0 is not None:
            self.board.regs[0] = r0
        self.saved = list(self.board.regs)
        with self.assertRaises(sw.SweepError) as cm:
            self.sweep(delay_plant(), **src)
        self.assertIn(words, str(cm.exception))
        self.assert_restored()

    def test_refuses_uninitialized_dac(self):
        self.expect_refusal("not initialized", dac_fmt=0x00)

    def test_refuses_dac_in_reset(self):
        self.expect_refusal("held in reset", r0=0x00)

    def test_refuses_stopped(self):
        self.expect_refusal("stopped", r0=RUNNING & ~(1 << iza_ctrl.B_RUN))

    def test_refuses_loopback(self):
        self.expect_refusal("loopback", r0=RUNNING | (1 << iza_ctrl.B_ADC_SEL))

    def test_refuses_test_signal(self):
        self.expect_refusal("test/replay", r0=RUNNING | (1 << iza_ctrl.B_DAC_TESTSIG))

    def test_refuses_uninitialized_adc(self):
        self.expect_refusal("ADC looks uninitialized", offset_binary=True)

    def test_tone_is_quiet_before_it_is_switched_on_and_after_restore(self):
        """Even with the user's tone register at 100 % and its TX bit off, the
        swept channel never outputs more than the sweep amplitude: not during
        setup, and not while the restore puts things back."""
        self.board.regs[iza_ctrl.R_CH_EN] = 0x010          # ch0 measured, not driven
        self.saved = list(self.board.regs)
        limit = sw.Config.code(5.0)
        loud = []           # (assertions raised in here would be swallowed)

        def watch(reg, old, new):
            r = self.board.regs
            if r[iza_ctrl.R_CH_EN] & 1 and (r[iza_ctrl.R_CH_FA[0]] >> 16) > limit:
                loud.append((reg, hex(new)))
        self.board.on_write.append(watch)
        self.sweep(delay_plant(), points=2, linearity=False)
        self.assertEqual(loud, [])
        self.assert_restored()

    def test_lost_control_datagrams_are_retried(self):
        # call 1: preflight's DAC read; calls 9 and 10: back to back inside a point
        lost = {1, 9, 10}
        calls = iter(range(10_000))
        drops = (i in lost for i in calls)

        def flaky(op, reg, value):
            if next(drops):
                raise iza_ctrl.CtrlError("no response from board (is iza_replay running?)")
        self.board.fail = flaky
        rows, meta = self.sweep(delay_plant(), points=6)
        self.assertEqual(len(rows), 6)
        self.assertNotIn("aborted", meta)
        self.assert_restored()

    def test_error_mid_sweep_keeps_the_points_and_restores(self):
        rows, meta = self.sweep(delay_plant(), points=10, fail_after=8,
                                fail_exc=iza_ctrl.CtrlError("no response from board"))
        self.assertTrue(0 < len(rows) < 10)
        self.assertIn("no response", meta["aborted"])
        self.assert_restored()

    def test_ctrl_c_keeps_the_points_and_restores(self):
        rows, meta = self.sweep(delay_plant(), points=10, fail_after=9,
                                fail_exc=KeyboardInterrupt())
        self.assertTrue(0 < len(rows) < 10)
        self.assertEqual(meta["aborted"], "interrupted")
        self.assert_restored()

    def test_error_before_any_point_is_raised_and_restores(self):
        with self.assertRaises(RuntimeError):
            self.sweep(delay_plant(), points=5, fail_after=1, fail_exc=RuntimeError("x"))
        self.assert_restored()

    def mask_restore_fails(self, user_mask):
        self.board.regs[iza_ctrl.R_CH_EN] = user_mask
        self.saved = list(self.board.regs)

        def fail(op, reg, value):
            if op == iza_ctrl.OP_REG_WRITE and reg == iza_ctrl.R_CH_EN and value == user_mask:
                raise iza_ctrl.CtrlError("no response from board")
        self.board.fail = fail
        logs = []
        src = self.source(delay_plant())
        _, meta = sw.run_sweep(self.ctrl, src, sw.Config(points=2, linearity=False),
                               sleep=src.sleep, log=logs.append)
        self.assertEqual(meta.get("restore_failed"), 1)
        self.assertTrue(any("could not restore" in m for m in logs))
        self.assertEqual(self.board.regs[iza_ctrl.R_PKT_CFG], USER_PKT)

    def test_restore_keeps_going_past_a_failed_write(self):
        self.mask_restore_fails(USER_CH_EN)            # tone was on: restore it
        self.assertEqual(self.board.regs[iza_ctrl.R_CH_FA[0]], self.saved[iza_ctrl.R_CH_FA[0]])

    def test_tone_stays_quiet_if_the_mask_cannot_be_restored(self):
        self.mask_restore_fails(0x010)                 # tone was off: keep it quiet
        self.assertLessEqual(self.board.regs[iza_ctrl.R_CH_FA[0]] >> 16, sw.Config.code(5.0))

    def test_console_errors_cannot_skip_the_restore(self):
        def broken(msg):
            raise OSError(22, "Invalid argument")      # e.g. a closed pipe
        src = self.source(delay_plant())
        rows, meta = sw.run_sweep(self.ctrl, src, sw.Config(points=3, linearity=False),
                                  sleep=src.sleep, log=broken)
        self.assertEqual(len(rows), 3)
        self.assertNotIn("aborted", meta)
        self.assert_restored()

    def test_initialized_adc_is_not_refused_on_a_large_tone(self):
        # 1 MHz is a 200 kHz multiple (coverage 1) and 40 % is a big tone: the
        # format probe runs with the tone off, so neither matters
        rows, _ = self.sweep(delay_plant(0.05), k_adc=40, start=1e6, stop=2e6,
                             amp_pct=40, points=2, linearity=False)
        self.assertEqual(len(rows), 2)


class ControlLinkTests(unittest.TestCase):
    def test_unreachable_control_port_is_a_ctrlerror(self):
        """On Windows an ICMP port-unreachable arrives as ConnectionResetError;
        it must end in the usual CtrlError, not a raw socket error."""
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()                          # nothing listens there now
        c = iza_ctrl.IzaCtrl("127.0.0.1", port, timeout=0.2)
        try:
            with self.assertRaises(iza_ctrl.CtrlError):
                c.reg_read(0)
        finally:
            c.sock.close()


def pack_records(ts0, n, mask, adc_val=1234, sig=1000, phase=200, ts_step=TICKS):
    """Bytes the packetizer would send for n records (inverse of deinterleave)."""
    words = []
    for i in range(n):
        ts = ts0 + i * ts_step
        words += [ts & 0xFFFFFFFF, (ts >> 32) & 0x3FFFFFFF]
        for _ in izp.demod_list(mask):
            words += [sig & 0xFFFFFFFF, phase & 0xFFFFFFFF]
        if izp.adc_enabled(mask):
            words.append(adc_val & 0xFFFFFFFF)
    return struct.pack(f"<{len(words)}I", *words)


def datagram(seq, mask, payload, stride=None):
    stride = stride or izp.stride_words(mask)
    return struct.pack(izp.HDR_FMT, izp.MAGIC, seq, 0, mask, stride, 0,
                       len(payload), 0, 0) + payload


class UdpSourceTests(unittest.TestCase):
    def setUp(self):
        self.src = sw.UdpSource(0)
        self.addCleanup(self.src.close)
        self.port = self.src.sock.getsockname()[1]
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addCleanup(self.tx.close)

    def send(self, data):
        self.tx.sendto(data, ("127.0.0.1", self.port))

    def test_collect_filters_counts_gaps_and_drain_discards(self):
        self.send(datagram(1, 0x11, pack_records(0, 10, 0x11, adc_val=-1)))   # stale
        time.sleep(0.05)
        self.src.drain()
        self.send(datagram(10, 0x11, pack_records(1000, 10, 0x11)))           # good
        self.send(datagram(11, 0x01, pack_records(1000, 10, 0x01)))           # wrong mask
        misframed = pack_records(5000, 12, 0x01)                              # stride 4 ...
        self.send(datagram(12, 0x11, misframed[:len(misframed) // 20 * 20]))  # ...labeled 5
        self.send(datagram(16, 0x11, pack_records(9000, 10, 0x11) + b"junk")) # trailing bytes
        self.send(b"\x00" * 3000)                                             # oversized junk
        data = self.src.collect(0.3, 0x11)
        self.assertEqual(data["n"], 20)
        self.assertTrue(np.all(data["adc"] == 1234))                          # stale one gone
        self.assertEqual(self.src.drops, 4)        # 11 (other layout) and 13-15

    def test_bind_conflict_is_a_clear_error(self):
        with self.assertRaises(sw.SweepError) as cm:
            sw.UdpSource(self.port)
        self.assertIn("Close the GUI", str(cm.exception))


class AnalysisTests(unittest.TestCase):
    def rows(self, f, h, flags="", se=1e-4):
        return [dict(freq_hz=fi, re=hi.real, im=hi.imag, flags=flags, se=se)
                for fi, hi in zip(f, h)]

    def test_open_and_reference_deembedding(self):
        f = np.array([1e6, 2e6, 4e6])
        h_open = np.array([0.01 + 0.02j, 0.02 + 0.04j, 0.04 + 0.08j])
        h_ref = h_open + np.array([0.5, 0.5j, -0.5])
        d_true = np.array([0.2 - 0.1j, 1.5j, 0.3 + 0.3j])
        h_load = h_open + d_true * (h_ref - h_open)
        out = sw.deembed(self.rows(f, h_load), self.rows(f, h_open), self.rows(f, h_ref))
        got = np.array([r["d_re"] + 1j * r["d_im"] for r in out])
        np.testing.assert_allclose(got, d_true, atol=1e-12)
        self.assertTrue(all(r["flags"] == "" for r in out))
        self.assertTrue(all(0 < r["d_se"] < 1e-3 for r in out))
        only_open = sw.deembed(self.rows(f, h_load), self.rows(f, h_open))
        np.testing.assert_allclose([r["d_re"] + 1j * r["d_im"] for r in only_open],
                                   h_load - h_open, atol=1e-12)

    def test_open_and_reference_problems_are_carried_into_the_result(self):
        f = np.array([1e6, 2e6, 3e6])
        load = self.rows(f, [0.30 + 0.01j, 0.31, 0.32])
        opn = self.rows(f, [0.0, 0.0, 0.0])
        opn[0]["flags"] = "unsettled"
        ref = self.rows(f, [0.6, 0.4, 0.65])
        ref[1]["flags"] = "headroom;nonlinear"
        out = sw.deembed(load, opn, ref)
        self.assertEqual(out[0]["flags"], "open:unsettled")
        self.assertEqual(out[1]["flags"], "ref:headroom;ref:nonlinear")
        same = sw.deembed(self.rows(f, [0.3 + 1e-5, 0.3, 0.3], se=1e-5),
                          self.rows(f, [0.3, 0.3, 0.3], se=1e-5))
        self.assertTrue(all("low-snr" in r["flags"] for r in same))

    def test_only_measurement_problems_carry_over(self):
        f = np.array([1e6, 2e6])
        opn = self.rows(f, [1e-7, 1e-7])
        opn[0]["flags"] = "low-snr"                     # a clean fixture: noise only
        opn[1]["flags"] = "headroom;dac-filter"
        out = sw.deembed(self.rows(f, [0.3, 0.3]), opn)
        self.assertEqual([r["flags"] for r in out], ["", "open:headroom"])

    def test_plot_phase_unwraps_the_wide_high_end(self):
        f = np.array([k * sw.RASTER for k in sw.plan_frequencies(500e3, 40e6, 40, TICKS)])
        tau = 150e-9
        h = np.exp(-2j * math.pi * f * tau)
        ph = sw.plot_phase(f, h, sw.fit_delay(f, h), remove_delay=False)
        np.testing.assert_allclose(ph - ph[0], -360 * (f - f[0]) * tau, atol=1.0)

    def test_mismatched_grid_is_interpolated_and_flagged(self):
        with mock.patch("builtins.print"):
            out = sw.deembed(self.rows([1.5e6, 9e6], [1, 1]),
                             self.rows([1e6, 2e6], [0.1 + 0j, 0.2 + 0j]))
        self.assertIn("interp", out[0]["flags"])
        self.assertTrue(math.isnan(out[1]["d_re"]))         # outside the open sweep

    def test_csv_round_trip_utf8_and_atomic(self):
        row = dict(freq_hz=1012500.0, fcw=81, cover=16, amp_pct=5.0, re=0.1, im=-0.2,
                   mag=0.2236, phase_deg=-63.4, se=1e-5, adc_peak=0.12, or_frac=0.0,
                   n=40000, lin_err_pct=0.1, lin_phase_deg=0.02, flags="low-snr;interp",
                   d_re=1.0, d_im=2.0, d_mag=2.236, d_phase_deg=63.4, d_se=0.01)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.csv")
            sw.write_csv(p, [row], {"record_ticks": 1000, "open": "open_50Ω.csv"})
            rows, meta = sw.read_csv(p)
            self.assertEqual(meta, {"record_ticks": "1000", "open": "open_50Ω.csv"})
            for k, v in row.items():
                self.assertEqual(rows[0][k], v)
            with mock.patch("csv.DictWriter.writerow", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    sw.write_csv(p, [row])
            self.assertEqual(sw.read_csv(p)[0][0]["fcw"], 81)      # old file intact
            self.assertEqual([x for x in os.listdir(d) if x.endswith(".tmp")], [])
            # a target held open (viewer, OneDrive): rename fails, copy in place works
            row2 = dict(row, fcw=83)
            with mock.patch("os.replace", side_effect=PermissionError("in use")), \
                    mock.patch.object(sw.time, "sleep"):
                sw.write_csv(p, [row2])
            self.assertEqual(sw.read_csv(p)[0][0]["fcw"], 83)
            self.assertEqual([x for x in os.listdir(d) if x.endswith(".tmp")], [])

    def test_fit_delay_unwraps_a_wide_log_sweep(self):
        f = np.array([k * sw.RASTER for k in sw.plan_frequencies(500e3, 40e6, 40, TICKS)])
        for tau in (80e-9, 250e-9):
            h = 1j * np.exp(-2j * math.pi * f * tau)          # +90 deg offset, then delay
            self.assertAlmostEqual(sw.fit_delay(f, h), tau, delta=0.5e-9)

    def test_fit_delay_ignores_noisy_points_when_told(self):
        f = np.array([k * sw.RASTER for k in sw.plan_frequencies(500e3, 40e6, 40, TICKS)])
        h = (f / 40e6) * np.exp(-2j * math.pi * f * 200e-9)
        rng = np.random.default_rng(3)
        noisy = h + 0.02 * (rng.standard_normal(f.size) + 1j * rng.standard_normal(f.size))
        good = np.abs(h) > 3 * 0.02 * math.sqrt(2)
        self.assertAlmostEqual(sw.fit_delay(f, noisy, good), 200e-9, delta=3e-9)

    def test_phase_keeps_going_after_a_gap(self):
        f = np.linspace(1e6, 10e6, 10)
        h = np.exp(-2j * math.pi * f * 100e-9)
        h[3] = complex("nan")
        ph = sw.phase_deg(f, h)
        self.assertTrue(math.isnan(ph[3]))
        self.assertTrue(np.all(np.isfinite(ph[4:])))
        np.testing.assert_allclose(sw.phase_deg(f, h, 100e-9)[4:], 0, atol=1e-6)

    def test_analyze_cli_offline(self):
        f = np.array([1e6, 2e6, 4e6])
        with tempfile.TemporaryDirectory() as d:
            load, opn, out = (os.path.join(d, n) for n in ("load.csv", "open.csv", "o.csv"))
            sw.write_csv(load, self.rows(f, [1 + 1j, 2, 3j]))
            sw.write_csv(opn, self.rows(f, [0.5j, 0.1, 0]))
            with mock.patch("builtins.print"):
                rc = sw.main(["--analyze", load, "--open", opn, "--out", out, "--no-plot"])
            self.assertEqual(rc, 0)
            rows, meta = sw.read_csv(out)
        self.assertEqual(meta["open"], opn)
        np.testing.assert_allclose([r["d_re"] + 1j * r["d_im"] for r in rows],
                                   [1 + 0.5j, 1.9, 3j])

    def test_reanalysis_forgets_the_previous_deembedding(self):
        f = np.array([1e6, 2e6, 4e6])
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "data.v2")
            os.makedirs(folder)
            load = os.path.join(folder, "load")                 # no extension
            opn, ref = os.path.join(d, "open.csv"), os.path.join(d, "ref.csv")
            sw.write_csv(opn, self.rows(f, [0.1, 0.1, 0.1]))
            sw.write_csv(ref, self.rows(f, [2, 2, 2]))
            first = sw.deembed(self.rows(f, [1, 1, 1], flags="interp"),
                               self.rows(f, [0.1, 0.1, 0.1], flags="unsettled", se=1.0))
            self.assertTrue(all("low-snr" in r["flags"] for r in first))
            sw.write_csv(load, first, {"open": opn})
            with mock.patch("builtins.print"):
                self.assertEqual(sw.main(["--analyze", load, "--ref", ref]), 0)
                self.assertEqual(sw.main(["--analyze", load]), 1)   # needs --open/--ref
            out = os.path.join(folder, "load_deembedded.csv")
            self.assertTrue(os.path.exists(out))
            self.assertTrue(os.path.exists(os.path.join(folder, "load_deembedded.png")))
            rows, meta = sw.read_csv(out)
        self.assertNotIn("open", meta)
        np.testing.assert_allclose([r["d_re"] for r in rows], [0.5, 0.5, 0.5])
        self.assertTrue(all(r["flags"] == "" for r in rows))

    def test_bad_port_is_refused(self):
        for port in ("0", "70000", "-1"):
            with self.subTest(port=port), mock.patch("sys.stderr"), \
                    self.assertRaises(SystemExit):
                sw.main(["--port", port])
        with self.assertRaises(sw.SweepError):
            sw.UdpSource(70000)

    def test_bad_open_file_is_refused_before_the_board(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.csv")
            with open(bad, "w") as fh:
                fh.write("a,b\n1,2\n")
            with mock.patch.object(iza_ctrl, "IzaCtrl") as ctrl, \
                    mock.patch("builtins.print"):
                self.assertEqual(sw.main(["--open", bad, "--out", os.path.join(d, "x.csv")]), 1)
            ctrl.assert_not_called()

    def test_plot_is_written(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")
        f = np.array([k * sw.RASTER for k in sw.plan_frequencies(500e3, 40e6, 20, TICKS)])
        rows = self.rows(f, 0.05j * np.exp(-2j * math.pi * f * 150e-9))
        rows[3]["flags"] = "nonlinear"
        rows[5]["re"] = float("nan")
        with tempfile.TemporaryDirectory() as d:
            for kw in ({}, {"remove_delay": True}):
                p = os.path.join(d, "s.png")
                self.assertEqual(sw.plot(p, rows, **kw), p)
                self.assertGreater(os.path.getsize(p), 10_000)


class LiveCliTests(SweepHarness):
    """main() end to end on the simulated board: a sweep that fails part-way
    still writes its points (and exits 1)."""

    def run_main(self, *extra, **src_kw):
        src = self.source(delay_plant(), **src_kw)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "sub", "s.csv")               # folder created
            with mock.patch.object(sw, "UdpSource", lambda port: src), \
                    mock.patch.object(sw, "SLEEP", src.sleep), \
                    mock.patch("builtins.print"):
                rc = sw.main(["--points", "8", "--no-plot", "--out", out, *extra])
            rows, meta = sw.read_csv(out) if os.path.exists(out) else ([], {})
        return rc, rows, meta

    def test_full_sweep(self):
        rc, rows, meta = self.run_main()
        self.assertEqual((rc, len(rows)), (0, 8))
        self.assertEqual(meta["board"], sw.DEFAULT_BOARD)
        self.assert_restored()

    def test_unwritable_output_is_rescued_with_exit_code_2(self):
        real = sw.write_csv
        with tempfile.TemporaryDirectory() as rescue:
            def failing(path, rows, meta=None):
                if os.path.basename(path) == "s.csv":       # the requested --out
                    raise PermissionError("locked")
                real(path, rows, meta)
            with mock.patch.object(sw, "write_csv", failing), \
                    mock.patch.object(sw.tempfile, "gettempdir", return_value=rescue):
                rc, rows, _ = self.run_main()
            saved = [x for x in os.listdir(rescue) if x.startswith("sweep_rescued_")]
            self.assertEqual(rc, 2)
            self.assertEqual(rows, [])                   # --out was not written
            self.assertEqual(len(saved), 1)
            self.assertEqual(len(sw.read_csv(os.path.join(rescue, saved[0]))[0]), 8)

    def test_partial_sweep_is_saved(self):
        rc, rows, meta = self.run_main(
            fail_after=10, fail_exc=iza_ctrl.CtrlError("no response from board"))
        self.assertEqual(rc, 1)
        self.assertTrue(0 < len(rows) < 8)
        self.assertIn("no response", meta["aborted"])
        self.assert_restored()


if __name__ == "__main__":
    unittest.main()
