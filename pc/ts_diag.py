#!/usr/bin/env python3
"""
ts_diag.py — timestamp-delta diagnostic for a raw capture.bin.

Reads a capture from iza_receiver (self-describing records) and prints a
histogram of consecutive timestamp deltas, so you can read off the demod
output/record rate (rate = pl_clk / dominant_delta).

Layout comes from the <capture>.json sidecar (chan_mask); override with
--chan-mask. --channel picks which demod channel's `signal` the zero/non-zero
tally uses (default: lowest enabled).

Usage:
  python ts_diag.py [capture.bin] [--pl-clk 200e6] [--max-records 100000]
"""

import argparse
import json
import os
import sys
from collections import Counter

import numpy as np

import iza_packet as izp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="capture.bin")
    ap.add_argument("--pl-clk", type=float, default=izp.PL_CLK_HZ)
    ap.add_argument("--chan-mask", type=lambda s: int(s, 0), default=None)
    ap.add_argument("--channel", type=int, default=None)
    ap.add_argument("--max-records", type=int, default=100_000,
                    help="analyse first N records (0 = all)")
    ap.add_argument("--bucket", type=int, default=50,
                    help="histogram bucket width in PL clocks")
    args = ap.parse_args()

    try:
        payload = open(args.file, "rb").read()
    except FileNotFoundError:
        sys.exit(f"ERROR: file not found: {args.file}")

    chan_mask = args.chan_mask
    if chan_mask is None:
        side = args.file + ".json"
        if not os.path.exists(side):
            side = os.path.splitext(args.file)[0] + ".json"
        chan_mask = json.load(open(side))["chan_mask"] if os.path.exists(side) else 0x01
        if args.chan_mask is None and not os.path.exists(side):
            print("no layout sidecar; assuming chan_mask=0x01 (ch0)")

    rec = izp.deinterleave(payload, chan_mask)
    if rec is None:
        sys.exit("no whole records in capture")
    demod = izp.demod_list(chan_mask)
    ch = args.channel if args.channel is not None else (demod[0] if demod else None)

    n = rec["n"]
    if args.max_records and n > args.max_records:
        n = args.max_records
    print(f"Analysing {n} records from {args.file} (chan_mask=0x{chan_mask:02x})")

    ts = rec["ts"][:n].astype(np.int64)
    d = np.diff(ts)
    deltas = d[(d > 0) & (d < 50_000)]   # drop seq-gap jumps

    if ch is not None:
        sig = rec["sig"][ch][:n]
        nz = int(np.count_nonzero(sig))
        print(f"ch{ch} non-zero signal : {nz} ({100*nz/n:.1f}%)")

    if deltas.size == 0:
        print("No in-range deltas found.")
        return

    b = args.bucket
    buckets = Counter((int(x) // b) * b for x in deltas)
    top = sorted(buckets.items(), key=lambda x: -x[1])[:20]

    print(f"\nTimestamp delta histogram (bucket={b} clocks, top 20):")
    print(f"{'delta range':>20}  {'count':>8}  {'fraction':>8}  {'rate Hz':>10}")
    total = deltas.size
    for lo, cnt in top:
        mid = lo + b // 2
        rate = args.pl_clk / mid if mid > 0 else 0
        print(f"  {lo:6d}-{lo+b-1:<6d}  {cnt:>8d}  {cnt/total:>8.3f}  {rate:>10.1f}")

    dominant_lo = top[0][0]
    dominant_mid = dominant_lo + b // 2
    dominant_rate = args.pl_clk / dominant_mid if dominant_mid > 0 else 0
    print(f"\nDominant delta: ~{dominant_mid} clocks  ->  record rate "
          f"~ {dominant_rate:.0f} Hz")


if __name__ == "__main__":
    main()
