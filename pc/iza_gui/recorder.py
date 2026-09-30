"""Asynchronous logging of relative differential admittance signals.

D1/Freq<N>.ziBin files retain the seven-column big-endian float64 layout, with
a per-row uint8 validity sidecar (D1/Freq<N>.validity.bin) flagging ADC
over-range and invalid input; flagged rows are still written unchanged. The GUI
producer only decimates, copies selected rows and enqueues; conversion and disk
I/O run on one worker. Queue overflow explicitly ends recording without
blocking live controls.
"""

from datetime import datetime
import json
import os
import queue
import tempfile
import threading
import time

import numpy as np

import iza_packet as izp
from .recording_values import INVALID_INPUT, OVER_RANGE, admittance_values

COLUMNS = ["t", "x", "y", "freq", "dio", "auxin0", "auxin1"]


class ZiBinRecorder:
    """One GUI producer; one disk worker. No Qt dependency."""

    def __init__(self, max_queue_bytes=32 * 1024 * 1024):
        if max_queue_bytes <= 0:
            raise ValueError("max_queue_bytes must be positive")
        self._max_queue_bytes = int(max_queue_bytes)
        self._lock = threading.Lock()
        self._thread = None
        self.active = False
        self.error = None
        self.session_dir = None
        self._bytes = 0
        self._records = {}
        self._invalid_total = 0

    @property
    def busy(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, base_dir, freqs=None, decim=1):
        if self.busy or self.active:
            raise RuntimeError("A recording is still active or being flushed")
        decim = max(1, int(decim))
        frequencies = dict(freqs or {})
        if any(not np.isfinite(v) or v < 0 for v in frequencies.values()):
            raise ValueError("Recording frequencies must be finite and nonnegative")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = tempfile.mkdtemp(prefix=f"iza_{stamp}_", dir=base_dir)
        self.session_dir = os.path.join(root, "D1")
        self._freqs = frequencies
        self._decim = decim
        self._gcount = 0
        self._start_wall = time.time()
        self._q = queue.Queue(maxsize=128)
        self._stop = threading.Event()
        self._queued_bytes = 0
        self._accepted_records = self._written_records = self._rejected_records = 0
        self._files = {}
        self._records = {}
        self._invalid = {}
        self._invalid_total = 0
        self._t_first = {}
        self._t_last = {}
        self._adc_samples = 0
        self._bytes = 0
        self.error = None
        self.active = True
        self._thread = threading.Thread(target=self._worker, name="iza-recorder",
                                        daemon=True)
        try:
            self._thread.start()
        except Exception:
            self.active = False
            self._thread = None
            raise
        return self.session_dir

    def _fail(self, message):
        with self._lock:
            if self.error is None:
                self.error = message
            elif message not in self.error:
                self.error += "; " + message
            self.active = False
            self._stop.set()

    def on_batch(self, b):
        if not self.active:
            return
        reserved = 0
        try:
            n0 = b["ts"].size
            i0 = (-self._gcount) % self._decim
            self._gcount += n0
            n = max(0, (n0 - i0 + self._decim - 1) // self._decim)
            if n == 0:
                return
            sel = slice(i0, None, self._decim)
            mask = b["chan_mask"]
            arrays = {"ts": b["ts"]}
            for ch in izp.demod_list(mask):
                arrays[f"sig{ch}"] = b["sig"][ch]
                arrays[f"phase{ch}"] = b["phase"][ch]
            if b.get("orf") is not None:
                arrays["orf"] = b["orf"]
            if b.get("adc") is not None and izp.adc_enabled(mask):
                arrays["adc"] = b["adc"]
            if any(a.ndim != 1 or a.size != n0 or a.dtype.kind not in "iuf"
                   for a in arrays.values()):
                raise ValueError("Malformed recording batch: unequal lengths or nonnumeric data")
            size = n * sum(a.dtype.itemsize for a in arrays.values())
            with self._lock:
                full = self._queued_bytes + size > self._max_queue_bytes
                if not full:
                    self._queued_bytes += size
                    reserved = size
            if full:
                self._rejected_records += n
                self._fail("Recording queue full; recording stopped before losing a batch. "
                           "Reduce recording rate or use a faster disk.")
                return
            owned = {key: a[sel].copy() for key, a in arrays.items()}
            with self._lock:
                # A disk error can end the worker while the producer copies.
                if not self.active:
                    return
                self._q.put_nowait((mask, owned, size))
                self._accepted_records += n
                reserved = 0
        except queue.Full:
            self._rejected_records += n
            self._fail("Recording queue full; recording stopped before losing a batch. "
                       "Reduce recording rate or use a faster disk.")
        except Exception as exc:
            self._fail(f"Recording input failed: {exc}")
        finally:
            if reserved:
                with self._lock:
                    self._queued_bytes = max(0, self._queued_bytes - reserved)

    def stop(self, wait=True, timeout=5.0):
        """Flush accepted batches; GUI uses wait=False and polls busy.

        Timeout does not close files underneath the writer. Starting another
        recording is prohibited until this worker has actually finished.
        """
        if self._thread is None:
            return None
        self.active = False
        self._stop.set()
        if wait:
            self._thread.join(timeout)
            if self.busy:
                raise TimeoutError("Recording is still flushing; disk worker remains active")
        return self.session_dir

    def _file(self, path):
        if path not in self._files:
            # Unbuffered writes expose disk errors here rather than at close.
            self._files[path] = open(os.path.join(self.session_dir, path), "xb", buffering=0)
        return self._files[path]

    def _append(self, path, array):
        f = self._file(path)
        data = memoryview(np.ascontiguousarray(array)).cast("B")
        if f.write(data) != data.nbytes:
            raise OSError(f"Short write to {path}")

    def _write_batch(self, mask, b):
        t = b["ts"].astype(np.float64) / izp.PL_CLK_HZ
        n = t.size
        updates = {}
        byte_count = 0
        offsets = {path: f.tell() for path, f in self._files.items()}
        try:
            for ch in izp.demod_list(mask):
                x, y, flags = admittance_values(
                    b[f"sig{ch}"], b[f"phase{ch}"], b.get("orf", 0))
                rec = np.zeros((n, 7), dtype=">f8")
                rec[:, 0], rec[:, 1], rec[:, 2] = t, x, y
                rec[:, 3] = self._freqs.get(ch, 0.0)
                self._append(f"Freq{ch + 1}.ziBin", rec)
                self._append(f"Freq{ch + 1}.validity.bin", flags)
                updates[ch] = {
                    "total": int(np.count_nonzero(flags)),
                    "invalid_input": int(np.count_nonzero(flags & INVALID_INPUT)),
                    "over_range": int(np.count_nonzero(flags & OVER_RANGE)),
                }
                byte_count += rec.nbytes + flags.nbytes
            if "adc" in b:
                adc = np.ascontiguousarray(b["adc"], dtype="<i2")
                self._append("adc_int16.bin", adc)
                byte_count += adc.nbytes
        except Exception:
            # Roll back the whole batch, including earlier successful channels.
            for path, f in self._files.items():
                try:
                    f.seek(offsets.get(path, 0))
                    f.truncate()
                except OSError as exc:
                    self._fail(f"Partial batch could not be removed from {path}: {exc}")
            raise
        for ch, counts in updates.items():
            self._t_first.setdefault(ch, float(t[0]))
            self._t_last[ch] = float(t[-1])
            self._records[ch] = self._records.get(ch, 0) + n
            total = self._invalid.setdefault(ch, dict.fromkeys(counts, 0))
            for key, value in counts.items():
                total[key] += value
            self._invalid_total += counts["total"]
        if "adc" in b:
            self._adc_samples += n
        self._written_records += n
        self._bytes += byte_count

    def _worker(self):
        try:
            os.makedirs(self.session_dir)
            self._write_metadata("recording")
            checkpoint = time.monotonic()
            while not self._stop.is_set() or not self._q.empty():
                try:
                    mask, b, size = self._q.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    self._write_batch(mask, b)
                finally:
                    with self._lock:
                        self._queued_bytes -= size
                if time.monotonic() - checkpoint >= 1.0:
                    self._write_metadata("recording")
                    checkpoint = time.monotonic()
        except Exception as exc:
            self._fail(f"Recording writer failed: {exc}")
        finally:
            with self._lock:
                self.active = False
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            with self._lock:
                self._queued_bytes = 0
            for f in self._files.values():
                try:
                    f.close()
                except OSError as exc:
                    self._fail(f"Recording close failed: {exc}")
            self._files = {}
            try:
                self._write_metadata("failed" if self.error else "complete")
            except Exception as exc:
                self._fail(f"Recording metadata could not be finalized: {exc}")

    def _write_metadata(self, state):
        with self._lock:
            recording = {"state": state, "error": self.error,
                         "accepted_records": self._accepted_records,
                         "written_records": self._written_records,
                         "unwritten_records": self._accepted_records - self._written_records,
                         "rejected_records": self._rejected_records,
                         "queue_limit_bytes": self._max_queue_bytes}
        rates = {}
        for ch, count in self._records.items():
            duration = self._t_last[ch] - self._t_first[ch]
            rates[ch] = (count - 1) / duration if duration > 0 else 0.0
        meta = {
            "format_version": 3,
            "zi_meta": {"estimated_sample_rate_hz": max(rates.values(), default=0.0),
                        "columns": COLUMNS, "dtype": ">f8"},
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._start_wall)),
            "decimation": self._decim,
            "recording": recording,
            "channels": {
                str(ch): {"file": f"Freq{ch + 1}.ziBin", "records": count,
                          "quantity": "relative_differential_admittance", "label": "Relative differential admittance",
                          "excitation_hz": self._freqs.get(ch, 0.0),
                          "estimated_sample_rate_hz": rates[ch],
                          "validity_file": f"Freq{ch + 1}.validity.bin",
                          "invalid_records": self._invalid[ch]}
                for ch, count in self._records.items()},
            "validity": {
                "dtype": "uint8",
                "rows": "one byte per row of the matching Freq<N>.ziBin",
                "flags": {"valid": 0, "invalid_input": INVALID_INPUT,
                          "adc_over_range": OVER_RANGE},
                "flagged_rows": "written unchanged; flags only mark them",
            },
            "adc": ({"file": "adc_int16.bin", "samples": self._adc_samples, "dtype": "<i2"}
                    if self._adc_samples else None),
            "scaling": {"magnitude": "sig / 2^30 (dimensionless full-scale)",
                        "phase": "rad = phase / 2^29",
                        "t": "board seconds (PL ticks / 200 MHz)",
                        "x_y": "relative differential admittance: mag*cos(phase) + j*mag*sin(phase)"},
        }
        path = os.path.join(self.session_dir, "meta.json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, allow_nan=False)
        os.replace(path + ".tmp", path)

    def status_text(self):
        if self.error:
            return "REC ERROR: " + self.error
        if not self.active and not self.busy:
            return ""
        count = max(list(self._records.values()), default=0)
        state = "REC" if self.active else "Saving"
        return (f"{state} {self._bytes / 1e6:.1f} MB, {count:,} records/ch, "
                f"{self._invalid_total:,} flagged")
