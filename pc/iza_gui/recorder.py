"""recorder.py — stream measurements to disk in Zurich Instruments format.

Matches the lab's existing analysis scripts (see Testing/extract_window.py):
  * one `Freq<N>.ziBin` per demod channel (N = channel + 1), big-endian
    float64, flat records of 7 columns: t, x, y, freq, dio, auxin0, auxin1
      - t     board timestamp in seconds (PL ticks / 200 MHz)
      - x, y  in-phase / quadrature   (mag·cos(φ), mag·sin(φ); mag = sig/2^30)
      - freq  the channel's excitation frequency in Hz
      - dio, auxin0, auxin1  written as 0
  * layout mirrors the lab's sessions:  <base>/iza_<stamp>/D1/Freq<N>.ziBin
  * `meta.json` sidecar with {"zi_meta": {"estimated_sample_rate_hz": ...}}
    (the key iza_sender/iza_view/iza_plotter already read)
  * raw ADC samples, when streaming, land in `adc_int16.bin` (int16 LE).

Records are written as they arrive (up to ~11 MB/s per channel at the full CIC
output rate — 200 MHz / R, i.e. 200 kHz at R=1000 down to 25 kHz at R=8000; mind
your disk on long recordings).  Pass `decim` to start() to
keep only every Nth record (uniform, phase-continuous across batches) and cut
the rate/size proportionally; meta.json's estimated_sample_rate_hz reflects the
decimated rate.
"""

import json
import os
import time

import numpy as np

import iza_packet as izp
from . import data_stream as ds

COLUMNS = ["t", "x", "y", "freq", "dio", "auxin0", "auxin1"]


class ZiBinRecorder:
    """start() -> feed on_batch() -> stop().  One instance per GUI."""

    def __init__(self):
        self.active = False
        self.session_dir = None
        self._files = {}          # ch -> open file (Freq<N>.ziBin)
        self._adc_file = None
        self._freqs = {}          # ch -> excitation Hz (for the freq column)
        self._records = {}        # ch -> records written
        self._adc_samples = 0
        self._bytes = 0
        self._t_first = {}        # ch -> first timestamp (s)
        self._t_last = {}         # ch -> last timestamp (s)
        self._start_wall = None
        self._decim = 1           # keep every Nth record (1 = full rate)
        self._gcount = 0          # running record index (for continuous phase)

    # ------------------------------------------------------------------ api
    def start(self, base_dir, freqs=None, decim=1):
        """Create <base_dir>/iza_<stamp>/D1/ and begin recording.
        `freqs` maps channel -> excitation Hz for the freq column.
        `decim` keeps every Nth record (1 = the full CIC output rate)."""
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(base_dir, f"iza_{stamp}", "D1")
        os.makedirs(self.session_dir, exist_ok=True)
        self._freqs = dict(freqs or {})
        self._files = {}
        self._adc_file = None
        self._records = {}
        self._adc_samples = 0
        self._bytes = 0
        self._t_first = {}
        self._t_last = {}
        self._decim = max(1, int(decim))
        self._gcount = 0
        self._start_wall = time.time()
        self.active = True
        return self.session_dir

    def on_batch(self, b):
        if not self.active:
            return
        n0 = b["ts"].size
        if n0 == 0:
            return
        # Decimate by keeping every Nth record, with the phase carried across
        # batches so the kept samples stay uniformly spaced over the whole stream
        # (all channels + ADC use the SAME picks, so they stay aligned).
        if self._decim > 1:
            i0 = (-self._gcount) % self._decim
            sel = slice(i0, None, self._decim)
        else:
            sel = slice(None)
        self._gcount += n0

        t = b["ts"][sel].astype(np.float64) / izp.PL_CLK_HZ
        n = t.size
        if n == 0:
            return
        for ch in izp.demod_list(b["chan_mask"]):
            mag = ds.scale_mag(b["sig"][ch][sel])
            phr = ds.scale_phase_rad(b["phase"][ch][sel])
            rec = np.empty((n, 7), dtype=">f8")
            rec[:, 0] = t
            rec[:, 1] = mag * np.cos(phr)          # x (in-phase)
            rec[:, 2] = mag * np.sin(phr)          # y (quadrature)
            rec[:, 3] = self._freqs.get(ch, 0.0)   # freq
            rec[:, 4:7] = 0.0                      # dio, auxin0, auxin1
            f = self._files.get(ch)
            if f is None:
                path = os.path.join(self.session_dir, f"Freq{ch + 1}.ziBin")
                f = self._files[ch] = open(path, "ab")
                self._records[ch] = 0
                self._t_first[ch] = float(t[0])
            rec.tofile(f)
            self._records[ch] += n
            self._t_last[ch] = float(t[-1])
            self._bytes += rec.nbytes
        if b.get("adc") is not None and izp.adc_enabled(b["chan_mask"]):
            if self._adc_file is None:
                self._adc_file = open(
                    os.path.join(self.session_dir, "adc_int16.bin"), "ab")
            a = np.ascontiguousarray(b["adc"][sel], dtype="<i2")
            a.tofile(self._adc_file)
            self._adc_samples += a.size
            self._bytes += a.nbytes

    def stop(self):
        """Close files and write the meta.json sidecar. Returns the dir."""
        if not self.active:
            return None
        self.active = False
        for f in self._files.values():
            f.close()
        if self._adc_file is not None:
            self._adc_file.close()

        rates = {}
        for ch, nrec in self._records.items():
            dur = self._t_last[ch] - self._t_first[ch]
            rates[ch] = (nrec - 1) / dur if dur > 0 and nrec > 1 else 0.0
        est = max(rates.values()) if rates else 0.0
        meta = {
            "zi_meta": {
                "estimated_sample_rate_hz": est,
                "columns": COLUMNS,
                "dtype": ">f8",
            },
            "recorded_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._start_wall)),
            "decimation": self._decim,   # 1 = full rate; N = kept every Nth record
            "channels": {
                str(ch): {
                    "file": f"Freq{ch + 1}.ziBin",
                    "records": self._records[ch],
                    "excitation_hz": self._freqs.get(ch, 0.0),
                    "estimated_sample_rate_hz": rates.get(ch, 0.0),
                } for ch in sorted(self._records)
            },
            "adc": ({"file": "adc_int16.bin", "samples": self._adc_samples,
                     "dtype": "<i2"} if self._adc_samples else None),
            "scaling": {"magnitude": "sig / 2^30 (dimensionless full-scale)",
                        "phase": "rad = phase / 2^29",
                        "t": "board seconds (PL ticks / 200 MHz)"},
        }
        with open(os.path.join(self.session_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        d = self.session_dir
        self._files = {}
        self._adc_file = None
        return d

    def status_text(self):
        if not self.active:
            return ""
        nrec = max(self._records.values()) if self._records else 0
        return (f"REC {self._bytes / 1e6:.1f} MB, "
                f"{nrec:,} records/ch")
