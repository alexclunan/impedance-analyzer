#!/usr/bin/env python3
"""
iza_sender.py — push real lab data PC -> board over UDP (verification plan 03).

Reads an int16 magnitude file from export_zbin_magnitude.py
(`<stem>_adc_int16.bin` + `<stem>.json`), resamples it to the board's fixed
message consume rate (~312.5 kHz), and streams it continuously (looping) to the
board's message port. A telemetry-listener thread reads the board's ring-fill
reports and trims the send rate toward ~50% ring fill, so the PC tracks the
board's hardware-paced consume rate without under/overrunning.

Wire formats: see iza_protocol.h (iza_sample_hdr_t, iza_telem_t).

Usage:
  python iza_sender.py <stem>_adc_int16.bin --board 192.168.0.80 \
      [--msg-port 7200] [--telemetry-port 7201] [--board-rate 312500] \
      [--no-resample] [--loop] [--seconds 0]
"""

import argparse
import json
import os
import socket
import struct
import sys
import threading
import time

import numpy as np

SMAGIC = 0x31415A53            # "SZA1"
TMAGIC = 0x31415A54            # "TZA1"
SAMPLES_PER_DGRAM = 700        # matches IZA_SAMPLES_PER_DGRAM
SFLAG_LOOP_WRAP = 0x0001

SHDR = struct.Struct("<IIIIQ")          # magic, seq, n_samples, flags, stream_pos (24 B)
THDR = struct.Struct("<IIIIQIIIIQ")     # iza_telem_t (48 B)

BOARD_RATE_DEFAULT = 625000.0   # 200 MHz / 320 (sample_hold consume rate)


def generate_samples(kind, board_rate, freq, amp, seconds):
    """Synthesise a test message at the board rate (no resampling needed).
    Length is rounded to a whole number of cycles so the loop wrap is seamless."""
    amp_i = max(0.0, min(1.0, amp)) * 32767.0
    if kind == "dc":
        n = max(1, int(round(seconds * board_rate)))
        return np.full(n, int(amp_i), dtype="<i2")
    cycles = max(1, int(round(seconds * freq)))
    n = max(2, int(round(cycles * board_rate / freq)))
    t = np.arange(n) / board_rate
    if kind == "ramp":
        # sawtooth 0..1 over each period, mapped to +-amp
        phase = (freq * t) % 1.0
        wave = 2.0 * phase - 1.0
    else:  # sine
        wave = np.sin(2.0 * np.pi * freq * t)
    data = np.clip(np.round(amp_i * wave), -32768, 32767).astype("<i2")
    print(f"generated {kind} {freq:.1f} Hz amp {amp:.2f} @ {board_rate:.0f} Hz: "
          f"{n} samples ({cycles} cycles, seamless loop)")
    return data


def load_samples(path, board_rate, do_resample, src_rate=0.0, use_scipy=False):
    data = np.fromfile(path, dtype="<i2")
    if data.size == 0:
        sys.exit(f"empty sample file: {path}")

    native = None
    if src_rate and src_rate > 0:
        native = float(src_rate)            # explicit override (e.g. 14000)
    else:
        jpath = os.path.splitext(path)[0]
        # export writes "<output>.json"; tolerate "<stem>.json" or "<bin>.json"
        for cand in (path + ".json", jpath + ".json"):
            if os.path.exists(cand):
                try:
                    meta = json.load(open(cand))
                    native = meta.get("zi_meta", {}).get("estimated_sample_rate_hz")
                except Exception:
                    pass
                break

    if do_resample and native and abs(native - board_rate) > 1.0:
        # Preserve real-time duration: native_n / native = out_n / board_rate.
        # numpy linear interp is the DEFAULT (adequate for the big upsample here
        # and dependency-free); scipy's polyphase filter is opt-in via --hq
        # because importing scipy can hang/fail on some interpreters. We NEVER
        # silently send at the wrong rate (that plays the data too fast).
        did_scipy = False
        if use_scipy:
            try:
                from fractions import Fraction
                from scipy.signal import resample_poly
                frac = Fraction(board_rate / float(native)).limit_denominator(4000)
                data = resample_poly(data.astype(np.float64), frac.numerator,
                                     frac.denominator)
                data = np.clip(np.round(data), -32768, 32767).astype("<i2")
                print(f"resampled {native:.1f} Hz -> {board_rate:.1f} Hz "
                      f"(scipy {frac.numerator}/{frac.denominator}), "
                      f"{data.size} samples")
                did_scipy = True
            except Exception as e:                       # ImportError or worse
                print(f"scipy resample unavailable ({e}); using numpy",
                      file=sys.stderr)
        if not did_scipy:
            n_out = int(round(data.size * board_rate / float(native)))
            xq = np.linspace(0.0, data.size - 1.0, n_out)
            data = np.interp(xq, np.arange(data.size), data.astype(np.float64))
            data = np.clip(np.round(data), -32768, 32767).astype("<i2")
            print(f"resampled {native:.1f} Hz -> {board_rate:.1f} Hz "
                  f"(numpy linear interp, {data.size} samples)")
    elif native:
        print(f"native rate {native:.1f} Hz == board rate; no resample")
    else:
        print("no sample-rate metadata; assuming data is already at board rate")
    # native = samples-per-real-second of the ORIGINAL waveform (what the plotter
    # overlays); the returned data is resampled to board_rate but plays in the
    # same real time, so native_rate is the wall-time -> ref-index scale.
    return np.ascontiguousarray(data, dtype="<i2"), float(native or board_rate)


