#!/usr/bin/env python3
"""
iza_sweep.py — frequency-response sweep at low amplitude, guarded against clipping.

Steps one tone across a log-spaced list of frequencies and, at each point,
averages the demodulated output (x + jy).  Results are divided by the DAC
amplitude actually used, so points measured at different amplitudes compare
directly: units are "demod output per unit DAC full-scale amplitude".

Clipping guards:
  * The raw-ADC monitor and the over-range flag carry ONE ADC sample per record
    (every R clocks; R = 1000 gives 200 kHz records).  A tone that is a multiple
    of the record rate (e.g. 15 or 25 MHz at R = 1000) is sampled at the same
    point of its cycle in every record, so its peaks can go unseen.  The sweep
    picks frequencies whose snapshot walks through >= 16 points of the cycle
    (the nearest such grid point to each target), so the monitor sees the peak.
  * Each point's ADC peak must stay below --max-peak of full scale (default
    0.5, i.e. -6 dBFS) with no over-range flags; otherwise the amplitude is
    lowered and the point measured again.
  * Linearity check (on by default): each point is measured again at half
    amplitude, and the two normalized results must agree within noise.

De-embedding (open / reference):
  1. Sweep the fixture with the load removed:  --out open.csv
  2. Sweep with the load:                       --open open.csv --out load.csv
     The open (fixture coupling) is subtracted point by point.
  3. Optionally, also divide by a sweep of a known reference load (taken the
     same way):  --ref ref.csv   ->   result = (H - H_open) / (H_ref - H_open)
  --analyze FILE redoes 2-3 offline from saved sweeps, without the board.

Before running: close the GUI (it holds the data port, UDP 7100); the board
must be running with both converters initialized (Start, then Initialize
DAC + ADC; CLI: run, dac-init, adc-init).  The sweep disarms triggering (it
cannot be re-armed automatically) and restores the tone, channel and packet
settings it touched.  Points measured before an error or Ctrl-C are saved.

Usage:
  python iza_sweep.py --board 192.168.0.80 --start 500e3 --stop 40e6 \\
                      --points 40 --amp 5 --out open.csv
  python iza_sweep.py --board 192.168.0.80 --open open.csv --out load.csv
  python iza_sweep.py --analyze load.csv --open open.csv --ref ref.csv
"""

import argparse
import csv
import math
import os
import signal
import socket
import sys
import shutil
import tempfile
import threading
import time

import numpy as np

import iza_ctrl
import iza_packet as izp

DEFAULT_BOARD = "192.168.0.80"
DATA_PORT = 7100
MAG_SCALE = float(1 << 30)            # demod magnitude fix32_30
PHASE_SCALE = float(1 << 29)          # demod phase fix32_29 (radians)
ADC_FS = 32768.0                      # raw-ADC monitor full scale (int16)
UNITY = iza_ctrl.AMP_DEFAULT          # 0x8000 = 100 % of DAC full scale
RASTER = iza_ctrl.RASTER_HZ           # 12.5 kHz frequency grid
MOD = iza_ctrl.FCW_MAX                # DDS modulus (16000)
F_MAX = 50e6                          # same limit as the GUI tone boxes
F_DAC_CLEAN = 40e6                    # 2x interpolation: HB1 passband edge
F_HPF = 400e3                         # analog high-pass cutoff (per the docs)
FCW_HPF = int(math.ceil(F_HPF / RASTER))
DAC_FORMAT_REG = 0x03                 # AD9122 Data format: 0x01 after dac-init
SLEEP = time.sleep                    # injectable (tests run on a virtual clock)

COLUMNS = ["freq_hz", "fcw", "cover", "amp_pct", "re", "im", "mag", "phase_deg",
           "se", "adc_peak", "or_frac", "n", "lin_err_pct", "lin_phase_deg",
           "flags"]
DCOLUMNS = ["d_re", "d_im", "d_mag", "d_phase_deg", "d_se"]
BAD_FLAGS = {"headroom", "nonlinear", "unsettled", "low-snr"}
CARRY_FLAGS = {"headroom", "nonlinear", "unsettled"}   # from open/ref points


class SweepError(Exception):
    pass


def _finite(*vals):
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals)


# ----------------------------------------------------------- frequency plan
def coverage(fcw, rec_ticks):
    """How many distinct points of the tone's cycle the once-per-record ADC
    snapshot hits: the phase advances fcw * rec_ticks / MOD cycles per record."""
    return MOD // math.gcd(fcw * rec_ticks, MOD)


def max_coverage(rec_ticks):
    """Best coverage any frequency can get at this record spacing."""
    return MOD // math.gcd(rec_ticks, MOD)


