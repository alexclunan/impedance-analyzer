#!/usr/bin/env python3
"""
iza_validate.py — offline check of a capture.bin from iza_receiver.py.

Payload values are validated as a recovered waveform (they pass through the
demod pipeline), not byte-for-byte:

  * dominant frequency of a channel's `signal` column == --msg-freq
  * timestamp column strictly increasing, uniform spacing

The record layout is read from the <capture>.json sidecar written by
iza_receiver (chan_mask/stride_words); override with --chan-mask. --channel
selects which demod channel to validate (default: the lowest enabled).

Usage:
  python iza_validate.py capture.bin --msg-freq 100 --sample-rate 14000 [--plot]
"""

import argparse
import json
import os
import sys

import numpy as np

import iza_packet as izp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--msg-freq", type=float, default=100.0)
    ap.add_argument("--sample-rate", type=float, default=14000.0)
    ap.add_argument("--pl-clk", type=float, default=izp.PL_CLK_HZ)
    ap.add_argument("--chan-mask", type=lambda s: int(s, 0), default=None,
                    help="override the layout (default: read <capture>.json)")
    ap.add_argument("--channel", type=int, default=None,
                    help="demod channel to validate (default: lowest enabled)")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    chan_mask = args.chan_mask
    if chan_mask is None:
        side = args.capture + ".json"
        if not os.path.exists(side):
            side = os.path.splitext(args.capture)[0] + ".json"
        if os.path.exists(side):
            chan_mask = json.load(open(side))["chan_mask"]
        else:
            chan_mask = 0x01   # fall back to single ch0
            print("no layout sidecar; assuming chan_mask=0x01 (ch0)")

    demod = izp.demod_list(chan_mask)
    if not demod:
        sys.exit(f"chan_mask 0x{chan_mask:02x} has no demod channels")
    ch = args.channel if args.channel is not None else demod[0]
    if ch not in demod:
        sys.exit(f"channel {ch} not in mask 0x{chan_mask:02x} (has {demod})")

    payload = open(args.capture, "rb").read()
    rec = izp.deinterleave(payload, chan_mask)
    if rec is None or rec["n"] < 1024:
        sys.exit(f"only {rec['n'] if rec else 0} records — capture more data")
    print(f"{rec['n']} records loaded  (chan_mask=0x{chan_mask:02x}, "
          f"validating ch{ch})")

    ts = rec["ts"].astype(np.int64)
    dt = np.diff(ts)
    expected_dt = args.pl_clk / args.sample_rate
    contiguous = dt[(dt > 0) & (dt < 2 * expected_dt)]
    print(f"timestamp deltas: mean {contiguous.mean():.2f}, "
          f"expected {expected_dt:.2f}, "
          f"min {contiguous.min()}, max {contiguous.max()}")
    ts_ok = abs(contiguous.mean() - expected_dt) < 2 and \
        (contiguous.max() - contiguous.min()) <= 2
    mono_ok = bool(np.all(dt > 0))

    sig = rec["sig"][ch].astype(np.float64)
    # detrend: remove DC + slow baseline wander so the FFT shows the tone
    sig = sig - np.polyval(np.polyfit(np.arange(len(sig)), sig, 1),
                           np.arange(len(sig)))
    n = len(sig)
    spec = np.abs(np.fft.rfft(sig * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / args.sample_rate)
    spec[0] = 0

    lo_cut = max(2.0, args.msg_freq / 20.0)
    band = freqs >= lo_cut
    f_peak = freqs[band][int(np.argmax(spec[band]))]

    order = np.argsort(spec)[::-1]
    print("top spectral peaks (Hz : relative magnitude):")
    smax = spec.max()
    shown, i = 0, 0
    while shown < 8 and i < len(order):
        f = freqs[order[i]]
        if f >= 0.1:
            print(f"    {f:9.2f} Hz : {spec[order[i]] / smax:5.3f}")
            shown += 1
        i += 1
    k = int(round(args.msg_freq * n / args.sample_rate))
    print(f"power at expected {args.msg_freq:.2f} Hz : "
          f"{spec[k] / smax:5.3f} of peak")
    print(f"dominant signal frequency (>{lo_cut:.1f} Hz): {f_peak:.2f} Hz "
          f"(expected {args.msg_freq:.2f} Hz)")
    freq_ok = abs(f_peak - args.msg_freq) <= max(1.0, 0.02 * args.msg_freq)

    print(f"timestamps monotonic : {'PASS' if mono_ok else 'FAIL'}")
    print(f"timestamps uniform   : {'PASS' if ts_ok else 'FAIL'}")
    print(f"recovered tone       : {'PASS' if freq_ok else 'FAIL'}")

    if args.plot:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(10, 7))
        nshow = min(n, int(5 * args.sample_rate / args.msg_freq))
        axes[0].plot(sig[:nshow])
        axes[0].set_title(f"recovered signal ch{ch} (first ~5 message periods)")
        axes[1].semilogy(freqs[1:], spec[1:])
        axes[1].axvline(args.msg_freq, color="r", ls="--", alpha=0.5)
        axes[1].set_title("spectrum")
        axes[1].set_xlabel("Hz")
        plt.tight_layout()
        plt.show()

    sys.exit(0 if (mono_ok and ts_ok and freq_ok) else 1)


if __name__ == "__main__":
    main()