class Servo:
    """Telemetry-driven proportional trim of the send rate toward 50% fill."""
    def __init__(self):
        self.mult = 1.0
        self.fill_frac = 0.0
        self.lock = threading.Lock()
        self.last = None     # latest iza_telem_t fields (dict)

    def update(self, t):
        cap = t["ring_capacity"] or 1
        fill = t["ring_fill"] / cap
        # proportional toward 50% fill; clamp +-10%
        mult = 1.0 + 0.3 * (0.5 - fill)
        if t["overrun_count"] and fill > 0.8:
            mult = min(mult, 0.95)
        mult = max(0.9, min(1.1, mult))
        with self.lock:
            self.mult = mult
            self.fill_frac = fill
            self.last = t

    def get(self):
        with self.lock:
            return self.mult, self.fill_frac, self.last


def telemetry_listener(sock, servo, stop):
    sock.settimeout(0.5)
    while not stop.is_set():
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue
        if len(data) < THDR.size:
            continue
        (magic, seq, ring_fill, ring_capacity, consumed_total,
         underrun, overrun, inb_last, inb_lost, uptime_ms) = THDR.unpack_from(data)
        if magic != TMAGIC:
            continue
        servo.update(dict(ring_fill=ring_fill, ring_capacity=ring_capacity,
                          consumed_total=consumed_total, underrun_count=underrun,
                          overrun_count=overrun, inbound_last_seq=inb_last,
                          inbound_lost=inb_lost, uptime_ms=uptime_ms))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?",
                    help="<stem>_adc_int16.bin from export_zbin_magnitude.py "
                         "(omit when using --gen)")
    ap.add_argument("--board", required=True, help="board IP (e.g. 192.168.0.80)")
    ap.add_argument("--gen", choices=["sine", "ramp", "dc"],
                    help="send a synthetic test message instead of a file "
                         "(pipeline bring-up before real data)")
    ap.add_argument("--gen-freq", type=float, default=1000.0,
                    help="synthetic message frequency in Hz (--gen sine/ramp)")
    ap.add_argument("--gen-amp", type=float, default=0.5,
                    help="synthetic amplitude, 0..1 of full scale")
    ap.add_argument("--gen-seconds", type=float, default=1.0,
                    help="length of the generated loop buffer in seconds")
    ap.add_argument("--save", help="write the generated/loaded int16 to this file "
                                   "(so iza_plotter --ref can overlay it)")
    ap.add_argument("--sync-file",
                    help="write {t0_wall, native_rate} here at stream start so "
                         "iza_plotter --sync can anchor the overlay via the shared "
                         "PC wall clock (accurate to the PC<->board round trip)")
    ap.add_argument("--msg-port", type=int, default=7200)
    ap.add_argument("--telemetry-port", type=int, default=7201)
    ap.add_argument("--board-rate", type=float, default=BOARD_RATE_DEFAULT,
                    help="board message consume rate in Hz (default 312500)")
    ap.add_argument("--src-rate", type=float, default=0.0,
                    help="native sample rate of the lab data in Hz "
                         "(e.g. 14000); overrides the JSON estimate")
    ap.add_argument("--no-resample", action="store_true")
    ap.add_argument("--hq", action="store_true",
                    help="use scipy polyphase resampling (higher quality but "
                         "imports scipy; default is numpy linear interp)")
    ap.add_argument("--loop", action="store_true",
                    help="loop the finite file forever (recommended)")
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after N seconds (0 = until Ctrl+C)")
    args = ap.parse_args()

    if args.gen:
        data = generate_samples(args.gen, args.board_rate, args.gen_freq,
                                args.gen_amp, args.gen_seconds)
        native_rate = args.board_rate   # generated data plays at board rate
        args.loop = True                # a finite generated buffer is meant to loop
    elif args.file:
        data, native_rate = load_samples(args.file, args.board_rate,
                                          not args.no_resample, args.src_rate,
                                          args.hq)
    else:
        sys.exit("give a sample file or use --gen sine|ramp|dc")

    if args.save:
        data.tofile(args.save)
        # a --save file is what gets streamed: it plays at the board rate, so
        # tag it with that rate for iza_plotter's auto-overlay.
        json.dump({"zi_meta": {"estimated_sample_rate_hz": args.board_rate}},
                  open(args.save + ".json", "w"))
        print(f"saved {data.size} int16 to {args.save} "
              f"(overlay: iza_plotter.py --ref {args.save})")

    n_total = data.size
    print(f"streaming {n_total} samples to {args.board}:{args.msg_port} "
          f"@ ~{args.board_rate:.0f} Hz  (loop={args.loop})")

    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    dst = (args.board, args.msg_port)

    telem = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    telem.bind(("0.0.0.0", args.telemetry_port))
    servo = Servo()
    stop = threading.Event()
    tthr = threading.Thread(target=telemetry_listener, args=(telem, servo, stop),
                            daemon=True)
    tthr.start()

    seq = 0
    pos = 0           # absolute sample index (monotonic across loops)
    src = 0           # index into data
    # Anchor: wall-clock at the instant stream_pos 0 starts. The plotter (same
    # PC, same wall clock) counts native_rate samples elapsed since this to know
    # where in the file the board is currently playing (within the round trip).
    wall_t0 = time.time()
    if args.sync_file:
        json.dump({"t0_wall": wall_t0, "native_rate": native_rate,
                   "source": args.file or f"gen:{args.gen}"},
                  open(args.sync_file, "w"))
        print(f"sync: wrote {args.sync_file}  t0_wall={wall_t0:.3f}  "
              f"native_rate={native_rate:.1f} Hz")
    t0 = time.perf_counter()
    deadline = t0
    t_report = t0
    sent_samples = 0

    try:
        while True:
            mult, fill, last = servo.get()
            interval = SAMPLES_PER_DGRAM / (args.board_rate * mult)

            # build one datagram of up to SAMPLES_PER_DGRAM samples
            flags = 0
            end = src + SAMPLES_PER_DGRAM
            if end <= n_total:
                chunk = data[src:end]
                src = end if end < n_total else 0
                if end == n_total and args.loop:
                    flags |= SFLAG_LOOP_WRAP
            else:
                # wrap: take tail + head (only when looping)
                if not args.loop:
                    chunk = data[src:n_total]
                else:
                    head = end - n_total
                    chunk = np.concatenate([data[src:n_total], data[:head]])
                    flags |= SFLAG_LOOP_WRAP
                src = (end - n_total) if args.loop else n_total

            nsmp = chunk.size
            hdr = SHDR.pack(SMAGIC, seq, nsmp, flags, pos)
            tx.sendto(hdr + chunk.tobytes(), dst)
            seq += 1
            pos += nsmp
            sent_samples += nsmp

            if not args.loop and src >= n_total:
                print("reached end of file (no --loop); done")
                break

            # deadline pacing (avoids sleep drift)
            deadline += interval
            now = time.perf_counter()
            sleep = deadline - now
            if sleep > 0:
                time.sleep(sleep)
            elif sleep < -0.5:
                deadline = now      # fell badly behind; resync

            now = time.perf_counter()
            if now - t_report >= 1.0:
                el = now - t0
                eff = sent_samples / el if el > 0 else 0
                lost = last["inbound_lost"] if last else 0
                under = last["underrun_count"] if last else 0
                over = last["overrun_count"] if last else 0
                print(f"[{el:6.1f}s] sent {sent_samples} smp  "
                      f"{eff:8.0f} Hz  mult={mult:.3f}  fill={fill*100:4.1f}%  "
                      f"under={under} over={over} lost={lost}")
                t_report = now
            if args.seconds and now - t0 >= args.seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        tthr.join(timeout=1.0)
    print("sender stopped")


if __name__ == "__main__":
    main()