def plan_frequencies(start, stop, points, rec_ticks, min_cover=16, notes=None):
    """Log-spaced targets, each snapped to the nearest unused grid point (fcw)
    whose snapshot coverage is at least min_cover (capped at what the record
    spacing allows). Points stay inside [start, stop], and at or above the
    400 kHz high-pass when start is, unless no qualifying grid point is left
    there; then the nearest one outside is used and a note is added."""
    if not _finite(start, stop) or not 0 < start <= stop <= F_MAX:
        raise SweepError(f"need 0 < start <= stop <= {F_MAX / 1e6:g} MHz")
    if points < 1:
        raise SweepError("--points must be at least 1")
    want = min(min_cover, max_coverage(rec_ticks))
    k_max = int(F_MAX // RASTER)
    good = [k for k in range(1, k_max + 1) if coverage(k, rec_ticks) >= want]
    if points > len(good):
        raise SweepError(f"could not place all points; at most {len(good)} "
                         "--points at this record spacing")
    lo = max(1, math.ceil(start / RASTER - 1e-9))     # >= FCW_HPF if start >= F_HPF
    hi = min(k_max, math.floor(stop / RASTER + 1e-9))
    floor = FCW_HPF if start >= F_HPF else 1
    inside = [k for k in good if lo <= k <= hi]
    targets = np.geomspace(start, stop, points) if points > 1 else [start]
    chosen = set()
    for t in targets:
        kt = t / RASTER
        cands = [k for k in inside if k not in chosen]
        if not cands:
            # nothing left inside: the nearest elsewhere, above the HPF if possible
            cands = [k for k in good if k not in chosen]
            pick = min(cands, key=lambda k: (k < floor, abs(k - kt), k))
            if notes is not None:
                notes.append(f"{t / 1e6:.6g} MHz placed at {pick * RASTER / 1e6:.6g} MHz, "
                             "outside the requested range (no grid point inside it "
                             "gives full ADC-snapshot coverage)")
        else:
            pick = min(cands, key=lambda k: (abs(k - kt), k))
        chosen.add(pick)
    return sorted(chosen)


# ----------------------------------------------------------- data source
def _merge(parts, mask):
    demods = izp.demod_list(mask)
    if not parts:
        return dict(n=0, ts=np.zeros(0, np.uint64), orf=np.zeros(0, np.uint8),
                    sig={c: np.zeros(0, np.int32) for c in demods},
                    phase={c: np.zeros(0, np.int32) for c in demods},
                    adc=np.zeros(0, np.int32) if izp.adc_enabled(mask) else None)
    cat = np.concatenate
    return dict(
        n=sum(p["n"] for p in parts),
        ts=cat([p["ts"] for p in parts]),
        orf=cat([p["orf"] for p in parts]),
        sig={c: cat([p["sig"][c] for p in parts]) for c in demods},
        phase={c: cat([p["phase"][c] for p in parts]) for c in demods},
        adc=(cat([p["adc"] for p in parts]) if izp.adc_enabled(mask) else None))


class UdpSource:
    """The board's UDP data stream (port 7100)."""

    BUF = 65535     # whole datagram: packets that straddle a framing change can
                    # exceed the MTU, and Windows errors on a short buffer

    def __init__(self, port=DATA_PORT):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for want in (32, 16, 8):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, want << 20)
                break
            except OSError:
                continue
        # No SO_REUSEADDR: if the GUI holds the port, fail loudly instead of
        # silently sharing (on Windows) the datagrams with it.
        try:
            s.bind(("0.0.0.0", port))
        except (OSError, OverflowError) as e:
            s.close()
            raise SweepError(f"cannot listen on UDP {port} ({e}). Close the GUI "
                             "first: it holds the data port.") from e
        s.settimeout(0.2)
        self.sock = s
        self.drops = 0
        self._seq = None

    def close(self):
        self.sock.close()

    def drain(self):
        """Discard everything already queued."""
        self.sock.setblocking(False)
        try:
            for _ in range(1_000_000):
                try:
                    self.sock.recvfrom(self.BUF)
                except BlockingIOError:
                    break               # queue is empty
                except OSError:
                    continue            # an odd datagram: keep draining
        finally:
            self.sock.settimeout(0.2)
            self._seq = None

    def collect(self, seconds, mask):
        """Records with layout `mask` (demod bits + bit 4 raw ADC) for `seconds`."""
        end = time.monotonic() + seconds
        parts = []
        while time.monotonic() < end:
            try:
                data, _ = self.sock.recvfrom(self.BUF)
            except socket.timeout:
                continue
            except OSError:
                continue
            if len(data) < izp.HDR_LEN:
                continue
            h = izp.parse_header(data)
            if h["magic"] != izp.MAGIC or h["chan_mask"] != mask:
                continue
            if self._seq is not None:
                gap = (h["seq"] - self._seq - 1) & 0xFFFFFFFF
                if gap < 100_000:       # ignore reordering / counter restarts
                    self.drops += gap
            self._seq = h["seq"]
            payload = data[izp.HDR_LEN:izp.HDR_LEN + h["payload_len"]]
            rec = izp.deinterleave(payload, mask, h["stride_words"])
            if rec is None:
                continue
            d = np.diff(rec["ts"].astype(np.int64))
            if d.size and (d <= 0).any():
                continue                # misframed packet across a config change
            parts.append(rec)
        return _merge(parts, mask)


# ----------------------------------------------------------- statistics
def _se(z, blocks):
    """Standard error of the mean from block means (records are correlated
    over the demod filter's span, so per-record scatter would understate it)."""
    n = z.size
    if n >= 2 * blocks:
        bm = np.array([b.mean() for b in np.array_split(z, blocks)])
        return math.sqrt(bm.real.var(ddof=1) + bm.imag.var(ddof=1)) / math.sqrt(blocks)
    return float(np.abs(z - z.mean()).std()) / math.sqrt(max(1, n))


def _se_noise(z, blocks=8):
    """Noise-only standard error, for the settling and linearity checks. Built
    from the median second difference of block means: second differences
    cancel a steady drift, and the median ignores the one or two that straddle
    a step, so neither a transient nor a drift can inflate it and hide itself."""
    if z.size < 4 * blocks:
        return _se(z, blocks)
    bm = np.array([b.mean() for b in np.array_split(z, blocks)])
    d2 = bm[2:] - 2 * bm[1:-1] + bm[:-2]
    # |d2| is Rayleigh with per-component variance 6 v (v = that of one block
    # mean); its median is 1.1774 x the Rayleigh scale
    v = (float(np.median(np.abs(d2))) / 1.1774) ** 2 / 6
    return math.sqrt(2 * v / blocks)


