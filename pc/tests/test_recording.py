"""Run from pc/: python -B -m unittest discover -s tests -v (NumPy only)."""

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

import numpy as np

from iza_gui.recorder import ZiBinRecorder
from iza_gui.recording_values import (
    INVALID_INPUT, MAG_SCALE, OVER_RANGE, PHASE_SCALE, admittance_values,
)


def batch(start=0, n=8, mask=1):
    channels = [ch for ch in range(4) if mask & (1 << ch)]
    return {
        "chan_mask": mask,
        "ts": np.arange(start, start + n, dtype=np.uint64) * 1000,
        "sig": {ch: np.full(n, int(MAG_SCALE / (ch + 2)), dtype=np.int32)
                for ch in channels},
        "phase": {ch: np.full(n, int(PHASE_SCALE * 0.4 * ch), dtype=np.int32)
                  for ch in channels},
        "orf": np.zeros(n, dtype=np.uint8),
        "adc": np.arange(start, start + n, dtype=np.int32) if mask & 16 else None,
    }


class PausedRecorder(ZiBinRecorder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entered = threading.Event()
        self.release = threading.Event()

    def _write_batch(self, mask, b):
        self.entered.set()
        if not self.release.wait(3):
            raise TimeoutError("Test did not release the disk worker")
        super()._write_batch(mask, b)


class ValuesTests(unittest.TestCase):
    def test_admittance_scaling_all_quadrants(self):
        phase = np.linspace(-np.pi, np.pi, 1001)
        magnitude = np.geomspace(2e-6, 1.9, 1001)
        with np.errstate(all="raise"):
            x, y, flags = admittance_values(
                magnitude * MAG_SCALE, phase * PHASE_SCALE, 0)
        # Bit-identical to the legacy mag*cos / mag*sin scaling.
        np.testing.assert_array_equal(x, magnitude * np.cos(phase))
        np.testing.assert_array_equal(y, magnitude * np.sin(phase))
        self.assertFalse(flags.any())

    def test_nonfinite_negative_and_overrange_flags(self):
        sig = np.array([0, 1024, -1, np.nan, np.inf, 2048, 2048])
        phase = np.zeros(sig.size)
        phase[-2] = np.inf
        over = np.zeros(sig.size, dtype=np.uint8)
        over[-1] = 2
        with np.errstate(all="raise"):
            x, y, flags = admittance_values(sig, phase, over)
        expected = [0, 0] + [INVALID_INPUT] * 4 + [OVER_RANGE]
        np.testing.assert_array_equal(flags, expected)
        self.assertEqual(x[0], 0.0)  # zero magnitude is valid admittance data
        self.assertEqual(x[1], 1024 / MAG_SCALE)
        self.assertEqual(x[-1], 2048 / MAG_SCALE)  # flagged, not clamped or removed

    def test_combined_flags_and_recovery_without_latching(self):
        x, y, flags = admittance_values(
            np.array([-1, 2048, 2048, 2048]), np.zeros(4), np.array([1, 0, 1, 0]))
        np.testing.assert_array_equal(
            flags, [INVALID_INPUT | OVER_RANGE, 0, OVER_RANGE, 0])
        self.assertEqual(x[1], x[3])


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.recorders = []

    def tearDown(self):
        for r in self.recorders:
            if hasattr(r, "release"):
                r.release.set()
            r.stop(timeout=4)
        self.tmp.cleanup()

    def recorder(self, cls=ZiBinRecorder, **kwargs):
        r = cls(**kwargs)
        self.recorders.append(r)
        return r

    @staticmethod
    def read(path):
        return np.fromfile(path, dtype=">f8").reshape(-1, 7)

    @staticmethod
    def meta(r):
        return json.loads((Path(r.session_dir) / "meta.json").read_text())

    def test_legacy_rows_and_validity_alignment_across_batches(self):
        r = self.recorder()
        d = Path(r.start(self.tmp.name, {0: 500000., 1: 5000000.}, decim=3))
        first, second = batch(0, 5, 19), batch(5, 7, 19)
        first["orf"][3] = 1   # absolute index 3, selected by decimation
        second["orf"][4] = 1  # absolute index 9, selected by decimation
        r.on_batch(first)
        r.on_batch(second)
        r.stop()
        self.assertIsNone(r.error)
        for ch in (0, 1):
            original = self.read(d / f"Freq{ch + 1}.ziBin")
            validity = np.fromfile(d / f"Freq{ch + 1}.validity.bin", dtype="u1")
            raw_sig = np.r_[first["sig"][ch], second["sig"][ch]][::3]
            raw_phase = np.r_[first["phase"][ch], second["phase"][ch]][::3]
            # Exact original scaling and layout remain compatible.
            np.testing.assert_array_equal(original[:, 1], raw_sig / MAG_SCALE * np.cos(raw_phase / PHASE_SCALE))
            np.testing.assert_array_equal(original[:, 2], raw_sig / MAG_SCALE * np.sin(raw_phase / PHASE_SCALE))
            np.testing.assert_allclose(original[:, 0], np.arange(0, 12, 3) * 5e-6,
                                       rtol=0, atol=1e-20)
            # One validity byte per row; over-range rows are flagged, not altered.
            np.testing.assert_array_equal(validity, [0, OVER_RANGE, 0, OVER_RANGE])
        np.testing.assert_array_equal(np.fromfile(d / "adc_int16.bin", dtype="<i2"), [0, 3, 6, 9])
        meta = self.meta(r)
        self.assertEqual(meta["recording"]["state"], "complete")
        self.assertEqual(meta["recording"]["written_records"], 4)
        self.assertEqual(meta["channels"]["0"]["quantity"], "relative_differential_admittance")
        self.assertEqual(meta["channels"]["0"]["validity_file"], "Freq1.validity.bin")
        self.assertEqual(meta["channels"]["0"]["invalid_records"]["over_range"], 2)
        self.assertEqual(meta["validity"]["flags"]["adc_over_range"], OVER_RANGE)
        self.assertFalse((d / "relative_impedance").exists())

    def test_mask_changes_and_empty_decimated_batches(self):
        r = self.recorder()
        d = Path(r.start(self.tmp.name, decim=3))
        r.on_batch(batch(0, 1, 1))
        r.on_batch(batch(1, 1, 2))  # no selected row
        r.on_batch(batch(2, 5, 2))
        r.stop()
        self.assertIsNone(r.error)
        self.assertEqual(len(self.read(d / "Freq1.ziBin")), 1)
        self.assertEqual(len(self.read(d / "Freq2.ziBin")), 2)

    def test_producer_owns_snapshot_and_stop_is_nonblocking(self):
        r = self.recorder(PausedRecorder)
        d = Path(r.start(self.tmp.name))
        b = batch()
        r.on_batch(b)
        self.assertTrue(r.entered.wait(1))
        b["sig"][0][:] = 0
        r.stop(wait=False)  # returns while writer is deliberately blocked
        self.assertTrue(r.busy)
        with self.assertRaises(RuntimeError):
            r.start(self.tmp.name)
        with self.assertRaises(TimeoutError):
            r.stop(timeout=0.001)
        r.release.set()
        r.stop()
        self.assertTrue((self.read(d / "Freq1.ziBin")[:, 1] == 0.5).all())

    def test_queue_overflow_drains_accepted_data_and_reports_failure(self):
        r = self.recorder(PausedRecorder, max_queue_bytes=68)  # 4 * (8 + 4 + 4 + 1)
        d = Path(r.start(self.tmp.name))
        r.on_batch(batch(n=4))
        self.assertTrue(r.entered.wait(1))
        r.on_batch(batch(start=4, n=4))
        self.assertFalse(r.active)
        self.assertIn("queue full", r.error)
        r.release.set()
        r.stop()
        self.assertEqual(len(self.read(d / "Freq1.ziBin")), 4)
        meta = self.meta(r)["recording"]
        self.assertEqual(meta["state"], "failed")
        self.assertEqual(meta["rejected_records"], 4)
        self.assertEqual(meta["unwritten_records"], 0)
        self.assertEqual(r._queued_bytes, 0)

    def test_partial_disk_failure_rolls_back_whole_batch(self):
        r = self.recorder()
        append = r._append

        def fail_validity(path, array):
            if path.endswith("validity.bin"):
                r._file(path).write(b"partial row")
                raise OSError("disk full")
            append(path, array)

        with mock.patch.object(r, "_append", side_effect=fail_validity):
            d = Path(r.start(self.tmp.name))
            r.on_batch(batch())
            r.stop()
        self.assertIn("disk full", r.error)
        self.assertEqual((d / "Freq1.ziBin").stat().st_size, 0)
        self.assertEqual((d / "Freq1.validity.bin").stat().st_size, 0)
        self.assertEqual(self.meta(r)["recording"]["unwritten_records"], 8)
        self.assertEqual(self.meta(r)["recording"]["state"], "failed")

    def test_failure_keeps_previous_committed_rows(self):
        r = self.recorder()
        write = r._write_batch
        committed = threading.Event()
        calls = []

        def fail_second(mask, b):
            calls.append(1)
            if len(calls) == 1:
                write(mask, b)
                committed.set()
            else:
                append = r._append

                def partial(path, array):
                    if path.endswith("validity.bin"):
                        r._file(path).write(b"partial")
                        raise OSError("disk full on second batch")
                    append(path, array)

                with mock.patch.object(r, "_append", side_effect=partial):
                    write(mask, b)

        with mock.patch.object(r, "_write_batch", side_effect=fail_second):
            d = Path(r.start(self.tmp.name))
            r.on_batch(batch())
            self.assertTrue(committed.wait(1))
            r.on_batch(batch(start=8))
            r.stop()
        self.assertIn("second batch", r.error)
        self.assertEqual(len(self.read(d / "Freq1.ziBin")), 8)
        self.assertEqual((d / "Freq1.validity.bin").stat().st_size, 8)
        meta = self.meta(r)
        self.assertEqual(meta["channels"]["0"]["records"], 8)
        self.assertEqual(meta["recording"]["unwritten_records"], 8)

    def test_batch_count_limit_is_also_nonblocking(self):
        r = self.recorder(PausedRecorder)
        r.start(self.tmp.name)
        r._q.maxsize = 1
        r.on_batch(batch())
        self.assertTrue(r.entered.wait(1))
        r.on_batch(batch(start=8))
        r.on_batch(batch(start=16))
        self.assertIn("queue full", r.error)
        r.release.set()
        r.stop()
        meta = self.meta(r)["recording"]
        self.assertEqual(meta["written_records"], 16)
        self.assertEqual(meta["rejected_records"], 8)
        self.assertEqual(r._queued_bytes, 0)

    def test_short_write_and_metadata_failure_are_visible(self):
        r = self.recorder()
        fake = mock.Mock()
        fake.write.return_value = 1
        with mock.patch.object(r, "_file", return_value=fake):
            with self.assertRaisesRegex(OSError, "Short write"):
                r._append("example", np.ones(3))
        with mock.patch.object(r, "_write_metadata", side_effect=OSError("permission denied")):
            r.start(self.tmp.name)
            r.stop()
        self.assertIn("permission denied", r.error)
        self.assertFalse(r.active)

    def test_bad_batch_is_contained_and_recording_fails(self):
        r = self.recorder()
        r.start(self.tmp.name)
        b = batch()
        b["phase"][0] = np.zeros(2)
        r.on_batch(b)
        r.stop()
        self.assertIn("Malformed", r.error)
        self.assertEqual(self.meta(r)["recording"]["state"], "failed")

    def test_empty_stop_restart_and_bad_frequency(self):
        r = self.recorder()
        self.assertIsNone(r.stop())
        with self.assertRaises(ValueError):
            r.start(self.tmp.name, {0: -1.0})
        d1 = r.start(self.tmp.name)
        r.stop()
        self.assertEqual(self.meta(r)["channels"], {})
        d2 = r.start(self.tmp.name)
        r.on_batch(batch())
        r.stop()
        self.assertNotEqual(d1, d2)
        self.assertIsNone(r.error)


if __name__ == "__main__":
    unittest.main()
