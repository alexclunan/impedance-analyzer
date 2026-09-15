#!/usr/bin/env python3
"""fir_design.py — design the demod decimation filter: CIC rate + FIR taps.

The signal chain is  ADC (200 MSPS) -> CIC /R -> FIR -> demod output.
The CIC decimation R is programmable and the FIR runs at the CIC output rate:

    R = 1000 -> 200 kHz      R = 4000 ->  50 kHz
    R = 2000 -> 100 kHz      R = 8000 ->  25 kHz

R is restricted to power-of-two multiples of 1000 so the CIC's R^4 gain change
between rates is an exact bit shift (4*log2(R/1000) bits relative to R=1000).

QUICK START
-----------
    from fir_design import make_filter
    f = make_filter(250)                    # pick R/taps/method automatically
    print(f.report())
    f.write_coe("fir.coe"); f.write_config("fir.json")

    f = make_filter(250, rate=8000)         # pin the CIC rate
    f = make_filter(5000, mode="latency")   # minimum group delay
    f = make_filter(250, taps=999, method="kaiser", rate=1000)   # fully explicit

CLI:
    python fir_design.py 250                        # auto everything
    python fir_design.py 5000 --mode latency        # minimum delay
    python fir_design.py 250 --rate 8000 --taps 999 # explicit
    python fir_design.py 250 --coe f.coe --json f.json
    python fir_design.py --sweep                    # table over 20 Hz..10 kHz

`cutoff` means the **-3 dB** point everywhere in the high-level API (make_filter,
the CLI). The low-level design() primitive keeps its original meaning, where
cutoff is the ~-6 dB point of the windowed sinc.

TWO MODES
---------
quality  (default) uses the whole tap frame for the sharpest transition it can
         reach. Group delay is (taps-1)/2 samples regardless of cutoff.
latency  finds the FEWEST taps meeting a selectivity spec (`shape` = f_stop /
         f_3dB) and left-justifies them in the frame, so delay is (M-1)/2. This
         needs the FIR Compiler built NON-symmetric (C_SYMMETRY=0): the block is
         symmetric about its own centre, but not about the frame's.
         Delay is then set by the transition width alone - roughly
         (atten-8)/(28.7*transition_hz) seconds - not by R or by the cutoff.

WHAT LIMITS A DESIGN
--------------------
Resolution: a windowed design needs about
    f_3dB >= 0.79 * fs / taps * (atten-8)/72
so 999 taps reach ~158 Hz at 200 kHz and ~20 Hz at 25 kHz. Asking for less does
not fail - it collapses onto the window main lobe and quietly costs ~20 dB of
stopband. Everything here checks for that rather than trusting the request.

DC gain: quantize() derives the integer gain from the tap count (a fixed 65536
underfills the coefficient word once the taps spread out - 999 taps peak at 75
of +/-32767, a -58 dB quantization floor). Always take the gain and the matching
datapath shift from info["gain_used"] / info["shift"]; they change with the tap
count and the coefficient width.

Phase: taps are exactly symmetric, so group delay is constant and the demod
phase is delayed, never distorted. The delay varies across designs by ~300x
(135 us to 20 ms), so the consumer must subtract the value carried in the config
rather than a hardcoded constant.

CIC droop (N=4, M=1 -> sinc^4) is negligible for narrow cutoffs (<0.001 dB below
1 kHz) but reaches ~0.09 dB across the passband of a 10 kHz cutoff at R=1000;
cic_comp=True adds the inverse-sinc^4 pre-emphasis, flattening that to ~0.001 dB.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np

# ------------------------------------------------------------------ hardware
FS_IN_DEFAULT = 200e6        # ADC / CIC input rate
RATE_DEFAULT  = 1000         # CIC decimation R
RATES         = (1000, 2000, 4000, 8000)   # power-of-two multiples of 1000
FS_DEFAULT    = FS_IN_DEFAULT / RATE_DEFAULT      # 200 kHz
TAPS_DEFAULT  = 999          # odd -> Type-I linear phase
WIDTH         = 16           # signed coefficient width (bits)
CIC_STAGES    = 4
CIC_DIFF      = 1

# HARDCODED to 999, matching the NCOEF parameter hardcoded in
# fir_coeff_loader.v. These two numbers must be equal; nothing checks it at
# build time, so treat them as one constant kept in two languages.
#
# The loader streams exactly NCOEF beats per commit and SATURATES its write
# pointer past the end rather than erroring, so a mismatch is not reported
# anywhere - the board just runs a filter nobody designed. loader_payload()
# pads short frames and refuses long ones for that reason.
LOADER_NCOEF  = 999

# Legacy only: the fixed DC gain the original 127-tap .coe files were built with.
# Pass it explicitly to quantize() only when regenerating one of those.
GAIN_LEGACY_127 = 65536


def fs_for_rate(rate=RATE_DEFAULT, fs_in=FS_IN_DEFAULT):
    """FIR sample rate for a CIC decimation factor."""
    return float(fs_in) / float(rate)


def cic_gain_shift(rate, base=1000):
    """Bit shift of the CIC's R^4 gain relative to `base` (exact for the
    power-of-two rate ladder; that is the whole reason for the ladder)."""
    s = 4 * np.log2(float(rate) / base)
    if abs(s - round(s)) > 1e-9:
        raise ValueError(f"rate {rate} is not a power-of-two multiple of {base}; "
                         "gain normalisation would need a multiplier, not a shift")
    return int(round(s))


def cic_delay_s(rate, stages=CIC_STAGES, diff=CIC_DIFF, fs_in=FS_IN_DEFAULT):
    """CIC group delay in seconds: N(RM-1)/2 input samples."""
    return stages * (rate * diff - 1) / 2.0 / fs_in


def cic_droop_db(f, fs_out, stages=CIC_STAGES):
    """CIC passband droop in dB at output-band frequency f.

    sinc(f/fs_out)^stages. Exact to well under a millidecibel for R >= 1000:
    the true expression sin(pi R M f/fs_in)/(R M sin(pi f/fs_in)) has a
    denominator that is linear to that accuracy at these rates.
    """
    return stages * 20 * np.log10(np.abs(np.sinc(np.asarray(f, float) / fs_out))
                                  + 1e-300)


def resolution_limit(fs, taps, atten_db=80.0):
    """Narrowest -3 dB cutoff this many taps can resolve at this rate."""
    return 0.79 * fs / taps * (atten_db - 8.0) / 72.0


# ------------------------------------------------------------ design methods
def _kaiser_beta(atten_db):
    a = float(atten_db)
    if a > 50:   return 0.1102 * (a - 8.7)
    if a >= 21:  return 0.5842 * (a - 21) ** 0.4 + 0.07886 * (a - 21)
    return 0.0


def design(cutoff_hz, fs=FS_DEFAULT, taps=TAPS_DEFAULT, atten_db=80.0,
           cic_comp=False, cic_stages=CIC_STAGES, cic_diff=CIC_DIFF,
           trans_hz=None):
    """Return `taps` float coefficients (exactly symmetric, unity DC gain).

    Windowed-sinc (Kaiser). `cutoff_hz` is the ~-6 dB point; for a filter
    specified at -3 dB use design_for_f3() or make_filter().

    cutoff_hz : ~-6 dB low-pass cutoff.
    atten_db  : target stopband attenuation (sets the Kaiser window).
    cic_comp  : pre-emphasize the passband by 1/sinc^cic_stages to flatten CIC droop.
    """
    if taps % 2 == 0:
        raise ValueError("use an odd tap count for a Type-I linear-phase low-pass")
    fn = cutoff_hz / fs                      # normalized cutoff (cycles/sample)
    if not 0 < fn < 0.5:
        raise ValueError(f"cutoff {cutoff_hz} Hz must be in (0, fs/2={fs/2:g})")
    n = np.arange(taps) - (taps - 1) / 2.0
    win = np.kaiser(taps, _kaiser_beta(atten_db))

    if not cic_comp:
        h = 2 * fn * np.sinc(2 * fn * n) * win          # windowed-sinc low-pass
    else:
        # frequency-sampling design so we can shape the passband (inverse sinc^N)
        L = 8192
        f = np.linspace(0, 0.5, L // 2 + 1)             # cycles/sample, 0..Nyquist
        Hd = np.zeros_like(f)
        tw = (trans_hz / fs) if trans_hz else max(2.0 / taps, 0.01)
        pb = f <= fn
        with np.errstate(divide="ignore", invalid="ignore"):
            comp = 1.0 / np.sinc(f) ** cic_stages
        Hd[pb] = comp[pb]
        tr = (f > fn) & (f <= fn + tw)                  # raised-cosine transition
        Hd[tr] = comp[tr] * 0.5 * (1 + np.cos(np.pi * (f[tr] - fn) / tw))
        hfull = np.fft.irfft(Hd, L)                     # zero-phase, symmetric about 0
        c = taps // 2
        h = np.concatenate([hfull[-c:], hfull[:c + 1]]) * win

    h = 0.5 * (h + h[::-1])                  # exact symmetry
    return h / h.sum()                       # unity DC gain


def _remez_transition(taps, atten_db, ripple_db, fs):
    """Harris/Rabiner estimate of the transition width remez needs."""
    dp = 10 ** (ripple_db / 20.0) - 1.0
    ds = 10 ** (-atten_db / 20.0)
    a = -20 * np.log10(np.sqrt(dp * ds)) - 13.0
    return a / (14.6 * (taps - 1)) * fs


def design_equiripple(f_pass, f_stop, fs=FS_DEFAULT, taps=TAPS_DEFAULT,
                      atten_db=80.0, ripple_db=0.1):
    """Parks-McClellan equiripple low-pass with the given band edges.

    Type-I symmetric, so linear phase holds exactly. For the same tap count and
    attenuation this reaches a narrower transition than the window design, and
    it lets passband ripple and stopband attenuation be set independently.
    Raises if scipy's Remez exchange fails to converge.
    """
    from scipy.signal import remez
    if taps % 2 == 0:
        raise ValueError("use an odd tap count for a Type-I linear-phase low-pass")
    if not 0 < f_pass < f_stop < fs / 2:
        raise ValueError(f"need 0 < f_pass ({f_pass:g}) < f_stop ({f_stop:g}) "
                         f"< fs/2 ({fs/2:g})")
    dp = 10 ** (ripple_db / 20.0) - 1.0
    ds = 10 ** (-atten_db / 20.0)
    h = remez(taps, [0.0, f_pass, f_stop, 0.5 * fs], [1.0, 0.0],
              weight=[1.0 / dp, 1.0 / ds], fs=fs, grid_density=16, maxiter=50)
    h = 0.5 * (h + h[::-1])
    return h / h.sum()


# ------------------------------------------------- solving for a -3 dB point
def _mag_db(h, f, fs):
    n = np.arange(len(h))
    return 20 * np.log10(np.abs(np.exp(-2j * np.pi * np.outer(f / fs, n)) @ h)
                         + 1e-300)


def _cross(f, db, level):
    """First downward crossing of `level` dB, linearly interpolated."""
    below = np.flatnonzero(db <= level)
    if not below.size or below[0] == 0:
        return float("nan")
    i = below[0]
    f0, f1, d0, d1 = f[i - 1], f[i], db[i - 1], db[i]
    return float(f0 + (level - d0) * (f1 - f0) / (d1 - d0)) if d1 != d0 else float(f1)


def _f3_of(h, fs, fmax, npts=1500):
    f = np.linspace(0.0, fmax, npts)
    return _cross(f, _mag_db(h, f, fs), -3.0)


def _solve(build, target_f3, fs, lo, hi, tol=1e-3, iters=30, npts=1500):
    """Bisect a design parameter so the -3 dB point lands on target_f3.

    Returns None when the target is below the design's floor - the -3 dB point
    saturates once the design collapses onto the window main lobe, which is
    exactly the "too narrow for this tap count" case.
    """
    fmax = 4.0 * target_f3
    f_lo = _f3_of(build(lo), fs, fmax, npts)
    if not np.isfinite(f_lo) or f_lo > target_f3 * (1 + tol):
        return None
    mid = hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f3 = _f3_of(build(mid), fs, fmax, npts)
        if not np.isfinite(f3):
            lo = mid
            continue
        if abs(f3 - target_f3) <= tol * target_f3:
            return mid
        lo, hi = (mid, hi) if f3 < target_f3 else (lo, mid)
    return mid


def design_for_f3(target_f3, fs=FS_DEFAULT, taps=TAPS_DEFAULT, atten_db=80.0,
                  method="kaiser", f_stop=None, ripple_db=0.1, cic_comp=False,
                  fast=False):
    """Taps whose **-3 dB** point lands on target_f3, or None if unreachable.

    method   : "kaiser" or "remez".
    f_stop   : pin the stopband edge (remez only). Used by latency mode, where
               the shape is specified and the tap count is minimised. When None,
               the transition width is chosen to just meet atten_db.
    """
    tol, iters, npts = (5e-3, 18, 900) if fast else (1e-3, 30, 1500)

    if method == "kaiser":
        def build(fc):
            return design(fc, fs, taps, atten_db, cic_comp)
        fc = _solve(build, target_f3, fs, 0.05 * target_f3,
                    min(4.0 * target_f3, 0.45 * fs), tol, iters, npts)
        return None if fc is None else build(fc)

    if method != "remez":
        raise ValueError(f"unknown method {method!r} (use 'kaiser' or 'remez')")

    if f_stop is not None:
        def build(fp):
            return design_equiripple(fp, f_stop, fs, taps, atten_db, ripple_db)
        try:
            fp = _solve(build, target_f3, fs, 0.05 * target_f3, 0.99 * f_stop,
                        tol, iters, npts)
            return None if fp is None else build(fp)
        except Exception:
            return None

    # No pinned stopband: start from the Harris width estimate and correct it
    # against the measured attenuation. For fixed taps the achievable
    # attenuation is nearly linear in the transition width, so
    #   dw <- dw * (A_target-13)/(A_achieved-13)
    # converges in two or three passes, and converges from below - giving the
    # NARROWEST transition that meets the target rather than merely one that does.
    dw = _remez_transition(taps, atten_db, ripple_db, fs)
    best = None
    for _ in range(4):
        width = dw

        def build(fp):
            return design_equiripple(fp, min(fp + width, 0.49 * fs), fs, taps,
                                     atten_db, ripple_db)
        try:
            fp = _solve(build, target_f3, fs, 0.05 * target_f3,
                        min(4.0 * target_f3, 0.45 * fs - width), tol, iters, npts)
            if fp is None:
                return None
            h = build(fp)
        except Exception:
            return None
        got = measure(h, fs)["stopband_db"]
        if got <= -atten_db:
            return h
        best = h
        scale = (atten_db - 13.0) / max(-got - 13.0, 1.0)
        if not np.isfinite(scale) or scale <= 1.0:
            break
        dw *= min(scale, 2.0)
    return best


# ----------------------------------------------------------- quantization
def max_gain(h, width=WIDTH):
    """Largest power-of-two DC gain whose peak tap still fits `width` bits.

    The peak tap - not the tap sum - is what the coefficient word must hold, and
    peak/sum shrinks as the taps spread out (~0.018 at 127 taps, ~0.0023 at 999).
    A fixed gain therefore underfills the word as the tap count grows. Power of
    two keeps the downstream normalization a shift rather than a divide.
    """
    lim = (1 << (width - 1)) - 1
    peak = float(np.abs(h).max())
    if peak <= 0:
        raise ValueError("all-zero coefficients")
    return 1 << int(np.floor(np.log2(lim / peak)))


def quantize(h, width=WIDTH, gain=None):
    """Scale unity-gain float taps to signed `width`-bit integers, keeping exact
    symmetry and an exact power-of-two DC gain. Returns (ints, info).

    gain=None (the default) picks the largest power of two that fits the word.
    An explicit gain that would clip is reduced to the next lower power of two,
    never to an arbitrary value, so info["shift"] stays meaningful.

    info["shift"] is log2(DC gain): the right-shift the datapath must apply to
    undo this filter's DC gain. Carry it with the coefficients - it changes
    whenever the tap count or the coefficient width changes.
    """
    lim = (1 << (width - 1)) - 1
    fits = max_gain(h, width)
    requested = gain
    if gain is None:
        eff = fits
    else:
        eff = 1 << int(np.floor(np.log2(gain)))     # snap to a power of two
        if eff > fits:
            eff = fits                              # back off in whole bits
    q = np.round(np.asarray(h, float) * eff).astype(np.int64)
    c = len(q) // 2
    q[c + 1:] = q[:c][::-1]                          # exact symmetry
    # Rounding leaves the sum a few counts off (65535 for a nominal 65536), a
    # small DC gain error for a shift-normalised datapath. The centre tap is its
    # own mirror, so it can absorb the residual without breaking symmetry.
    q[c] += eff - int(q.sum())
    q = np.clip(q, -lim - 1, lim)
    info = {"dc_sum": int(q.sum()), "peak": int(np.abs(q).max()),
            "gain_used": int(eff), "shift": int(np.log2(eff)),
            "clipped": requested is not None and eff < (1 << int(np.floor(
                np.log2(requested)))),
            "symmetric": bool(np.array_equal(q, q[::-1]))}
    return q.astype(np.int32), info


# ------------------------------------------------------------- measurement
def measure(h, fs=FS_DEFAULT, rate=None, npts=1 << 13):
    """Measured performance of a tap vector. Returns a metrics dict.

    Works on float taps or on integers straight out of a .coe (it normalises),
    and on a left-justified frame (the delay comes from the coefficients, not
    from an assumed (N-1)/2).
    """
    h = np.asarray(h, float)
    if h.sum() != 0:
        h = h / h.sum()
    f = np.linspace(0.0, fs / 2, npts)
    db = _mag_db(h, f, fs)
    f3, f6, f60 = (_cross(f, db, -3.0), _cross(f, db, -6.0), _cross(f, db, -60.0))

    # true stopband edge = first null past the transition, not "where it drops
    # below X dB" (which would just report X back)
    start = int(np.searchsorted(f, f60 if np.isfinite(f60) else fs / 8))
    seg = db[start:]
    dips = np.flatnonzero((seg[1:-1] < seg[:-2]) & (seg[1:-1] <= seg[2:])) + 1
    if dips.size:
        edge = start + int(dips[0])
        sb_edge, sb_worst = float(f[edge]), float(db[edge:].max())
    else:
        sb_edge, sb_worst = float("nan"), float(seg.max())

    # group delay from the coefficients themselves
    n = np.arange(len(h))
    E = np.exp(-2j * np.pi * np.outer(f[:64] / fs, n))
    with np.errstate(divide="ignore", invalid="ignore"):
        gd = np.real((E @ (n * h)) / (E @ h))
    gd_samples = float(gd[0])

    pb = f <= (0.5 * f3 if np.isfinite(f3) else fs / 8)
    first, last, span = active_span(h)
    out = {
        "f3_hz": f3, "f6_hz": f6, "f60_hz": f60,
        "transition_hz": f60 - f3 if np.isfinite(f60) else float("nan"),
        "shape": f60 / f3 if np.isfinite(f60) and f3 else float("nan"),
        "ripple_db": float(db[pb].max() - db[pb].min()),
        "stopband_db": sb_worst, "stopband_edge_hz": sb_edge,
        "enbw_hz": fs * float(np.sum(h ** 2)) / float(np.sum(h)) ** 2 / 2.0,
        "group_delay_samples": gd_samples,
        "group_delay_s": gd_samples / fs,
        "taps": len(h), "active_taps": span, "active_offset": first,
        "symmetric": bool(np.allclose(h, h[::-1])),
    }
    if rate is not None:
        out["cic_droop_db"] = (float(cic_droop_db(f3, fs)) if np.isfinite(f3)
                               else float("nan"))
        out["cic_delay_s"] = cic_delay_s(rate)
        out["total_delay_s"] = out["group_delay_s"] + out["cic_delay_s"]
    return out


# ---------------------------------------------------------------- selection
def _accept(m, target, atten, droop_max, fs, f3_tol=0.03):
    """Does a candidate genuinely meet the spec? Returns (ok, reason)."""
    if not np.isfinite(m["f3_hz"]):
        return False, "no -3 dB point"
    if abs(m["f3_hz"] - target) > f3_tol * target:
        return False, f"-3 dB off target ({m['f3_hz']:.4g} vs {target:g} Hz)"
    if not m["symmetric"]:
        return False, "not symmetric (would break linear phase)"
    # 6 dB of slack: at the tap-count wall the stopband collapses ~20 dB, which
    # is exactly the failure this guard exists to catch.
    if m["stopband_db"] > -(atten - 6.0):
        return False, f"stopband only {m['stopband_db']:.1f} dB (want {-atten:g})"
    if m.get("cic_droop_db", 0.0) < -droop_max:
        return False, f"CIC droop {m['cic_droop_db']:.2f} dB at the cutoff"
    if np.isfinite(m["f60_hz"]) and m["f60_hz"] > 0.45 * fs:
        return False, "transition runs into Nyquist"
    return True, "ok"


def _min_taps(target, fs, atten, f_stop, method, tmax=TAPS_DEFAULT, tmin=11):
    """Fewest odd taps meeting the shape spec, or None if tmax cannot.

    Feasibility is monotone in the tap count at fixed band edges, so this
    bisects. The equiripple search starts from the Kaiser answer (a sound upper
    bound) rather than bisecting the expensive method over the whole range.
    """
    def fits(n, fast=True):
        h = design_for_f3(target, fs, int(n) | 1, atten, method, f_stop=f_stop,
                          fast=fast)
        if h is None:
            return False
        m = measure(h, fs)
        if not np.isfinite(m["f3_hz"]) or abs(m["f3_hz"] - target) > 0.03 * target:
            return False
        f = np.linspace(f_stop, fs / 2, 1 << 11)
        return bool(_mag_db(h, f, fs).max() <= -atten)

    if method == "remez":
        hi = _min_taps(target, fs, atten, f_stop, "kaiser", tmax, tmin)
        if hi is None:
            return None
    else:
        if not fits(tmax):
            return None
        hi = tmax
    lo = tmin
    while lo < hi:
        mid = ((lo + hi) // 2) | 1
        if mid >= hi:
            break
        if fits(mid):
            hi = mid
        else:
            lo = mid + 2
    # bisection probes are deliberately cheap; confirm at full precision
    for n in range(hi, min(hi + 8, tmax) + 1, 2):
        if fits(n, fast=False):
            return n
    return hi


# -------------------------------------------------------------- the result
@dataclass
class Filter:
    """A designed filter plus everything the loader and the PC need."""
    cutoff_hz: float
    rate: int
    fs: float
    taps_float: np.ndarray
    ints: np.ndarray
    info: dict
    metrics: dict
    method: str
    mode: str
    atten_db: float
    frame: int = TAPS_DEFAULT
    shape: float = field(default=float("nan"))

    # -- placement -----------------------------------------------------------
    @property
    def left_justified(self):
        """True when a short block sits at the head of a longer frame - which is
        what makes the delay (M-1)/2 rather than the frame's (N-1)/2, and which
        requires the IP built with C_SYMMETRY=0."""
        return len(self.ints) < self.frame

    def framed_ints(self):
        """Coefficients padded to the full tap frame, ready to reload."""
        if not self.left_justified:
            return self.ints
        return np.concatenate(
            [self.ints, np.zeros(self.frame - len(self.ints), self.ints.dtype)])

    def reload_values(self, ncoef=None):
        """The exact vector to push at REG3 - always the full frame.

        The loader streams a fixed NCOEF values per commit, so this is padded to
        that length rather than trimmed to the design's active taps.
        """
        return loader_payload(reload_set(self.framed_ints()), ncoef)

    # -- outputs -------------------------------------------------------------
    def config(self):
        """The loader payload. Everything here changes between designs; none of
        it is safe to hardcode - least of all the delay, which the PC must
        subtract from the measured phase."""
        m = self.metrics
        return {
            "cic_rate": int(self.rate),
            "fs_out_hz": float(self.fs),
            "cic_gain_shift_vs_r1000": cic_gain_shift(self.rate),
            "fir_tap_frame": int(self.frame),
            "fir_taps_loaded": int(len(self.ints)),
            "fir_placement": ("left-justified, trailing zeros (requires "
                              "C_SYMMETRY=0)" if self.left_justified
                              else "full frame, symmetric fold OK"),
            "fir_coeff_width": WIDTH,
            "fir_reload_values": len(self.reload_values()),
            "fir_dc_gain": int(self.info["gain_used"]),
            "fir_output_shift": int(self.info["shift"]),
            "method": self.method,
            "mode": self.mode,
            "atten_db": float(self.atten_db),
            "f3_hz": round(float(m["f3_hz"]), 4),
            "group_delay_us": round(m["group_delay_s"] * 1e6, 2),
            "total_delay_us": round(m.get("total_delay_s", m["group_delay_s"])
                                    * 1e6, 2),
        }

    def coe_header(self):
        m = self.metrics
        place = (f"{len(self.ints)} active taps left-justified in a {self.frame}-tap "
                 f"frame, trailing zeros (requires C_SYMMETRY=0)"
                 if self.left_justified
                 else f"{self.frame} taps, symmetric about the frame centre")
        return (f"CIC R={self.rate} (fs_out={self.fs:g} Hz) + FIR\n{place}\n"
                f"-3 dB={m['f3_hz']:.4g} Hz  method={self.method}  "
                f"mode={self.mode}  atten={self.atten_db:g} dB\n"
                f"group delay {m['group_delay_samples']:.0f} samples = "
                f"{m['group_delay_s']*1e6:.1f} us\n"
                f"DC gain {self.info['dc_sum']} = 2^{self.info['shift']} "
                f"-> right-shift {self.info['shift']} bits")

    def write_coe(self, path):
        write_coe(path, self.framed_ints(), WIDTH, self.coe_header())
        return path

    def write_config(self, path):
        with open(path, "w") as fp:
            json.dump(self.config(), fp, indent=2)
        return path

    def report(self):
        m, i = self.metrics, self.info
        L = [
            f"  mode / method   : {self.mode} / {self.method}",
            f"  CIC             : R={self.rate}  fs_out={self.fs:g} Hz"
            f"  (gain shift vs R=1000: {cic_gain_shift(self.rate)} bits)",
            f"  target -3 dB    : {self.cutoff_hz:g} Hz",
            f"  achieved -3 dB  : {m['f3_hz']:.4g} Hz   -60 dB {m['f60_hz']:.4g} Hz",
            f"  transition      : {m['transition_hz']:.4g} Hz"
            f"  (shape {m['shape']:.2f}:1)",
            f"  passband ripple : {m['ripple_db']:.5f} dB (DC..0.5*f3)",
            f"  stopband        : {m['stopband_db']:.1f} dB from "
            f"{m['stopband_edge_hz']:.4g} Hz  (target {-self.atten_db:g})",
            f"  ENBW            : {m['enbw_hz']:.4g} Hz",
            f"  CIC droop at f3 : {m.get('cic_droop_db', float('nan')):.5f} dB",
            f"  taps            : {len(self.ints)} of {self.frame}"
            + ("   LEFT-JUSTIFIED - needs C_SYMMETRY=0" if self.left_justified
               else "   full frame, symmetric fold OK"),
            f"  group delay     : {m['group_delay_samples']:.0f} samples = "
            f"{m['group_delay_s']*1e6:.1f} us (constant - linear phase)",
            f"  total delay     : {m.get('total_delay_s', m['group_delay_s'])*1e6:.1f}"
            f" us  (CIC {m.get('cic_delay_s', 0)*1e6:.1f} us + FIR)",
            f"  coefficients    : peak {i['peak']} of +/-{(1 << (WIDTH-1))-1},"
            f"  DC sum {i['dc_sum']} = 2^{i['shift']}",
            f"  datapath shift  : {i['shift']} bits",
            f"  reload          : {len(self.reload_values())} values"
            f" ({'full set' if self.left_justified else 'symmetric fold'})",
        ]
        return "\n".join(L)


# ----------------------------------------------------------- the entry point
def make_filter(cutoff_hz, rate=None, taps=None, method=None, mode="quality",
                atten_db=80.0, shape=3.0, width=WIDTH, gain=None,
                cic_comp=False, droop_max=0.5, frame=TAPS_DEFAULT,
                rates=RATES, fs_in=FS_IN_DEFAULT):
    """Design one filter for a **-3 dB** cutoff. Returns a Filter, or raises.

    Anything left as None is chosen for you:
      rate   - the lowest decimation (so the lowest latency) that meets the spec
      taps   - `frame` in quality mode; the fewest that meet `shape` in latency
      method - whichever of kaiser/remez gives the narrower transition

    mode="latency" minimises group delay by shrinking the tap count against the
    `shape` (f_stop/f_3dB) selectivity spec, then left-justifying the block. It
    is NOT universally faster: it minimises delay subject to the shape you ask
    for, so a demanding shape at a low cutoff can cost more delay than quality
    mode. Loosen `shape` to buy the delay back.
    """
    if mode not in ("quality", "latency"):
        raise ValueError(f"mode must be 'quality' or 'latency', not {mode!r}")
    methods = (method,) if method else ("kaiser", "remez")
    candidates = []

    for r in ([rate] if rate else rates):
        fs = fs_for_rate(r, fs_in)
        if cutoff_hz >= 0.45 * fs:
            continue
        f_stop = shape * cutoff_hz
        if mode == "latency" and f_stop >= 0.45 * fs:
            continue
        for meth in methods:
            if mode == "latency":
                n = (taps if taps else
                     _min_taps(cutoff_hz, fs, atten_db, f_stop, meth, frame))
                if n is None:
                    continue
                h = design_for_f3(cutoff_hz, fs, n, atten_db, meth,
                                  f_stop=f_stop if meth == "remez" else None,
                                  cic_comp=cic_comp)
            else:
                n = taps or frame
                h = design_for_f3(cutoff_hz, fs, n, atten_db, meth,
                                  cic_comp=cic_comp)
            if h is None:
                continue
            ints, info = quantize(h, width, gain)
            m = measure(ints, fs, r)
            ok, why = _accept(m, cutoff_hz, atten_db, droop_max, fs)
            if not ok:
                continue
            candidates.append(Filter(cutoff_hz, r, fs, h, ints, info, m, meth,
                                     mode, atten_db, frame, shape))
        # rates are tried ascending and lower R is lower latency, so once a rate
        # works in quality mode nothing larger can win
        if candidates and mode == "quality" and rate is None:
            break

    if not candidates:
        floor = resolution_limit(fs_for_rate(max(rates), fs_in), taps or frame,
                                 atten_db)
        raise ValueError(
            f"no design meets a {cutoff_hz:g} Hz -3 dB cutoff at {atten_db:g} dB"
            + (f" with shape {shape:g}:1" if mode == "latency" else "")
            + f".\n  The narrowest {taps or frame} taps resolve is ~{floor:.4g} Hz "
              f"(at R={max(rates)}).\n  Relax --atten, widen --shape, or raise "
              f"the cutoff.")

    key = ((lambda c: (c.metrics["total_delay_s"], c.rate)) if mode == "latency"
           else (lambda c: (c.rate, c.metrics["transition_hz"])))
    return min(candidates, key=key)


# ---------------------------------------------------------------------- I/O
def write_coe(path, ints, width=WIDTH, header=""):
    """Write a FIR-Compiler .coe (Radix=16, two's-complement hex)."""
    mask = (1 << width) - 1
    hexw = (width + 3) // 4
    lines = ["; " + l for l in header.splitlines()] if header else []
    lines += ["Radix = 16;", f"Coefficient_Width = {width};", "CoefData ="]
    body = [f"{int(v) & mask:0{hexw}x}" for v in ints]
    with open(path, "w") as fp:
        fp.write("\n".join(lines) + "\n" + ",\n".join(body) + ";\n")


def read_coe(path):
    """Parse a Xilinx FIR .coe -> (list[int] signed coefficients, width_bits).

    Honors `Radix` and `Coefficient_Width`; interprets values as two's
    complement of that width."""
    radix, width, vals, in_data = 16, WIDTH, [], False
    txt = open(path).read()
    tokens = []
    for line in txt.splitlines():
        s = line.split(";")[0].strip() if line.strip().startswith(";") else line
        low = s.lower()
        if low.startswith("radix"):
            radix = int(s.split("=")[1].strip().rstrip(";"))
        elif low.startswith("coefficient_width"):
            width = int(s.split("=")[1].strip().rstrip(";"))
        elif "coefdata" in low:
            in_data = True
            tokens.append(s.split("=", 1)[1] if "=" in s else "")
        elif in_data:
            tokens.append(s)
    blob = " ".join(tokens).replace(";", " ")
    lim = 1 << width
    for tok in blob.replace(",", " ").split():
        v = int(tok, radix)
        vals.append(v - lim if v >= (lim >> 1) else v)
    if not vals:
        raise ValueError(f"no CoefData found in {path}")
    return vals, width


def reload_set(taps, symmetric=False):
    """Return the coefficient set to stream into the FIR Compiler reload port.

    Defaults to the FULL set. The PL loader (fir_coeff_loader) streams exactly
    its NCOEF parameter on commit and its write pointer SATURATES on overflow
    (`if (wr_ptr != NCOEF-1) wr_ptr <= wr_ptr + 1`), so a mismatched length is
    not an error on the board - it quietly loads the wrong filter. Send exactly
    `loader_payload()` worth of values.

    symmetric=True halves the vector for a folded (C_SYMMETRY=1) build. That is
    the legacy 127-tap configuration; do not use it for a left-justified latency
    design, which is symmetric about its own centre but not about the frame's -
    halving it would reload a different filter entirely.

    NOTE: confirm the exact reload ORDER against PG149 for your IP options -
    this returns ascending index order (the common case).
    """
    taps = [int(t) for t in taps]
    n = len(taps)
    if symmetric:
        if taps != taps[::-1]:
            raise ValueError(
                "symmetric reload requested but the coefficients are not "
                "symmetric about the frame centre (a left-justified design "
                "needs the full set and C_SYMMETRY=0)")
        return taps[:(n + 1) // 2]
    return taps


def loader_payload(taps, ncoef=None, width=WIDTH):
    """Exactly the value sequence to push at REG3, or raise saying why not.

    The loader has a fixed NCOEF-deep buffer and always streams NCOEF values on
    commit, so a short push leaves stale coefficients in the tail and a long one
    is silently truncated. This pads a short frame with zeros (harmless - the
    trailing taps of a left-justified design are zero anyway) and refuses a long
    one rather than letting the board load something the caller did not design.
    """
    ncoef = LOADER_NCOEF if ncoef is None else int(ncoef)
    vals = [int(t) for t in taps]
    lim = 1 << (width - 1)
    for v in vals:
        if not -lim <= v <= lim - 1:
            raise ValueError(f"coefficient {v} does not fit signed {width}-bit")
    if len(vals) > ncoef:
        raise ValueError(
            f"{len(vals)} coefficients but the loader holds {ncoef}; it would "
            f"silently keep only the first {ncoef}. Rebuild fir_coeff_loader "
            f"with NCOEF={len(vals)}, or design within the current frame.")
    return vals + [0] * (ncoef - len(vals))


def active_span(taps):
    """(first, last, length) of the non-zero run - the filter inside the frame."""
    nz = np.flatnonzero(np.asarray(taps))
    if not nz.size:
        raise ValueError("all-zero coefficients")
    return int(nz[0]), int(nz[-1]), int(nz[-1] - nz[0] + 1)


# ------------------------------------------------------- back-compat helper
def response(ints, fs=FS_DEFAULT, gain=None, npts=8192, cic_stages=CIC_STAGES):
    """Frequency response of a quantized filter (and CIC x FIR). Returns dict.

    Kept for callers that predate measure(). gain=None normalises by the actual
    tap sum - do not default it to a constant, since quantize() derives the DC
    gain from the tap count (2^23 taps read against a 2^16 assumption is a 42 dB
    offset).
    """
    ints = np.asarray(ints)
    h = ints.astype(np.float64) / (float(ints.sum()) if gain is None else gain)
    H = np.fft.rfft(h, npts)
    f = np.fft.rfftfreq(npts, 1 / fs)
    mag = 20 * np.log10(np.abs(H) + 1e-12)
    cic = cic_droop_db(f, fs, cic_stages)
    return {"f": f, "fir_db": mag, "cic_db": cic, "total_db": mag + cic}


# ---------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(
        description="Design the CIC+FIR demod decimation filter.",
        epilog="cutoff is the -3 dB point. With no --rate/--taps/--method, all "
               "three are chosen for you.")
    ap.add_argument("cutoff", type=float, nargs="?",
                    help="-3 dB cutoff in Hz (20 .. 10000)")
    ap.add_argument("--mode", choices=("quality", "latency"), default="quality",
                    help="quality: sharpest that fits the frame (default). "
                         "latency: fewest taps meeting --shape, minimum delay")
    ap.add_argument("--shape", type=float, default=3.0,
                    help="latency mode: required f_stop/f_3dB ratio (default 3)")
    ap.add_argument("--rate", type=int, default=None, choices=RATES,
                    help="pin the CIC decimation R (default: chosen)")
    ap.add_argument("--taps", type=int, default=None,
                    help=f"pin the tap count, odd (default: chosen, frame {TAPS_DEFAULT})")
    ap.add_argument("--method", choices=("kaiser", "remez"), default=None,
                    help="pin the design method (default: better of the two)")
    ap.add_argument("--atten", type=float, default=80.0,
                    help="stopband attenuation target in dB (default 80)")
    ap.add_argument("--frame", type=int, default=TAPS_DEFAULT,
                    help=f"FIR Compiler tap frame (default {TAPS_DEFAULT})")
    ap.add_argument("--width", type=int, default=WIDTH,
                    help=f"coefficient width in bits (default {WIDTH})")
    ap.add_argument("--gain", type=int, default=None,
                    help="pin the integer DC gain (default: auto power of two)")
    ap.add_argument("--cic-comp", action="store_true",
                    help="pre-emphasize to flatten CIC droop (only worth it "
                         "above ~1 kHz)")
    ap.add_argument("--droop-max", type=float, default=0.5,
                    help="max tolerated CIC droop at the cutoff in dB")
    ap.add_argument("--coe", default=None, help="write the .coe here")
    ap.add_argument("--json", default=None, help="write the loader config here")
    ap.add_argument("--sweep", action="store_true",
                    help="table of designs across 20 Hz .. 10 kHz")
    ap.add_argument("--plot", action="store_true", help="show the response")
    a = ap.parse_args()

    common = dict(mode=a.mode, shape=a.shape, atten_db=a.atten, frame=a.frame,
                  width=a.width, gain=a.gain, cic_comp=a.cic_comp,
                  droop_max=a.droop_max, rate=a.rate, taps=a.taps,
                  method=a.method)

    if a.sweep:
        print(f"{'target':>8} {'R':>6} {'fs_out':>9} {'method':>7} {'-3 dB':>10} "
              f"{'trans':>10} {'stop':>8} {'delay':>10} {'taps':>6} {'shift':>6}")
        for t in (20, 30, 50, 80, 100, 200, 500, 1000, 2000, 5000, 10000):
            try:
                f = make_filter(t, **common)
            except ValueError:
                print(f"{t:8g} {'-':>6} {'-':>9} {'none':>7}   no design meets spec")
                continue
            m = f.metrics
            print(f"{t:8g} {f.rate:6d} {f.fs/1e3:8.0f}k {f.method:>7} "
                  f"{m['f3_hz']:10.4g} {m['transition_hz']:10.4g} "
                  f"{m['stopband_db']:8.1f} {m['total_delay_s']*1e3:9.3f}m "
                  f"{len(f.ints):6d} {f.info['shift']:6d}")
        return

    if a.cutoff is None:
        ap.error("give a -3 dB cutoff in Hz, or --sweep")

    try:
        f = make_filter(a.cutoff, **common)
    except ValueError as e:
        raise SystemExit(str(e))

    print(f.report())
    print("\n  loader config:")
    for k, v in f.config().items():
        print(f"    {k:28s} {v}")

    if a.coe:
        print(f"\n  wrote {f.write_coe(a.coe)}")
    if a.json:
        print(f"  wrote {f.write_config(a.json)}")

    if a.plot:
        import matplotlib.pyplot as plt
        r = response(f.framed_ints(), f.fs)
        plt.figure(figsize=(9, 5))
        plt.plot(r["f"], r["fir_db"], label="FIR")
        plt.plot(r["f"], r["cic_db"], "--", label=f"CIC (sinc^{CIC_STAGES})")
        plt.plot(r["f"], r["total_db"], label="CIC x FIR")
        plt.axvline(f.metrics["f3_hz"], color="k", lw=.5, ls=":")
        plt.ylim(-120, 5)
        plt.xlim(0, min(f.fs / 2, 20 * f.metrics["f3_hz"]))
        plt.xlabel("Hz"); plt.ylabel("dB"); plt.grid(alpha=.3); plt.legend()
        plt.title(f"{len(f.ints)}-tap {f.method} @ {f.fs/1e3:g} kSPS, "
                  f"-3 dB {f.metrics['f3_hz']:.4g} Hz")
        plt.tight_layout(); plt.show()


if __name__ == "__main__":
    main()