def summarize(data, ch, blocks=8):
    """Complex mean of x + jy, its standard error, and a settling check:
    the first-half minus second-half difference, and the noise it should be
    compared with (see _se_noise)."""
    z = (data["sig"][ch] / MAG_SCALE) * np.exp(1j * data["phase"][ch] / PHASE_SCALE)
    n = z.size
    if n == 0:
        nan = float("nan")
        return dict(mean=complex(nan), se=nan, drift=nan, se_noise=nan)
    half = n // 2
    return dict(mean=complex(z.mean()), se=_se(z, blocks),
                drift=abs(complex(z[:half].mean() - z[half:].mean())) if half else 0.0,
                se_noise=_se_noise(z, blocks))


def adc_stats(data):
    """(ADC peak as a fraction of full scale, fraction of records flagged
    over-range).

    The monitor sample and the over-range bits are one ADC sample apart (the
    monitor goes through mux_0's register, the OR bits do not), so with R even
    they cover opposite sample parities. Above 40 MHz, where the DAC's HB1
    image alternates sign between samples, the peak limit therefore applies to
    one parity and the over-range flag (at full scale) guards the other."""
    n = max(1, data["n"])
    or_frac = float(np.count_nonzero(data["orf"])) / n
    adc = data.get("adc")
    if adc is None or not adc.size:
        return float("nan"), or_frac
    return float(np.abs(adc.astype(np.int64)).max()) / ADC_FS, or_frac


# ----------------------------------------------------------- board control
def _retry(fn, *args, tries=3):
    """Control calls are UDP: retry a lost or late datagram. A 'board returned
    status' error is deterministic and is not retried."""
    for i in range(tries):
        try:
            return fn(*args)
        except iza_ctrl.CtrlError as e:
            if "returned status" in str(e) or i == tries - 1:
                raise
        except OSError:
            if i == tries - 1:
                raise


def preflight(ctrl):
    """Refuse to sweep a board that would give garbage."""
    r0 = _retry(ctrl.reg_read, iza_ctrl.R_SYS_CTRL)
    if not r0 & (1 << iza_ctrl.B_DAC_CHIP_NRST):
        raise SweepError("DAC is held in reset. In the GUI press Start, then "
                         "Initialize DAC + ADC (CLI: run, dac-init, adc-init).")
    if not r0 & (1 << iza_ctrl.B_RUN):
        raise SweepError("instrument is stopped. Press Start (CLI: run).")
    if r0 & (1 << iza_ctrl.B_ADC_SEL):
        raise SweepError("Measurement input is set to internal loopback; set it "
                         "to Analog input (ADC) (CLI: demod-input 0).")
    if r0 & (1 << iza_ctrl.B_DAC_TESTSIG):
        raise SweepError("DAC output is the test/replay signal; set it to "
                         "Signal generator (tones) (CLI: dac-output 0).")
    fmt = _retry(ctrl.dac_read, DAC_FORMAT_REG)
    if fmt is None or (fmt & 0x03) != 0x01:
        shown = "no reply" if fmt is None else f"0x{fmt:02X}"
        raise SweepError(f"DAC is not initialized (reg 0x03 = {shown}, expected "
                         "0x01). Press Initialize DAC + ADC (CLI: dac-init, "
                         "adc-init).")


def check_adc_format(data):
    """Call with every tone OFF. An AD9467 still at its power-on output format
    (offset binary) has its MSB flipped when read as two's complement, so a
    quiet input (a few LSB around mid-scale) reads near +/- full scale, with
    no over-range flags. An initialized ADC reads a few LSB."""
    adc = data.get("adc")
    if adc is None or not adc.size:
        return
    _, or_frac = adc_stats(data)
    if float(np.median(np.abs(adc.astype(np.int64)))) > 0.5 * ADC_FS and or_frac == 0:
        raise SweepError("with the tones off the raw ADC reads near full scale "
                         "with no over-range: the ADC looks uninitialized "
                         "(offset-binary output). Press Initialize DAC + ADC "
                         "(CLI: adc-init).")


def disarm_trigger(ctrl, log):
    """A sweep's frequency and amplitude steps look like events, and its
    control traffic would keep the trigger watchdog fed: disarm first."""
    for _ in range(2):
        try:
            ctrl.trig_off()
            log("triggering disarmed for the sweep (re-arm it afterwards if needed)")
            return True
        except (iza_ctrl.CtrlError, OSError):
            continue
    log("WARNING: could not confirm that triggering is disarmed")
    return False


def save_state(ctrl, ch):
    regs = (iza_ctrl.R_CH_EN, iza_ctrl.R_PKT_CFG, iza_ctrl.R_CH_FA[ch])
    return {r: _retry(ctrl.reg_read, r) for r in regs}


def _safe_log(fn):
    """Console output must never abort a sweep or skip the restore (a closed
    pipe, e.g. `| head`, makes print raise)."""
    def log(msg):
        try:
            fn(msg)
        except Exception:
            pass
    return log


def restore_state(ctrl, saved, ch, log=None):
    """Put back what the sweep changed: the channel mask first (so the swept
    tone goes off if it was off before, while it still has the sweep's low
    amplitude), then the packet layout, then the tone register. If the mask
    could not be restored and the channel's tone was off before, the tone
    register is left at the sweep's low amplitude rather than playing the old
    one under the sweep's mask. Every other write is attempted even if one
    fails, and a Ctrl-C cannot cut it short (in the main thread)."""
    log = _safe_log(log or print)
    old = None
    if threading.current_thread() is threading.main_thread():
        old = signal.signal(signal.SIGINT, signal.SIG_IGN)
    errors = {}
    try:
        log("restoring board settings...")

        def put(r):
            try:
                _retry(ctrl.reg_write, r, saved[r])
                errors.pop(r, None)
                return True
            except Exception as e:      # keep going: restore as much as possible
                errors[r] = str(e)
                return False
        mask_ok = put(iza_ctrl.R_CH_EN)
        put(iza_ctrl.R_PKT_CFG)
        tone = iza_ctrl.R_CH_FA[ch]
        if not mask_ok:
            mask_ok = put(iza_ctrl.R_CH_EN)     # the link may be back by now
        if mask_ok or saved[iza_ctrl.R_CH_EN] & (1 << ch):
            put(tone)
        else:
            errors[tone] = ("skipped: channel mask not restored, tone left at "
                            "the sweep amplitude")
    finally:
        if old is not None:
            signal.signal(signal.SIGINT, old)
    if errors:
        log("WARNING: could not restore " + "; ".join(f"reg {r}: {m}" for r, m in errors.items()))
    else:
        log("board settings restored")
    return not errors


