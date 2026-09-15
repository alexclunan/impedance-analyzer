#!/usr/bin/env python3
"""
iza_packet.py — shared parser for the self-describing iza packet format.

The v2 packetizer emits variable records: the datagram header carries chan_mask
+ stride_words, and each record is, in fixed field order, only the enabled
fields:
    ts_lo, ts_hi(+OR)                       (always, 2 words)
    sig_i, phase_i  for each set demod bit  (ascending i, 2 words each)
    adc (i32, sign-extended)                (if chan_mask bit4)

Keep in sync with iza_protocol.h (iza_pkt_hdr_t) and output_packetizer_v2.v.
"""

import struct

import numpy as np

MAGIC = 0x31415A49                       # "IZA1"
# magic, seq, first_ts, chan_mask, stride_words, flags, payload_len, buf_seq, rec_index
HDR_FMT = "<IIQBBHIII"
HDR_LEN = struct.calcsize(HDR_FMT)       # 32
assert HDR_LEN == 32

# Timestamp counter runs at 100 MHz but increments by 2, so its value is in
# 5 ns units — numerically identical to the old 200 MHz counter.
PL_CLK_HZ = 200_000_000.0
NDEMOD = 4
TS_MASK = np.uint64(0x3FFF_FFFF_FFFF_FFFF)   # low 62 bits (strip OR in [63:62])


def parse_header(data):
    (magic, seq, first_ts, chan_mask, stride_words, flags,
     payload_len, buf_seq, rec_index) = struct.unpack_from(HDR_FMT, data)
    return dict(magic=magic, seq=seq, first_ts=first_ts, chan_mask=chan_mask,
                stride_words=stride_words, flags=flags, payload_len=payload_len,
                buf_seq=buf_seq, rec_index=rec_index)


def demod_list(chan_mask):
    return [i for i in range(NDEMOD) if chan_mask & (1 << i)]


def adc_enabled(chan_mask):
    return bool(chan_mask & (1 << 4))


def stride_words(chan_mask):
    """32-bit words per record for a given mask (matches the firmware)."""
    return 2 + 2 * len(demod_list(chan_mask)) + (1 if adc_enabled(chan_mask) else 0)


def deinterleave(payload, chan_mask, stride=None):
    """Parse a fixed-stride record payload into structured arrays.

    Returns dict:
      n     : record count
      ts    : uint64 counter (OR stripped), 5 ns units
      orf   : uint8 over-range flag (ts bits [63:62])
      sig   : {ch: int32 array}   demod magnitude per enabled channel
      phase : {ch: int32 array}   demod phase per enabled channel
      adc   : int32 array or None (raw-ADC monitor if enabled)
    or None if the payload holds no whole records.
    """
    sw = stride or stride_words(chan_mask)
    nrec = len(payload) // (sw * 4)
    if nrec == 0:
        return None
    u = np.frombuffer(payload, dtype="<u4", count=nrec * sw).reshape(nrec, sw)
    s = u.view(np.int32)

    ts_hi = u[:, 1].astype(np.uint64)
    ts = (((ts_hi << np.uint64(32)) | u[:, 0].astype(np.uint64)) & TS_MASK)
    orf = ((ts_hi >> np.uint64(30)) & np.uint64(0x3)).astype(np.uint8)

    col = 2
    sig, phase = {}, {}
    for ch in demod_list(chan_mask):
        sig[ch] = s[:, col].copy()
        phase[ch] = s[:, col + 1].copy()
        col += 2
    adc = s[:, col].copy() if adc_enabled(chan_mask) else None
    return dict(n=nrec, ts=ts, orf=orf, sig=sig, phase=phase, adc=adc)
