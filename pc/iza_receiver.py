#!/usr/bin/env python3
"""
iza_receiver.py — PC-side UDP sink + validator.

Receives the iza return flow from the Zynq, checks structure, and dumps raw
records for offline analysis:

  * seq_num monotonic; gaps detected and counted (drop rate)
  * header structure exact (magic, self-describing chan_mask/stride_words,
    payload_len vs datagram size)
  * PL timestamp deltas uniform (framing survived DMA + network intact)
  * sustained data rate reporting

The capture is written raw (concatenated records) plus a <out>.json sidecar
holding chan_mask/stride_words so iza_validate can parse the variable layout.

Usage:
  python iza_receiver.py [--port 7100] [--out capture.bin]
                         [--sample-rate 200000] [--seconds 0]
"""

import argparse
import json
import socket
import sys
import time

import numpy as np

import iza_packet as izp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7100)
    ap.add_argument("--out", default="capture.bin",
                    help="raw record dump for offline comparison")
    ap.add_argument("--sample-rate", type=float, default=200000.0,
                    help="demod output rate = 200 MHz / R (R=1000 -> 200 kHz, "
                         "R=8000 -> 25 kHz); only sets the expected record "
                         "spacing for the gap check — timestamps are authoritative")
    ap.add_argument("--pl-clk", type=float, default=izp.PL_CLK_HZ,
                    help="PL clock (timestamp units); default 200e6 (5 ns ticks)")
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after N seconds of data (0 = until Ctrl+C)")
    args = ap.parse_args()

    expected_dt = args.pl_clk / args.sample_rate  # PL clocks per record

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    eff = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    sock.bind(("0.0.0.0", args.port))
    sock.settimeout(1.0)
    print(f"listening on UDP {args.port}  (SO_RCVBUF={eff})")

    n_dgrams = n_bytes = n_records = 0
    n_bad_magic = n_bad_len = n_gaps = n_dropped = n_reorder = 0
    last_seq = None
    last_ts = None
    ts_dev_max = 0.0
    n_ts_checked = 0
    layout = None                 # (chan_mask, stride_words) of the stream
    t_first = None
    t_report = time.monotonic()

    out = open(args.out, "wb")
    try:
        while True:
            try:
                data, _ = sock.recvfrom(2048)
            except socket.timeout:
                if t_first and args.seconds and \
                   time.monotonic() - t_first >= args.seconds:
                    break
                continue

            now = time.monotonic()
            if t_first is None:
                t_first = now
                print("first datagram received")

            if len(data) < izp.HDR_LEN:
                n_bad_len += 1
                continue
            h = izp.parse_header(data)
            if h["magic"] != izp.MAGIC:
                n_bad_magic += 1
                continue
            rec_bytes = h["stride_words"] * 4
            if (len(data) != izp.HDR_LEN + h["payload_len"]
                    or rec_bytes == 0 or h["payload_len"] % rec_bytes):
                n_bad_len += 1
                continue

            if layout is None:
                layout = (h["chan_mask"], h["stride_words"])
                print(f"stream layout: chan_mask=0x{h['chan_mask']:02x} "
                      f"demod={izp.demod_list(h['chan_mask'])} "
                      f"adc={izp.adc_enabled(h['chan_mask'])} "
                      f"stride={h['stride_words']} words")

            n_dgrams += 1
            n_bytes += len(data)

            if last_seq is not None:
                d = h["seq"] - last_seq
                if d == 1:
                    pass
                elif d > 1:
                    n_gaps += 1
                    n_dropped += d - 1
                else:
                    n_reorder += 1
            if last_seq is None or h["seq"] > last_seq:
                last_seq = h["seq"]

            payload = data[izp.HDR_LEN:izp.HDR_LEN + h["payload_len"]]
            rec = izp.deinterleave(payload, h["chan_mask"], h["stride_words"])
            if rec:
                ts = rec["ts"].astype(np.int64)
                for k in range(rec["n"]):
                    if last_ts is not None:
                        dt = int(ts[k]) - last_ts
                        if 0 < dt < 2 * expected_dt:
                            dev = abs(dt - expected_dt)
                            ts_dev_max = max(ts_dev_max, dev)
                            n_ts_checked += 1
                    last_ts = int(ts[k])
                n_records += rec["n"]
            out.write(payload)

            if now - t_report >= 1.0:
                el = now - t_first
                mbps = n_bytes * 8 / el / 1e6 if el > 0 else 0.0
                print(f"[{el:7.1f}s] dgrams={n_dgrams}  recs={n_records}  "
                      f"{mbps:6.2f} Mbps  gaps={n_gaps} dropped={n_dropped}")
                t_report = now

            if args.seconds and now - t_first >= args.seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        out.close()
        if layout is not None:
            side = args.out + ".json"
            json.dump({"chan_mask": layout[0], "stride_words": layout[1]},
                      open(side, "w"))
            print(f"layout sidecar -> {side}")

    el = (time.monotonic() - t_first) if t_first else 0.0
    total_expected = n_dgrams + n_dropped
    drop_pct = 100.0 * n_dropped / total_expected if total_expected else 0.0
    print("\n================ summary ================")
    print(f"duration            : {el:.1f} s")
    print(f"datagrams received  : {n_dgrams}")
    print(f"records received    : {n_records}")
    print(f"throughput          : "
          f"{(n_bytes * 8 / el / 1e6) if el else 0:.2f} Mbps")
    print(f"seq gaps / dropped  : {n_gaps} / {n_dropped} ({drop_pct:.3f}%)")
    print(f"reordered           : {n_reorder}")
    print(f"bad magic / bad len : {n_bad_magic} / {n_bad_len}")
    print(f"ts delta expected   : {expected_dt:.2f} PL clocks")
    print(f"ts delta max dev    : {ts_dev_max:.2f} "
          f"(checked {n_ts_checked} contiguous pairs)")

    ok = (n_dgrams > 0 and n_bad_magic == 0 and n_bad_len == 0
          and n_reorder == 0 and ts_dev_max <= 1.5)
    print("ACCEPTANCE:", "PASS" if ok else "FAIL",
          "(structure exact, seq monotonic; review drop % against budget)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