def _tone(fcw, code):
    return ((code & 0xFFFF) << 16) | (fcw & iza_ctrl.FCW_MASK)


# ----------------------------------------------------------- measurement
class Config:
    def __init__(self, ch=0, amp_pct=5.0, min_amp_pct=0.25, max_peak=0.5,
                 settle=0.1, avg=0.2, linearity=True, lin_tol=0.01,
                 start=500e3, stop=40e6, points=40):
        if not (isinstance(ch, int) and 0 <= ch <= 3):
            raise SweepError("--ch must be 0..3")
        if not _finite(amp_pct, min_amp_pct) or not 0 < min_amp_pct <= amp_pct <= 100:
            raise SweepError("need 0 < --min-amp <= --amp <= 100")
        if not _finite(max_peak) or not 0 < max_peak < 1:
            raise SweepError("--max-peak must be between 0 and 1")
        if not _finite(settle) or not 0 <= settle <= 60:
            raise SweepError("--settle must be 0..60 s")
        if not _finite(avg) or not 0.01 <= avg <= 60:
            raise SweepError("--avg must be 0.01..60 s")
        if not _finite(lin_tol) or not lin_tol > 0:
            raise SweepError("--lin-tol must be positive")
        if not isinstance(points, int):
            raise SweepError("--points must be an integer")
        plan_frequencies(start, stop, points, 1000)     # validate before the board
        self.ch, self.amp_pct, self.min_amp_pct = ch, amp_pct, min_amp_pct
        self.max_peak, self.settle, self.avg = max_peak, settle, avg
        self.linearity, self.lin_tol = linearity, lin_tol
        self.start, self.stop, self.points = start, stop, points

    @staticmethod
    def code(pct):
        return max(1, min(0xFFFF, int(round(pct / 100.0 * UNITY))))

    @property
    def mask(self):
        return (1 << self.ch) | 0x10       # one demod channel + raw ADC monitor


def _collect(src, cfg):
    data = src.collect(cfg.avg, cfg.mask)
    if data["n"] < 50:                  # a short stall: try once more
        src.drain()
        data = src.collect(cfg.avg, cfg.mask)
    if data["n"] < 50:
        raise SweepError(f"only {data['n']} records in {cfg.avg:g} s. Is the "
                         "board streaming to this PC?")
    return data


def _measure(ctrl, src, cfg, fcw, code, settle, sleep):
    _retry(ctrl.reg_write, iza_ctrl.R_CH_FA[cfg.ch], _tone(fcw, code))
    sleep(settle)
    src.drain()
    data = _collect(src, cfg)
    s = summarize(data, cfg.ch)
    peak, or_frac = adc_stats(data)
    return dict(raw=s["mean"], se=s["se"], drift=s["drift"], se_noise=s["se_noise"],
                peak=peak, or_frac=or_frac, n=data["n"])


def _unsettled(m):
    # the halves of a settled measurement differ by noise only: typically
    # ~1.4 x the noise standard error, so 10 x is far outside chance
    return m["drift"] > max(10 * m["se_noise"], 0.005 * abs(m["raw"]))


def _measure_settled(ctrl, src, cfg, fcw, code, sleep):
    m = _measure(ctrl, src, cfg, fcw, code, cfg.settle, sleep)
    if _unsettled(m):
        m = _measure(ctrl, src, cfg, fcw, code, 4 * cfg.settle, sleep)
        m["unsettled"] = _unsettled(m)
    else:
        m["unsettled"] = False
    return m


def _headroom_ok(m, cfg):
    return m["peak"] <= cfg.max_peak and m["or_frac"] == 0


