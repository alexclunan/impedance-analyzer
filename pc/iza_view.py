#!/usr/bin/env python3
"""
iza_view.py — offline look at an int16 lab-data file before streaming it.

Loads a `*_adc_int16.bin` from export_zbin_magnitude.py, plots the magnitude
envelope over time, and (if present) prints the JSON metadata so you can see
the real physical magnitude range and native sample rate. Optionally overlays
the resampled-to-board-rate version to sanity-check the interpolation the
sender will do.

Usage:
  python iza_view.py Freq1_adc_int16.bin
  python iza_view.py Freq1_adc_int16.bin --rate 14391 --zoom-ms 50
  python iza_view.py Freq1_adc_int16.bin --board-rate 312500   # show resample
"""

import argparse
import json
import os
import sys

import numpy as np
import matplotlib.pyplot as plt


def load_meta(path):
    for cand in (path + ".json", os.path.splitext(path)[0] + ".json"):
        if os.path.exists(cand):
            try:
                return json.load(open(cand)), cand
            except Exception:
                return None, cand
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--rate", type=float, default=0.0,
                    help="native sample rate Hz (default: from JSON, else 14000)")
    ap.add_argument("--zoom-ms", type=float, default=50.0,
                    help="length of the zoomed lower panel in milliseconds")
    ap.add_argument("--board-rate", type=float, default=0.0,
                    help="if set, overlay the resample-to-this-rate version")
    ap.add_argument("--save", help="write the figure to a PNG instead of showing")
    args = ap.parse_args()

    data = np.fromfile(args.file, dtype="<i2").astype(np.float64)
    if data.size == 0:
        sys.exit(f"empty file: {args.file}")

    meta, jpath = load_meta(args.file)
    rate = args.rate
    if not rate and meta:
        rate = meta.get("zi_meta", {}).get("estimated_sample_rate_hz") or 0.0
    if not rate:
        rate = 14000.0
        print("no rate given/found; assuming 14000 Hz")

    dur = data.size / rate
    t = np.arange(data.size) / rate

    print(f"file        : {args.file}")
    print(f"samples     : {data.size}")
    print(f"sample rate : {rate:.3f} Hz")
    print(f"duration    : {dur:.2f} s")
    print(f"int16 stats : min {data.min():.0f}  max {data.max():.0f}  "
          f"mean {data.mean():.1f}  std {data.std():.1f}")
    if meta:
        sc = meta.get("scaling", {})
        if sc:
            print(f"phys magnitude (pre-int16): min {sc.get('mag_min')}  "
                  f"max {sc.get('mag_max')}  mean {sc.get('mag_mean')}")
        print(f"(metadata: {jpath})")

    nrows = 2
    fig, axes = plt.subplots(nrows, 1, figsize=(11, 7))
    fig.suptitle(f"{os.path.basename(args.file)} — {data.size} samples, "
                 f"{rate:.0f} Hz, {dur:.1f} s")

    axes[0].plot(t, data, lw=0.4)
    axes[0].set_title("full magnitude envelope")
    axes[0].set_xlabel("time (s)")
    axes[0].set_ylabel("int16")
    axes[0].grid(alpha=0.3)

    zoom_n = max(2, int(args.zoom_ms * 1e-3 * rate))
    zoom_n = min(zoom_n, data.size)
    axes[1].plot(t[:zoom_n], data[:zoom_n], lw=0.8, label=f"native {rate:.0f} Hz")
    if args.board_rate:
        try:
            from fractions import Fraction
            from scipy.signal import resample_poly
            frac = Fraction(args.board_rate / rate).limit_denominator(2000)
            seg = data[:zoom_n]
            up_seg = resample_poly(seg, frac.numerator, frac.denominator)
            tb = np.arange(up_seg.size) / args.board_rate
            axes[1].plot(tb, up_seg, lw=0.6, alpha=0.7,
                         label=f"resampled {args.board_rate:.0f} Hz")
        except ImportError:
            print("scipy not available — skipping resample overlay")
    axes[1].set_title(f"first {args.zoom_ms:.0f} ms (zoom)")
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("int16")
    axes[1].grid(alpha=0.3)
    axes[1].legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    if args.save:
        fig.savefig(args.save, dpi=110)
        print(f"saved figure to {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