def measure_point(ctrl, src, cfg, fcw, rec_ticks, sleep=time.sleep):
    """One frequency: find an amplitude with headroom, measure, check linearity."""
    flags = []
    code, min_code = cfg.code(cfg.amp_pct), cfg.code(cfg.min_amp_pct)
    while True:     # each failed pass at least halves code: ends at min_code
        m = _measure_settled(ctrl, src, cfg, fcw, code, sleep)
        if _headroom_ok(m, cfg) or code <= min_code:
            break
        scale = 0.7 * cfg.max_peak / m["peak"] if m["peak"] > 0 else 0.5
        code = max(min_code, int(code * min(0.5, scale)))
    if not _headroom_ok(m, cfg):
        flags.append("headroom")        # still too big at the smallest amplitude
    a = code / UNITY
    h = m["raw"] / a
    se = m["se"] / a
    if m["unsettled"]:
        flags.append("unsettled")
    if abs(h) < 3 * se:
        flags.append("low-snr")
    lin_err = lin_ph = float("nan")
    if cfg.linearity:
        half = max(1, code // 2)
        a2 = half / UNITY
        m2 = _measure_settled(ctrl, src, cfg, fcw, half, sleep)
        if m2["unsettled"]:
            # no verdict from a window that did not settle (its spread would
            # also loosen the tolerance)
            if "unsettled" not in flags:
                flags.append("unsettled")
        elif abs(h) > 0:
            h2 = m2["raw"] / a2
            ratio = h2 / h
            lin_err = abs(ratio - 1) * 100
            lin_ph = math.degrees(math.atan2(ratio.imag, ratio.real))
            # drift-proof noise of both windows, relative, ~4 sigma
            noise = 4 * math.hypot(m["se_noise"] / a, m2["se_noise"] / a2) / abs(h)
            if abs(ratio - 1) > max(cfg.lin_tol, noise):
                flags.append("nonlinear")
    f = fcw * RASTER
    if f < F_HPF:
        flags.append("below-hpf")
    if f > F_DAC_CLEAN:
        flags.append("dac-filter")
    return dict(freq_hz=f, fcw=fcw, cover=coverage(fcw, rec_ticks),
                amp_pct=100 * a, re=h.real, im=h.imag, mag=abs(h),
                phase_deg=math.degrees(math.atan2(h.imag, h.real)), se=se,
                adc_peak=m["peak"], or_frac=m["or_frac"], n=m["n"],
                lin_err_pct=lin_err, lin_phase_deg=lin_ph, flags=";".join(flags))


def record_rate(ticks):
    return izp.PL_CLK_HZ / ticks if ticks else float("nan")


def run_sweep(ctrl, src, cfg, sleep=time.sleep, log=None):
    """Preflight, set up, sweep, and always restore. Returns (rows, meta).
    An error after at least one point is measured is recorded as
    meta['aborted'] and the points so far are returned; a restore that did
    not fully succeed sets meta['restore_failed']."""
    log = _safe_log(log or print)
    preflight(ctrl)
    disarm_trigger(ctrl, log)
    saved = save_state(ctrl, cfg.ch)
    rows, meta = [], {}
    ok = False
    try:
        try:
            _sweep(ctrl, src, cfg, sleep, log, rows, meta)
        except KeyboardInterrupt:
            meta["aborted"] = "interrupted"
        except Exception as e:
            if not rows:
                raise
            meta["aborted"] = str(e)
    finally:
        ok = restore_state(ctrl, saved, cfg.ch, log)     # before any other output
    if not ok:
        meta["restore_failed"] = 1
    if meta.get("aborted") == "interrupted":
        log(f"interrupted: keeping {len(rows)} measured points")
    elif "aborted" in meta:
        log(f"ERROR after {len(rows)} points: {meta['aborted']}")
    return rows, meta


def _sweep(ctrl, src, cfg, sleep, log, rows, meta):
    """The sweep proper. Fills `rows` and `meta` in place as it goes, so the
    caller keeps the points measured before an error."""
    # quiet tone, still switched off: this channel's demod + raw ADC only
    first = max(1, int(round(cfg.start / RASTER)))
    _retry(ctrl.reg_write, iza_ctrl.R_CH_FA[cfg.ch], _tone(first, cfg.code(cfg.amp_pct)))
    rx = 1 << cfg.ch
    _retry(ctrl.set_channel_mask, 0, rx, True)
    stride = iza_ctrl.IzaCtrl.stride_words(rx, True)
    _retry(ctrl.set_pkt_cfg, max(1, min(255, iza_ctrl.MTU_PAYLOAD // (stride * 4))), rx)
    sleep(0.3)                          # let the framing change flush through
    src.drain()
    probe = src.collect(0.15, cfg.mask)
    if probe["n"] < 3:
        port = src.sock.getsockname()[1] if hasattr(src, "sock") else DATA_PORT
        raise SweepError(f"no data arriving on UDP {port}. Is the board streaming "
                         "to this PC (IP address, firewall)?")
    check_adc_format(probe)             # needs the tones off
    _retry(ctrl.set_channel_mask, rx, rx, True)          # now switch the tone on
    ticks = int(round(float(np.median(np.diff(probe["ts"].astype(np.int64))))))
    best = max_coverage(ticks)
    if best < 8:
        log(f"WARNING: at this record spacing ({ticks} ticks) the ADC snapshot "
            f"covers only {best} points per cycle, so the peak check is weak; "
            "rely on the linearity check (keep it on).")
    notes = []
    fcws = plan_frequencies(cfg.start, cfg.stop, cfg.points, ticks, notes=notes)
    for note in notes:
        log("note: " + note)
    meta.update(record_ticks=ticks, record_rate_hz=record_rate(ticks),
                channel=cfg.ch, amp_pct=cfg.amp_pct, max_peak=cfg.max_peak,
                settle_s=cfg.settle, avg_s=cfg.avg,
                linearity=int(cfg.linearity), points=len(fcws))
    for i, fcw in enumerate(fcws, 1):
        row = measure_point(ctrl, src, cfg, fcw, ticks, sleep)
        rows.append(row)
        log(f"[{i:3d}/{len(fcws)}] {row['freq_hz'] / 1e6:9.4f} MHz  "
            f"amp {row['amp_pct']:5.2f}%  |H| {row['mag']:.5g}  "
            f"{row['phase_deg']:7.2f} deg  peak {row['adc_peak']:.2f} FS"
            + (f"  [{row['flags']}]" if row["flags"] else ""))


# ----------------------------------------------------------- files
def write_csv(path, rows, meta=None):
    """Atomic: written to a temporary file first, so a failed write never
    truncates an existing file."""
    cols = COLUMNS + (DCOLUMNS if rows and "d_re" in rows[0] else [])
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".sweep_", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            for k, v in (meta or {}).items():
                fh.write(f"# {k} = {v}\n")
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in cols})
        _replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _replace(tmp, path, tries=5):
    """os.replace, which on Windows fails while any program (a viewer,
    OneDrive, antivirus) holds the target open, even with full sharing:
    retry briefly, then copy over the target in place, which works whenever
    that program allows writing."""
    for i in range(tries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i < tries - 1:
                time.sleep(0.2)
    shutil.copyfile(tmp, path)
    os.remove(tmp)


def read_csv(path):
    meta, lines = {}, []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                k, _, v = line[1:].partition("=")
                meta[k.strip()] = v.strip()
            else:
                lines.append(line)
    rows = []
    for r in csv.DictReader(lines):
        row = {}
        for k, v in r.items():
            if k is None:
                continue
            if k == "flags":
                row[k] = v or ""
            else:
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    row[k] = float("nan")
        row.setdefault("flags", "")
        rows.append(row)
    return rows, meta


def load_sweep(path, label):
    """A saved sweep for de-embedding, checked before the board is touched."""
    try:
        rows, meta = read_csv(path)
    except OSError as e:
        raise SweepError(f"cannot read {label} sweep {path}: {e}") from e
    if not rows or not {"freq_hz", "re", "im"} <= set(rows[0]):
        raise SweepError(f"{path} is not an iza_sweep CSV (needs freq_hz, re, im)")
    if not any(math.isfinite(r["re"]) and math.isfinite(r["im"]) for r in rows):
        raise SweepError(f"{path} has no valid points")
    return rows, meta


def check_writable(path):
    """Fail now, not after the sweep, if the output can't be written: a
    missing folder is created; a read-only folder, or a file another program
    holds without write sharing (as Excel does), is refused."""
    folder = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(folder, exist_ok=True)
        if os.path.exists(path):
            with open(path, "a"):
                pass
        else:
            fd, tmp = tempfile.mkstemp(prefix=".sweep_", dir=folder)
            os.close(fd)
            os.remove(tmp)
    except OSError as e:
        raise SweepError(f"cannot write {path} ({e}). Is it open in another "
                         "program?") from e


def save_rows(path, rows, meta, log=None):
    """Write; if that fails, fall back to a timestamped file in the temp
    folder so a finished sweep is never lost. Returns (path used, rescued?)."""
    log = _safe_log(log or (lambda m: print(m, file=sys.stderr)))
    try:
        write_csv(path, rows, meta)
        return path, False
    except (OSError, UnicodeError) as e:
        alt = os.path.join(tempfile.gettempdir(),
                           time.strftime("sweep_rescued_%Y%m%d_%H%M%S.csv"))
        log(f"ERROR: could not write {path} ({e}); it was NOT updated. The rows "
            f"are saved in {alt}")
        write_csv(alt, rows, meta)
        return alt, True


# ----------------------------------------------------------- analysis
def _complex(rows):
    return np.array([r["re"] + 1j * r["im"] for r in rows])


def _on_grid(rows, freqs, label):
    """Another sweep at `freqs`: (H, se, flags, interpolated?) per point.
    Exact frequency matches are taken as is; others are interpolated in log f
    (with the neighbours' flags and the larger se); outside its range: NaN."""
    order = sorted(range(len(rows)), key=lambda i: rows[i]["freq_hz"])
    rows = [rows[i] for i in order]
    f0 = np.array([r["freq_hz"] for r in rows])
    h0 = _complex(rows)
    se0 = np.array([r.get("se", float("nan")) for r in rows])
    fl0 = [set(x for x in r.get("flags", "").split(";") if x and x != "interp")
           for r in rows]
    exact = {f: i for i, f in enumerate(f0)}
    hs, ses, fls, interp = [], [], [], []
    for f in freqs:
        if f in exact:
            i = exact[f]
            hs.append(h0[i]); ses.append(se0[i]); fls.append(fl0[i]); interp.append(False)
        elif f0[0] <= f <= f0[-1]:
            j = int(np.searchsorted(f0, f))
            lf, lf0 = math.log(f), np.log(f0)
            hs.append(np.interp(lf, lf0, h0.real) + 1j * np.interp(lf, lf0, h0.imag))
            ses.append(max(se0[j - 1], se0[j]))
            fls.append(fl0[j - 1] | fl0[j])
            interp.append(True)
        else:
            hs.append(complex("nan")); ses.append(float("nan")); fls.append(set())
            interp.append(True)
    if any(interp):
        print(f"note: {label} sweep is on different frequencies; "
              f"{sum(interp)} point(s) interpolated or out of range")
    return np.array(hs), np.array(ses), fls, interp


def deembed(rows, open_rows=None, ref_rows=None):
    """Adds d_* columns: d = (H - H_open) / (H_ref - H_open), with either term
    optional, and its first-order standard error d_se. The open/ref points'
    measurement problems (headroom, nonlinear, unsettled) are carried over
    with an 'open:' / 'ref:' prefix; their noise is in d_se instead, and
    |d| < 3 d_se adds 'low-snr'. Interpolation adds 'interp'."""
    freqs = [r["freq_hz"] for r in rows]
    n = len(rows)
    h = _complex(rows)
    se = np.array([r.get("se", float("nan")) for r in rows])
    ho, seo = np.zeros(n, complex), np.zeros(n)
    hr, ser = np.ones(n, complex), np.zeros(n)
    extra = [[] for _ in rows]
    interp = [False] * n
    if open_rows:
        ho, seo, fl, ip = _on_grid(open_rows, freqs, "open")
        for i in range(n):
            extra[i] += [f"open:{x}" for x in sorted(fl[i] & CARRY_FLAGS)]
            interp[i] = interp[i] or ip[i]
    if ref_rows:
        hr, ser, fl, ip = _on_grid(ref_rows, freqs, "reference")
        for i in range(n):
            extra[i] += [f"ref:{x}" for x in sorted(fl[i] & CARRY_FLAGS)]
            interp[i] = interp[i] or ip[i]
    den = (hr - ho) if ref_rows else np.ones(n, complex)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = (h - ho) / den
        if ref_rows:
            d_se = np.sqrt(se ** 2 + np.abs(d) ** 2 * ser ** 2
                           + np.abs(1 - d) ** 2 * seo ** 2) / np.abs(den)
        else:
            d_se = np.sqrt(se ** 2 + seo ** 2)
    out = []
    for i, r in enumerate(rows):
        r = dict(r)
        dv = d[i]
        r.update(d_re=dv.real, d_im=dv.imag, d_mag=abs(dv),
                 d_phase_deg=math.degrees(math.atan2(dv.imag, dv.real)),
                 d_se=float(d_se[i]))
        fl = [x for x in r.get("flags", "").split(";") if x and x != "interp"]
        fl += [x for x in extra[i] if x not in fl]
        if interp[i]:
            fl.append("interp")
        if math.isfinite(d_se[i]) and abs(dv) < 3 * d_se[i] and "low-snr" not in fl:
            fl.append("low-snr")
        r["flags"] = ";".join(fl)
        out.append(r)
    return out


def fit_delay(freqs, h, use=None):
    """Time delay (s) from the phase slope, over the points in `use` (all
    finite ones by default). Fits the densely spaced low end first so wraps
    between widely spaced high points unwrap correctly."""
    f = np.asarray(freqs, float)
    h = np.asarray(h, complex)
    ok = np.isfinite(h) & (np.abs(h) > 0)
    if use is not None:
        ok &= np.asarray(use, bool)
    f, h = f[ok], h[ok]
    if f.size < 3:
        return float("nan")
    order = np.argsort(f)
    f, h = f[order], h[order]
    tau = 0.0
    for n in sorted({min(f.size, k) for k in (4, 8, 16, f.size)}):
        resid = np.unwrap(np.angle(h[:n] * np.exp(2j * math.pi * f[:n] * tau)))
        slope = np.polyfit(f[:n], resid, 1)[0]
        tau -= slope / (2 * math.pi)
    return tau


def phase_deg(f, h, tau=0.0):
    """Unwrapped phase in degrees, with delay tau removed, leaving NaN points
    as gaps (np.unwrap would carry one NaN into every later point)."""
    f = np.asarray(f, float)
    h = np.asarray(h, complex)
    ph = np.angle(h * np.exp(2j * math.pi * f * (tau if math.isfinite(tau) else 0.0)))
    ok = np.isfinite(ph)
    ph[ok] = np.unwrap(ph[ok])
    return np.degrees(ph)


def plot_phase(f, h, tau, remove_delay):
    """Phase for the plot. Unwrapping the raw phase fails at the wide high
    end of a log sweep (a delay of ~150 ns turns by more than 180 deg between
    neighbouring points), so unwrap the delay-removed residual and add the
    fitted delay back unless it is meant to be removed."""
    ph = phase_deg(f, h, tau)
    if not remove_delay and math.isfinite(tau):
        ph = ph - 360.0 * np.asarray(f, float) * tau
    return ph


def plot(path, rows, use_d=False, remove_delay=False, show=False):
    try:
        import matplotlib
        if not show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping the plot")
        return None
    order = sorted(range(len(rows)), key=lambda i: rows[i]["freq_hz"])
    rows = [rows[i] for i in order]
    f = np.array([r["freq_hz"] for r in rows])
    h = np.array([(r["d_re"] + 1j * r["d_im"]) if use_d else (r["re"] + 1j * r["im"])
                  for r in rows])
    se = np.array([r.get("d_se" if use_d else "se", float("nan")) for r in rows])
    flagsets = [set(r["flags"].split(";")) - {""} for r in rows]
    bad = np.array([bool(s) for s in flagsets])
    # fit the delay on trustworthy points only (an open sweep's low end can be noise)
    good = np.array([not ({x.split(":", 1)[-1] for x in s} & BAD_FLAGS)
                     for s in flagsets])
    good &= ~(np.abs(h) < 3 * se)
    tau = fit_delay(f, h, good if good.sum() >= 4 else None)
    ph = plot_phase(f, h, tau, remove_delay)
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 20 * np.log10(np.abs(h))
    a1.semilogx(f, db, "o-", ms=3)
    a2.semilogx(f, ph, "o-", ms=3)
    if bad.any():
        a1.semilogx(f[bad], db[bad], "rx", ms=8, label="flagged (see CSV)")
        a2.semilogx(f[bad], ph[bad], "rx", ms=8)
        a1.legend()
    a1.set_ylabel(("de-embedded " if use_d else "") + "|H| (dB)")
    a2.set_ylabel("phase (deg)" + (" minus delay" if remove_delay else ""))
    a2.set_xlabel("frequency (Hz)")
    for a in (a1, a2):
        a.grid(True, which="both", alpha=0.3)
    title = "iza sweep" + (" (de-embedded)" if use_d else "")
    if math.isfinite(tau):
        title += f"   fitted delay {tau * 1e9:.1f} ns"
    a1.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    if show:
        plt.show()
    plt.close(fig)
    return path


# ----------------------------------------------------------- CLI
def _strip_deembedding(rows, meta):
    """Forget a previous de-embedding before --analyze redoes it."""
    for k in ("open", "ref"):
        meta.pop(k, None)
    for r in rows:
        for k in DCOLUMNS:
            r.pop(k, None)
        fl = [x for x in r["flags"].split(";") if x and x not in ("interp", "low-snr")
              and not x.startswith(("open:", "ref:"))]
        # 'low-snr' may come from the old de-embedding: keep it only if the
        # raw point itself qualifies (same test as measure_point)
        se, h = r.get("se", float("nan")), complex(r["re"], r["im"])
        if math.isfinite(se) and math.isfinite(abs(h)) and abs(h) < 3 * se:
            fl.append("low-snr")
        r["flags"] = ";".join(fl)


def _port(text):
    v = int(text)
    if not 1 <= v <= 65535:
        raise argparse.ArgumentTypeError("port must be 1..65535")
    return v


def main(argv=None):
    for s in (sys.stdout, sys.stderr):  # user paths may not fit the console codec
        if hasattr(s, "reconfigure"):
            s.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(
        description="Low-amplitude frequency-response sweep with clipping "
                    "guards and open/reference de-embedding.")
    ap.add_argument("--board", default=DEFAULT_BOARD)
    ap.add_argument("--port", type=_port, default=DATA_PORT, help="data port (UDP)")
    ap.add_argument("--ch", type=int, default=0, help="tone/demod channel 0..3")
    ap.add_argument("--start", type=float, default=500e3, help="Hz")
    ap.add_argument("--stop", type=float, default=40e6, help="Hz (max 50 MHz)")
    ap.add_argument("--points", type=int, default=40)
    ap.add_argument("--amp", type=float, default=5.0,
                    help="tone amplitude, %% of DAC full scale (default 5)")
    ap.add_argument("--min-amp", type=float, default=0.25,
                    help="lowest amplitude the headroom search may use, %%")
    ap.add_argument("--max-peak", type=float, default=0.5,
                    help="max ADC peak, fraction of full scale (default 0.5)")
    ap.add_argument("--settle", type=float, default=0.1, help="s after each change")
    ap.add_argument("--avg", type=float, default=0.2, help="s averaged per point")
    ap.add_argument("--no-linearity", action="store_true",
                    help="skip the half-amplitude re-measurement (2x faster)")
    ap.add_argument("--lin-tol", type=float, default=0.01,
                    help="allowed half-amplitude mismatch (default 0.01 = 1%%)")
    ap.add_argument("--out", help="CSV to write (default sweep_<time>.csv)")
    ap.add_argument("--open", help="open-fixture sweep CSV to subtract")
    ap.add_argument("--ref", help="reference-load sweep CSV to divide by")
    ap.add_argument("--analyze", metavar="CSV",
                    help="re-process a saved sweep offline (no board)")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--show", action="store_true", help="also open the plot window")
    ap.add_argument("--remove-delay", action="store_true",
                    help="plot phase with the fitted delay removed")
    args = ap.parse_args(argv)

    out_ = _safe_log(print)
    err_ = _safe_log(lambda m: print(m, file=sys.stderr))
    rc, rescued, deembed_error = 0, False, None
    try:
        open_rows = load_sweep(args.open, "open")[0] if args.open else None
        ref_rows = load_sweep(args.ref, "reference")[0] if args.ref else None
        if args.analyze:
            if not (open_rows or ref_rows):
                raise SweepError("--analyze needs --open and/or --ref")
            rows, meta = load_sweep(args.analyze, "input")
            _strip_deembedding(rows, meta)
            out = args.out or os.path.splitext(args.analyze)[0] + "_deembedded.csv"
            check_writable(out)
            drops = 0
        else:
            cfg = Config(ch=args.ch, amp_pct=args.amp, min_amp_pct=args.min_amp,
                         max_peak=args.max_peak, settle=args.settle, avg=args.avg,
                         linearity=not args.no_linearity, lin_tol=args.lin_tol,
                         start=args.start, stop=args.stop, points=args.points)
            out = args.out or time.strftime("sweep_%Y%m%d_%H%M%S.csv")
            check_writable(out)
            ctrl = iza_ctrl.IzaCtrl(args.board)
            src = UdpSource(args.port)
            try:
                rows, meta = run_sweep(ctrl, src, cfg, sleep=SLEEP)
            finally:
                src.close()
                ctrl.sock.close()
            drops = src.drops
            meta.update(board=args.board, time=time.strftime("%Y-%m-%d %H:%M:%S"))
            if "aborted" in meta or "restore_failed" in meta:
                rc = 1
    except (SweepError, iza_ctrl.CtrlError, OSError) as e:
        err_(f"error: {e}")
        return 1
    if not rows:
        err_("no points measured")
        return 1
    if open_rows or ref_rows:
        try:
            rows = deembed(rows, open_rows, ref_rows)
            if args.open:
                meta["open"] = args.open
            if args.ref:
                meta["ref"] = args.ref
        except Exception as e:          # keep the raw sweep, report the failure
            deembed_error = e
    out, rescued = save_rows(out, rows, meta)     # one write: raw (+ de-embedded)
    flagged = [r for r in rows if r["flags"]]
    out_(f"wrote {out}: {len(rows)} points, {len(flagged)} flagged"
         + (" (" + ", ".join(sorted({f for r in flagged for f in r['flags'].split(';')}))
            + ")" if flagged else "")
         + (f"; sweep aborted: {meta['aborted']}" if "aborted" in meta else ""))
    if drops:
        out_(f"note: {drops} datagrams were dropped (averages are unaffected, "
             "only shorter)")
    if "restore_failed" in meta:
        err_("WARNING: the board settings were not fully restored (see above)")
    if deembed_error is not None:
        err_(f"error: de-embedding failed ({deembed_error}); the raw sweep was saved")
        rc = max(rc, 1)
    if not args.no_plot:
        try:
            png = plot(os.path.splitext(out)[0] + ".png", rows,
                       use_d=bool((open_rows or ref_rows) and "d_re" in rows[0]),
                       remove_delay=args.remove_delay, show=args.show)
            if png:
                out_(f"wrote {png}")
        except Exception as e:          # the CSV is already safe
            err_(f"error: could not draw the plot ({e})")
            rc = max(rc, 1)
    if rescued:
        rc = 2                          # the requested output was not written
    return rc

if __name__ == "__main__":
    sys.exit(main())
