#!/usr/bin/env python3
"""
iza_ctrl.py — PC control client for the board's config channel.

Talks to iza_replay's UDP control port (7202): write/read any AXI register
(reg index 0..15) and run raw SPI transactions to the AD9122 DAC / AD9467 ADC.
Importable (class IzaCtrl) so a GUI reuses it; also a CLI.

AXI register map (rasterized-DDS bitstream, 100/200 MHz split):
  0  SYS_CTRL0   [0]dds_rst_n [1]pipe_rst_n [2]dac_rst_n [3]fifo_rst_n
                 [4]dac_chip_nreset [5]run
                 [6]adc_input_sel (0=analog ADC, 1=am_modulator loopback)
                 [7]UNUSED (no hardware effect)
                 [8]dac_output_sel (0=dds_cos tones, 1=test/replay signal)
  1  ANALOG1     [3:0]PGA gain code
  2  CH_EN2      [3:0]TX tone mask, [7:4]RX demod mask
  3  FIR_COEFF_CMD  reloadable FIR loader: [15:0]coeff [17:16]op(0nop/1reset/2push/3commit)
                 [30:18]CIC rate 1000..8000 (0=unchanged, applied on commit) [31]toggle
  4  PKT_CFG4    [7:0]records/packet, [11:8]payload mask, [15:12]format
  5  CH0_FA5     [13:0]FCW0 (x12.5 kHz), [31:16]AMP0
  6  CH1_FA6     [13:0]FCW1,             [31:16]AMP1
  7  CH2_FA7     [13:0]FCW2,             [31:16]AMP2
  8  CH3_FA8     [13:0]FCW3,             [31:16]AMP3
  9  reg9        trigger output-1 fire timestamp low  (was tone 0/1 phase)
 10  reg10       trigger output-1 fire timestamp high (was tone 2/3 phase)

DDS is rasterized (modulus 16000): f_out = FCW * 12500 Hz, FCW in 0..15999.
Carrier must be on the 12.5 kHz grid AND >400 kHz (analog HPF) -> FCW >= 32.

SPI (see datasheets):
  AD9122 DAC  — 8-bit instr  [R/W][A6:0], byte mode, mode 0, <=40 MHz, 4-wire.
  AD9467 ADC  — 16-bit instr [R/W][W1][W0][A12:0], buffered writes committed by
                0xFF<-0x01, mode 0, <=25 MHz, 3-wire (reads best-effort).

Usage examples:
  python iza_ctrl.py --board 192.168.0.80 pga 8
  python iza_ctrl.py --board 192.168.0.80 dac-output 0     # DAC = generator tones
  python iza_ctrl.py --board 192.168.0.80 carrier 450e3    # channel 0
  python iza_ctrl.py --board 192.168.0.80 freq 1 462.5e3   # channel 1
  python iza_ctrl.py --board 192.168.0.80 reset            # hold all in reset
  python iza_ctrl.py --board 192.168.0.80 run              # release + run
  python iza_ctrl.py --board 192.168.0.80 dac-init
  python iza_ctrl.py --board 192.168.0.80 adc-init --pattern checkerboard
  python iza_ctrl.py --board 192.168.0.80 regread 0
"""

import argparse
import socket
import struct
import sys
import time
from dataclasses import dataclass, field

CMAGIC = 0x31415A43            # "CZA1"
CTRL_PORT = 7202
MAXDATA = 64

OP_REG_WRITE = 1
OP_REG_READ = 2
OP_SPI_XFER = 3
OP_TRIG_TEST = 4     # manual fire; target = output mask (bit0=out0, bit1=out1)
SPI_DAC = 0
SPI_ADC = 1

REQ = struct.Struct(f"<IIBBBBI{MAXDATA}s")   # 80 B
RSP = struct.Struct(f"<IIiIB3x{MAXDATA}s")   # 84 B

# ---- register indices ----
R_SYS_CTRL = 0
R_ANALOG   = 1
R_CH_EN    = 2
R_DECIM    = 3     # reserved / unused
R_PKT_CFG  = 4
R_CH_FA    = (5, 6, 7, 8)     # per-channel {AMP[31:16], FCW[13:0]}
R_PHASE    = (9, 10)          # POFF packed two channels per register

# ---- reloadable FIR coefficient loader (REG3 command port) ----
# REG3: [15:0] coeff, [17:16] opcode, [30:18] CIC rate, [31] strobe toggle.
# See fir_coeff_loader.v.
R_FIR_CMD    = 3
# HARDCODED to 999 — must equal NCOEF in fir_coeff_loader.v and
# fir_design.LOADER_NCOEF. The loader streams exactly this many coefficients on
# commit and saturates its write pointer past the end, so a wrong count loads a
# different filter without any error being reported.
FIR_NCOEF    = 999
# CIC decimation rate carried in REG3[30:18] (13 bits, 0 = leave unchanged).
# Must match RATE_MIN/RATE_MAX in fir_coeff_loader.v and the CIC Compiler's
# MIN_RATE/MAX_RATE. Restricted to power-of-two multiples of 1000 so the R^4
# gain change between rates is an exact bit shift.
FIR_RATE_MIN = 1000
FIR_RATE_MAX = 8000
FIR_RATES    = (1000, 2000, 4000, 8000)
FIR_RATE_SHIFT = 18
FIR_OP_NOP   = 0
FIR_OP_RESET = 1     # reset the write index
FIR_OP_PUSH  = 2     # store coeff at index, index++
FIR_OP_COMMIT = 3    # stream staged coeffs into the FIR + config (take effect)

# ---- SYS_CTRL0 bit positions (all *_rst_n: 1 = released/run) ----
# Verified against the block design (ilslice -> net):
#   bit6 -> mux_0.sel               : demod adc_input mux (ADC vs am_modulator)
#   bit8 -> dac_output_wrapper.test_mode : DAC output (dds_cos vs test_signal)
#   bit7 -> NOT WIRED (no slice)    : dead, has no hardware effect
B_DDS_RSTN     = 0
B_PIPE_RSTN    = 1
B_DAC_RSTN     = 2
B_FIFO_RSTN    = 3
B_DAC_CHIP_NRST = 4
B_RUN          = 5
B_ADC_SEL      = 6   # demod input: 0 = analog ADC, 1 = am_modulator (loopback)
B_DEMOD_SRC    = 7   # UNUSED in hardware (kept for the bit map; no effect)
B_DAC_TESTSIG  = 8   # DAC output: 0 = dds_cos tones, 1 = test/replay signal

SYS_RELEASE_ALL = ((1 << B_DDS_RSTN) | (1 << B_PIPE_RSTN) | (1 << B_DAC_RSTN)
                   | (1 << B_FIFO_RSTN) | (1 << B_DAC_CHIP_NRST))   # 0x1F
SYS_RUN  = SYS_RELEASE_ALL | (1 << B_RUN)                           # 0x3F
SYS_CORE_MASK = 0x3F         # reset+run bits; leaves mux/demod/test untouched

# ---- rasterized DDS ----
RASTER_HZ = 12500.0
FCW_MAX = 16000              # modulus; valid FCW = 0..15999
FCW_MASK = 0x3FFF            # 14 bits
AMP_DEFAULT = 0x8000        # Q1.15 unity: single tone = exact full-scale passthrough

# ---- packetizer ----
MTU_PAYLOAD = 1440          # 1472 - 32B header; records-per-packet target
PKT_HDR_WORDS = 2           # timestamp words per record (always present)

# AD9467 test-pattern codes (reg 0x0D[3:0])
ADC_PATTERNS = {
    "off": 0x0, "midscale": 0x1, "posfs": 0x2, "negfs": 0x3,
    "checkerboard": 0x4, "pn23": 0x5, "pn9": 0x6, "onezero": 0x7,
}

# ---- Plan 07 triggering (keep in sync with iza_protocol.h) ----
GMAGIC = 0x31415A47            # "GZA1" — trigger config (PC -> board)
EMAGIC = 0x31415A45            # "EZA1" — trigger event  (board -> PC)
EVT_PORT = 7203                # board -> PC trigger events

TRIG_OFF, TRIG_SOFT, TRIG_HW = 0, 1, 2
DLY_FIXED, DLY_VELOCITY = 0, 1
COMB_AND, COMB_OR = 0, 1
EVF_PASS, EVF_SOFT, EVF_VELOCITY = 1, 2, 4
TRIG_MAXCH = 4

# spare AXI regs carrying the Stage-2 PL fire command
R_TRIG_T_LO, R_TRIG_T_HI, R_TRIG_W, R_TRIG_CMD = 12, 13, 14, 15

# scaling to wire units — the single source of truth for the GUI
PL_TICK_HZ = 200_000_000       # timestamp counts: 5 ns each
TRIG_MAG_SCALE = 1 << 30       # fix32_30 magnitude (sig / 2^30)
TRIG_PH_SCALE = 1 << 29        # fix32_29 phase    (phase / 2^29 rad)

# iza_trig_cfg_t body (128 B) and iza_trig_evt_t (88 B); little-endian, packed.
_TRIG_BODY = "8BiiIIIIQQQQQff4f4f4f"
TRIG_CFG = struct.Struct("<" + _TRIG_BODY)
TRIG_MSG = struct.Struct("<II" + _TRIG_BODY)         # magic, seq, cfg...
TRIG_EVT = struct.Struct("<3I2H6Q2i4i")              # 88 B


@dataclass
class TrigCfg:
    """Trigger configuration in wire units (ticks / fix-point / radians).

    Use IzaCtrl.sec_to_ticks / mag_to_fix to convert from physical units.
    """
    mode: int = TRIG_OFF
    arm: int = 0
    amp_channel: int = 0
    polarity: int = 0                 # 0 peak-then-trough, 1 trough-then-peak
    combine: int = COMB_AND
    phase_mask: int = 0               # channels used in phase classification
    delay_mode: int = DLY_FIXED
    emit_candidates: int = 1          # stream events even when classify fails
    amp_threshold: int = 0            # fix32_30 excursion arm level
    min_peak_diff: int = 0            # fix32_30 min peak-to-trough
    baseline_shift: int = 12          # leaky-integrator shift (larger = slower)
    holdoff_ticks: int = 0
    event_ticks: int = 0              # max span of one bipolar event
    watchdog_ms: int = 3000           # auto-disarm if PC goes quiet (0 = never)
    fixed_delay_ticks: int = 0
    lead_offset_ticks: int = 0
    pulse_width_ticks: int = 0
    pulse_width2_ticks: int = 0
    pair_delay_ticks: int = 0
    distance_ratio: float = 1.0
    phase_mean: list = field(default_factory=lambda: [0.0] * TRIG_MAXCH)
    phase_lo: list = field(default_factory=lambda: [0.0] * TRIG_MAXCH)
    phase_hi: list = field(default_factory=lambda: [0.0] * TRIG_MAXCH)

    def _pad4(self, lst):
        v = list(lst)[:TRIG_MAXCH]
        return v + [0.0] * (TRIG_MAXCH - len(v))

    def pack_body(self):
        return TRIG_CFG.pack(
            self.mode, self.arm, self.amp_channel, self.polarity,
            self.combine, self.phase_mask, self.delay_mode, self.emit_candidates,
            self.amp_threshold, self.min_peak_diff,
            self.baseline_shift, self.holdoff_ticks, self.event_ticks,
            self.watchdog_ms,
            self.fixed_delay_ticks, self.lead_offset_ticks,
            self.pulse_width_ticks, self.pulse_width2_ticks, self.pair_delay_ticks,
            self.distance_ratio, 0.0,
            *self._pad4(self.phase_mean),
            *self._pad4(self.phase_lo),
            *self._pad4(self.phase_hi))


def parse_trig_evt(buf):
    """Decode a board->PC trigger-event datagram to a dict (ticks/fix units),
    or None if it isn't one. Convert with ticks/PL_TICK_HZ, mag/TRIG_MAG_SCALE,
    phase/TRIG_PH_SCALE."""
    if len(buf) < TRIG_EVT.size:
        return None
    (magic, seq, count, matched, flags,
     peak_ts, dt, delay, fire_ts, actual_ts, latency,
     peak_mag, trough_mag, p0, p1, p2, p3) = TRIG_EVT.unpack_from(buf)
    if magic != EMAGIC:
        return None
    return {
        "seq": seq, "count": count, "matched": matched, "flags": flags,
        "peak_ts": peak_ts, "dt_ticks": dt, "delay_ticks": delay,
        "fire_ts": fire_ts, "actual_ts": actual_ts, "latency_ticks": latency,
        "peak_mag": peak_mag, "trough_mag": trough_mag,
        "phase_cent": [p0, p1, p2, p3],
    }


class CtrlError(Exception):
    pass


class IzaCtrl:
    def __init__(self, board, port=CTRL_PORT, timeout=1.0):
        self.addr = (board, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.seq = 0
        self._fir_tog = 0            # strobe toggle for the FIR loader

    # ---- transport ----
    def _xact(self, op, target=0, reg=0, value=0, data=b""):
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        if len(data) > MAXDATA:
            raise CtrlError("SPI payload too long")
        pkt = REQ.pack(CMAGIC, self.seq, op, target, reg, len(data),
                       value & 0xFFFFFFFF, data.ljust(MAXDATA, b"\x00"))
        self.sock.sendto(pkt, self.addr)
        while True:
            try:
                buf, _ = self.sock.recvfrom(256)
            except socket.timeout:
                raise CtrlError("no response from board (is iza_replay running?)")
            if len(buf) < RSP.size:
                continue
            magic, seq, status, val, rlen, rdata = RSP.unpack_from(buf)
            if magic == CMAGIC and seq == self.seq:
                if status != 0:
                    raise CtrlError(f"board returned status {status}")
                return val, rdata[:rlen]

    # ---- AXI registers ----
    def reg_write(self, reg, value):
        return self._xact(OP_REG_WRITE, reg=reg, value=value)[0]

    def reg_read(self, reg):
        return self._xact(OP_REG_READ, reg=reg)[0]

    def _rmw(self, reg, mask, value):
        """Read-modify-write: replace the masked bits of `reg` with `value`.
        The board reads back written registers, so this is race-free for a
        single controller."""
        cur = self.reg_read(reg)
        new = (cur & ~mask) | (value & mask)
        self.reg_write(reg, new)
        return new

    # ---- PGA (ANALOG1[3:0]) ----
    # Parallel-mode PGA: the 4-bit code is INVERSE to gain.
    #   code 0 -> 26 dB (max) ... code 10 -> 6 dB (min).  gain_dB = 26 - 2*code
    PGA_GAIN_MIN_DB = 6
    PGA_GAIN_MAX_DB = 26

    def set_pga(self, gain_db):
        """Set PGA gain in dB (even, 6..26). Writes the inverse 4-bit code to
        ANALOG1[3:0]. Returns the code written."""
        if (gain_db < self.PGA_GAIN_MIN_DB or gain_db > self.PGA_GAIN_MAX_DB
                or gain_db % 2):
            raise CtrlError("PGA gain must be an even dB value in 6..26 "
                            "(higher dB = more gain = more front-end noise)")
        code = (26 - gain_db) // 2
        self._rmw(R_ANALOG, 0xF, code)
        return code

    def set_pga_code(self, code):
        """Write the raw 4-bit PGA code (debug). code 0 = 26 dB, code 10 = 6 dB."""
        if not 0 <= code <= 15:
            raise CtrlError("PGA code must be 0..15")
        return self._rmw(R_ANALOG, 0xF, code)

    # ---- SYS_CTRL0 config bits ----
    def set_demod_input(self, sel):
        """Demodulator input mux (SYS_CTRL0[6], mux_0.sel):
        0 = analog input (ADC), 1 = internal loopback (am_modulator = the PC
        replay / self-test signal)."""
        return self._rmw(R_SYS_CTRL, 1 << B_ADC_SEL, (sel & 1) << B_ADC_SEL)

    def set_dac_output(self, sel):
        """DAC output mux (SYS_CTRL0[8], dac_output_wrapper.test_mode):
        0 = signal-generator tones (dds_cos), 1 = internal test / replay
        signal (am_modulator output)."""
        return self._rmw(R_SYS_CTRL, 1 << B_DAC_TESTSIG, (sel & 1) << B_DAC_TESTSIG)

    def reset_all(self):
        """Assert every functional reset (hold), preserving mux/demod/test bits.

        TWO-STEP on purpose. Dropping RUN and the resets in one write chops the
        packetizer's AXI-Stream mid-beat, leaving the DMA S2MM holding a partial
        transfer that never completes -- FINISH blocks forever and dma_proxy has
        to be reloaded (this used to require a reboot). Clearing RUN first lets
        the packetizer's run-gate finish the record in flight and emit TLAST, so
        the DMA closes its buffer cleanly; only then is it safe to assert the
        resets."""
        self._rmw(R_SYS_CTRL, 1 << B_RUN, 0)   # graceful stop -> TLAST
        time.sleep(0.005)                      # let the packet drain (~us)
        return self._rmw(R_SYS_CTRL, SYS_CORE_MASK, 0)

    def run(self):
        """Release all resets and enable run, preserving mux/demod/test bits."""
        return self._rmw(R_SYS_CTRL, SYS_CORE_MASK, SYS_RUN)

    # ---- per-channel frequency / amplitude / phase ----
    @staticmethod
    def _fcw(hz):
        fcw = int(round(hz / RASTER_HZ))
        if not 0 <= fcw < FCW_MAX:
            raise CtrlError(f"carrier {hz:g} Hz -> FCW {fcw} out of 0..{FCW_MAX-1} "
                            f"(grid = {RASTER_HZ:g} Hz)")
        return fcw

    def set_freq(self, ch, hz):
        """Set channel `ch` (0..3) carrier. Rasterized: snaps to the 12.5 kHz
        grid. Warns if below the 400 kHz analog cutoff. Returns (fcw, actual_hz)."""
        if not 0 <= ch <= 3:
            raise CtrlError("channel must be 0..3")
        fcw = self._fcw(hz)
        actual = fcw * RASTER_HZ
        if actual < 400e3:
            print(f"warning: {actual:g} Hz is below the 400 kHz analog HPF cutoff",
                  file=sys.stderr)
        self._rmw(R_CH_FA[ch], FCW_MASK, fcw)
        return fcw, actual

    def set_amp(self, ch, amp):
        """Set channel `ch` DAC amplitude (Q1.15, 0x8000 = unity/full scale for a
        single tone). Warns if the enabled tones now sum past full scale."""
        if not 0 <= ch <= 3:
            raise CtrlError("channel must be 0..3")
        r = self._rmw(R_CH_FA[ch], 0xFFFF << 16, (amp & 0xFFFF) << 16)
        self._warn_if_clip()
        return r

    def dac_headroom(self):
        """Worst-case (peak-aligned) sum of the enabled TX tones' amplitudes as a
        fraction of DAC full scale. > 1.0 means the excitation can clip."""
        tx = self.reg_read(R_CH_EN) & 0xF
        total = sum(((self.reg_read(R_CH_FA[ch]) >> 16) & 0xFFFF)
                    for ch in range(4) if tx & (1 << ch))
        return total / float(AMP_DEFAULT)

    def _warn_if_clip(self):
        frac = self.dac_headroom()
        if frac > 1.0:
            print(f"WARNING: enabled DAC tones sum to {frac:.2f}x full scale — the "
                  f"excitation may clip. Lower a tone's amplitude (`amp <ch> <val>`) "
                  f"or let `channels` auto-balance them.", file=sys.stderr)

    def set_phase(self, ch, poff):
        """Set channel `ch` phase offset (0..15999; phase = poff/16000 * 2pi)."""
        if not 0 <= ch <= 3:
            raise CtrlError("channel must be 0..3")
        if not 0 <= poff < FCW_MAX:
            raise CtrlError(f"phase offset must be 0..{FCW_MAX-1}")
        shift = 16 if (ch & 1) else 0
        return self._rmw(R_PHASE[ch >> 1], FCW_MASK << shift,
                         (poff & FCW_MASK) << shift)

    def set_carrier(self, hz):
        """Convenience: set channel 0 carrier (single-tone bring-up)."""
        return self.set_freq(0, hz)

    # ---- packetizer config ----
    def set_channel_mask(self, tx_mask, rx_mask, adc=False):
        """CH_EN2: [3:0]TX tone, [7:4]RX demod, [8]raw-ADC monitor."""
        return self.reg_write(R_CH_EN, (tx_mask & 0xF) | ((rx_mask & 0xF) << 4)
                              | ((1 if adc else 0) << 8))

    def set_pkt_cfg(self, records_per_packet, payload_mask=None, fmt=0):
        """PKT_CFG4.  payload_mask defaults to the CURRENTLY ENABLED demod
        channels (read from CH_EN2) — never claim channels that aren't
        streaming: the mask must always describe the real frame layout."""
        if payload_mask is None:
            payload_mask = (self.reg_read(R_CH_EN) >> 4) & 0xF
        return self.reg_write(R_PKT_CFG, (records_per_packet & 0xFF)
                              | ((payload_mask & 0xF) << 8) | ((fmt & 0xF) << 12))

    @staticmethod
    def stride_words(demod_mask, adc):
        return PKT_HDR_WORDS + 2 * bin(demod_mask & 0xF).count("1") + (1 if adc else 0)

    def set_channels(self, demod_mask, adc=False, tx_mask=None, amp=None):
        """Host policy — the end user just picks channels and this keeps the DAC
        safe and the link efficient:
          * enable the given demod channels (+ optional raw-ADC),
          * size records_per_packet so each datagram fills close to the MTU,
          * AUTO-BALANCE the DAC amplitudes so the multitone sum can't clip:
            unity is split across the enabled TX tones (peak-aligned worst case),
            so 1 tone = full scale, 2 = half each, 4 = quarter each.
        Pass amp=<value> to set every enabled tone to a fixed amplitude instead.
        tx_mask defaults to demod_mask. Returns (records_per_packet, per_tone_amp).
        """
        if tx_mask is None:
            tx_mask = demod_mask
        stride_bytes = self.stride_words(demod_mask, adc) * 4
        rpp = max(1, min(255, MTU_PAYLOAD // stride_bytes))
        self.set_channel_mask(tx_mask, demod_mask, adc)
        self.set_pkt_cfg(rpp)

        n_tx = bin(tx_mask & 0xF).count("1")
        per = 0
        if n_tx:
            per = amp if amp is not None else max(1, AMP_DEFAULT // n_tx)
            for ch in range(4):
                if tx_mask & (1 << ch):
                    self._rmw(R_CH_FA[ch], 0xFFFF << 16, (per & 0xFFFF) << 16)
        return rpp, per

    # ---- reloadable FIR coefficients ----
    @staticmethod
    def check_rate(rate):
        """Validate a CIC decimation rate, returning it as an int.

        The PL ignores an out-of-range rate field rather than clamping it, so a
        bad value would silently leave the old rate in place while the PC
        believed it had changed. Reject it here instead.
        """
        r = int(rate)
        if not FIR_RATE_MIN <= r <= FIR_RATE_MAX:
            raise CtrlError(
                f"CIC rate {r} out of range {FIR_RATE_MIN}..{FIR_RATE_MAX}")
        if r & (r - 1) and (r // 1000) & (r // 1000 - 1):
            # Not fatal, but the R^4 gain step stops being an exact bit shift.
            raise CtrlError(
                f"CIC rate {r} is not a power-of-two multiple of 1000 "
                f"({FIR_RATES}); the R^4 gain change would need a multiplier "
                f"instead of a shift to normalise")
        return r

    def _fir_cmd(self, op, data=0, rate=0):
        """Write one REG3 command.

        rate=0 leaves the decimation rate untouched, which is what every write
        except the rate-carrying commit should send.
        """
        self._fir_tog ^= 1
        word = ((int(data) & 0xFFFF) | ((op & 0x3) << 16)
                | ((int(rate) & 0x1FFF) << 18)
                | (self._fir_tog << 31))
        return self.reg_write(R_FIR_CMD, word)

    def fir_load(self, coeffs, rate=None):
        """Load a FIR reload coefficient set into the PL loader over REG3.

        `coeffs` must be exactly FIR_NCOEF values — the full frame, padded if
        the design is shorter (use fir_design.loader_payload()).
        Sequence: reset index, push each, commit.

        rate : CIC decimation to apply with this filter, or None to leave the
               rate alone. It rides the COMMIT word so the coefficients and the
               sample rate they were designed for take effect together — the
               chain is never running a filter against the wrong rate. A rate
               change steps the output sample rate, so quiesce the packetizer
               and DMA around this call and re-arm afterwards.
        """
        rate = 0 if rate is None else self.check_rate(rate)
        coeffs = [int(c) for c in coeffs]
        if not coeffs:
            raise CtrlError("no coefficients to load")
        if len(coeffs) != FIR_NCOEF:
            raise CtrlError(
                f"{len(coeffs)} coefficients but the loader expects exactly "
                f"{FIR_NCOEF}; it streams NCOEF beats per commit and saturates "
                f"past the end, so this would silently load the wrong filter. "
                f"Use fir_design.loader_payload() to pad/validate.")
        self._fir_cmd(FIR_OP_RESET)
        for c in coeffs:
            if not -32768 <= c <= 32767:
                raise CtrlError(f"coefficient {c} does not fit signed 16-bit")
            self._fir_cmd(FIR_OP_PUSH, c)
        # The rate rides the commit: the PL applies it only on this opcode.
        self._fir_cmd(FIR_OP_COMMIT, rate=rate)
        return len(coeffs)

    # ---- Plan 07: triggering ----
    @staticmethod
    def sec_to_ticks(seconds):
        """Physical seconds -> PL timestamp counts (5 ns each)."""
        return int(round(seconds * PL_TICK_HZ))

    @staticmethod
    def ticks_to_sec(ticks):
        return ticks / float(PL_TICK_HZ)

    @staticmethod
    def mag_to_fix(frac):
        """Magnitude as a fraction of full scale -> fix32_30."""
        return int(round(frac * TRIG_MAG_SCALE))

    def trig_send(self, cfg):
        """Send a TrigCfg to the board and wait for its ack. Returns status (0)."""
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        pkt = struct.pack("<II", GMAGIC, self.seq) + cfg.pack_body()
        self.sock.sendto(pkt, self.addr)
        while True:
            try:
                buf, _ = self.sock.recvfrom(256)
            except socket.timeout:
                raise CtrlError("no trigger-config ack (is iza_replay running?)")
            if len(buf) < RSP.size:
                continue
            magic, seq, status, _val, _rlen, _rdata = RSP.unpack_from(buf)
            if magic == GMAGIC and seq == self.seq:
                if status != 0:
                    raise CtrlError(f"trigger cfg returned status {status}")
                return status

    def trig_off(self):
        """Disarm triggering."""
        return self.trig_send(TrigCfg(mode=TRIG_OFF, arm=0))

    def trig_test(self, out_mask=0b11):
        """Manually fire the actuation outputs (bit0=out0, bit1=out1) a few ms
        from now, for bench checkout — independent of the detection arm state."""
        return self._xact(OP_TRIG_TEST, target=out_mask & 0x3)

    # ---- SPI: raw ----
    def spi(self, bus, tx):
        """Full-duplex SPI transfer; returns rx bytes (same length as tx)."""
        return self._xact(OP_SPI_XFER, target=bus, data=bytes(tx))[1]

    # ---- AD9122 DAC (8-bit instruction, byte mode) ----
    def dac_write(self, addr, val):
        self.spi(SPI_DAC, [addr & 0x7F, val & 0xFF])

    def dac_read(self, addr):
        rx = self.spi(SPI_DAC, [0x80 | (addr & 0x7F), 0x00])
        return rx[1] if len(rx) >= 2 else None

    # HB1/HB2/HB3 Control = 0x1C/0x1D/0x1E.  In each, bit0 = "Bypass HBn"
    # (1 = bypass that interpolation stage); the modulation-mode field sits
    # above it (HB1[1:0] in 0x1C[2:1], HB2[5:0] in 0x1D[6:1], HB3[5:0] in
    # 0x1E[6:1]) and stays 0 for unmodulated baseband.  So 0x01 = bypassed:
    # interp=1 bypasses all three, interp=8 enables all three.
    _INTERP_HB = {
        1: (0x01, 0x01, 0x01),
        2: (0x00, 0x01, 0x01),
        4: (0x00, 0x00, 0x01),
        8: (0x00, 0x00, 0x00),
    }

    def dac_init(self, interp=2):
        """AD9122 byte-mode baseband bring-up (2x interpolation default).
        Requires the DAC chip released:
        SYS_CTRL0[4] (dac_chip_nreset) = 1, i.e. `run` first."""
        if interp not in self._INTERP_HB:
            raise CtrlError("interp must be 1, 2, 4, or 8")
        if not (self.reg_read(R_SYS_CTRL) & (1 << B_DAC_CHIP_NRST)):
            raise CtrlError("DAC chip held in reset (SYS_CTRL0 bit4=0) — run 'run' "
                            "before dac-init or the SPI path is dead")
        self.dac_write(0x00, 0x20)   # software reset
        self.dac_write(0x00, 0x00)   # release; SDIO input-only (4-wire), MSB-first
        self.dac_write(0x01, 0x00)   # power up I/Q DACs + data receiver
        # Data format (0x03): bit7=0 twos complement, bit6=0 I first,
        # bit5=0 no MSB swap, [1:0]=01 -> BYTE MODE, 8-bit interface bus.
        # Byte mode is CORRECT for this board: dac_data_out is a selectio_wiz
        # with SYSTEM_DATA_WIDTH=8 (eight LVDS pairs, DDR), with FRAME on its
        # own 1-bit OSERDES (frame_out).  Do not "fix" this to word mode -- the
        # 16-bit dac_output_wrapper port is serialized down to 8 pairs, so the
        # wrapper's width says nothing about the bus mode.
        self.dac_write(0x03, 0x01)
        self.dac_write(0x1B, 0xE4)   # datapath: bypass premod, sinc1, NCO (baseband)
        hb1, hb2, hb3 = self._INTERP_HB[interp]
        self.dac_write(0x1C, hb1)
        self.dac_write(0x1D, hb2)
        self.dac_write(0x1E, hb3)
        self.dac_write(0x10, 0x48)   # data-rate mode (FRAME pulse resets FIFO)
        self.dac_write(0x17, 0x04)   # FIFO phase offset (default midpoint)
        self.dac_write(0x18, 0x02)   # request FIFO soft align
        s18_req = self.dac_read(0x18)
        self.dac_write(0x18, 0x00)
        fifo_level = self.dac_read(0x19)
        s18_final = self.dac_read(0x18)
        # Datasheet "Example Start-Up Routine" expects 0x18 == 0x07 after the
        # align request (bit2 soft-align acknowledge set), and a FIFO level of
        # 0x1F / 0x0F / 0x07 -- anything else means the read/write pointers did
        # not align and the data interface is not reliable.
        return {"interp": interp,
                "fifo_0x18_after_req": s18_req,
                "fifo_0x19_level": fifo_level,
                "fifo_0x18_final": s18_final,
                "align_ack": bool((s18_req or 0) & 0x04),
                "level_ok": fifo_level in (0x1F, 0x0F, 0x07),
                "warnings_clear": (s18_final & 0xC0) == 0}

    # ---- AD9467 ADC (16-bit instruction, buffered; commit via 0xFF) ----
    @staticmethod
    def _adc_instr(rw, addr):
        word = ((rw & 1) << 15) | (addr & 0x1FFF)
        return [(word >> 8) & 0xFF, word & 0xFF]

    def adc_write(self, addr, val, commit=True):
        self.spi(SPI_ADC, self._adc_instr(0, addr) + [val & 0xFF])
        if commit:
            self.spi(SPI_ADC, self._adc_instr(0, 0xFF) + [0x01])

    def adc_read(self, addr):
        rx = self.spi(SPI_ADC, self._adc_instr(1, addr) + [0x00])
        return rx[2] if len(rx) >= 3 else None

    def adc_init(self, pattern="off"):
        if pattern not in ADC_PATTERNS:
            raise CtrlError(f"pattern must be one of {list(ADC_PATTERNS)}")
        self.adc_write(0x08, 0x00, commit=False)
        self.adc_write(0x14, 0x09, commit=False)
        self.adc_write(0x0D, ADC_PATTERNS[pattern], commit=False)
        self.spi(SPI_ADC, self._adc_instr(0, 0xFF) + [0x01])
        return f"adc_init: 2s-comp, pattern={pattern}, committed"


# ---------------------------------------------------------------- CLI
def fir_design_rates():
    """CIC rates the designer offers, without importing it at module load."""
    try:
        import fir_design as fd
        return list(fd.RATES)
    except Exception:
        return [1000, 2000, 4000, 8000]


def _int(s):
    return int(s, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True)
    ap.add_argument("--port", type=int, default=CTRL_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run");      sub.add_parser("reset")
    p = sub.add_parser("pga");      p.add_argument("gain_db", type=int,
                                                   help="PGA gain in dB (even, 6..26; higher=more gain)")
    p = sub.add_parser("pga-code"); p.add_argument("code", type=int,
                                                   help="raw 4-bit PGA code (0=26dB..10=6dB)")
    p = sub.add_parser("demod-input"); p.add_argument("sel", type=int, help="demod input: 0=ADC 1=loopback")
    p = sub.add_parser("dac-output");  p.add_argument("sel", type=int, help="DAC out: 0=tones 1=test/replay")
    p = sub.add_parser("carrier");  p.add_argument("hz", type=float, help="channel 0 carrier (Hz)")
    p = sub.add_parser("freq");     p.add_argument("ch", type=int); p.add_argument("hz", type=float)
    p = sub.add_parser("amp");      p.add_argument("ch", type=int); p.add_argument("val", type=_int)
    p = sub.add_parser("phase");    p.add_argument("ch", type=int); p.add_argument("poff", type=_int)
    p = sub.add_parser("channels",  help="enable demod channels + size packets to MTU")
    p.add_argument("demod_mask", type=_int, help="4-bit RX demod mask (e.g. 0x1, 0xF)")
    p.add_argument("--adc", action="store_true", help="also stream the raw-ADC monitor")
    p.add_argument("--tx", type=_int, default=None, help="TX tone mask (default = demod_mask)")
    p.add_argument("--amp", type=_int, default=None,
                   help="fixed per-tone amp (default: auto-balance to avoid clipping)")
    p = sub.add_parser("regwrite"); p.add_argument("reg", type=int); p.add_argument("value", type=_int)
    p = sub.add_parser("regread");  p.add_argument("reg", type=int)
    p = sub.add_parser("dac-init"); p.add_argument("--interp", type=int, default=2, choices=[1, 2, 4, 8])
    p = sub.add_parser("adc-init"); p.add_argument("--pattern", default="off", choices=list(ADC_PATTERNS))
    p = sub.add_parser("dac-write"); p.add_argument("addr", type=_int); p.add_argument("val", type=_int)
    p = sub.add_parser("dac-read");  p.add_argument("addr", type=_int)
    p = sub.add_parser("adc-write"); p.add_argument("addr", type=_int); p.add_argument("val", type=_int)
    p = sub.add_parser("adc-read");  p.add_argument("addr", type=_int)
    p = sub.add_parser("fir-load", help="upload FIR coefficients from a .coe file")
    p.add_argument("coe", help="path to a FIR .coe file")
    p.add_argument("--symmetric-half", action="store_true",
                   help="send only the folded half (legacy C_SYMMETRY=1 build); "
                        "default sends the full set the loader expects")
    p.add_argument("--rate", type=int, default=None, choices=FIR_RATES,
                   help="also set the CIC decimation rate with this commit")
    p = sub.add_parser("fir-design",
                       help="design a low-pass and load it (cutoff is -3 dB)")
    p.add_argument("cutoff", type=float, help="-3 dB cutoff (Hz)")
    p.add_argument("--taps", type=int, default=None,
                   help="pin the tap count (default: chosen)")
    p.add_argument("--rate", type=int, default=None, choices=fir_design_rates(),
                   help="pin the CIC decimation R (default: chosen)")
    p.add_argument("--mode", choices=("quality", "latency"), default="quality",
                   help="quality (sharpest) or latency (minimum group delay)")
    p.add_argument("--atten", type=float, default=80.0)
    p.add_argument("--cic-comp", action="store_true")
    p.add_argument("--no-rate", action="store_true",
                   help="do not change the CIC rate (default: apply the rate "
                        "the filter was designed for)")
    p.add_argument("--save", help="also write the .coe to this path")
    sub.add_parser("trig-off", help="disarm triggering")
    p = sub.add_parser("trig-soft", help="arm soft (no-pin) triggering for bring-up")
    p.add_argument("--ampch", type=int, default=0, help="amplitude demod channel 0..3")
    p.add_argument("--thr", type=float, default=0.02, help="excursion arm level (frac of FS)")
    p.add_argument("--mindiff", type=float, default=0.03, help="min peak-to-trough (frac of FS)")
    p.add_argument("--shift", type=int, default=12, help="baseline leaky shift")
    p.add_argument("--holdoff", type=float, default=0.050, help="debounce (s)")
    p.add_argument("--event", type=float, default=0.050, help="max bipolar-event span (s)")
    p.add_argument("--fixed-delay", type=float, default=0.0, help="fixed fire delay (s)")
    p.add_argument("--pulse", type=float, default=0.001, help="output pulse width (s)")
    p.add_argument("--polarity", type=int, default=0, help="0 peak-then-trough, 1 flipped")
    args = ap.parse_args()

    c = IzaCtrl(args.board, args.port)
    try:
        if args.cmd == "run":      print("run: SYS_CTRL0 =", hex(c.run()))
        elif args.cmd == "reset":  print("reset: SYS_CTRL0 =", hex(c.reset_all()))
        elif args.cmd == "pga":    print(f"pga: {args.gain_db} dB -> code {c.set_pga(args.gain_db)}")
        elif args.cmd == "pga-code": print("pga code:", hex(c.set_pga_code(args.code)))
        elif args.cmd == "demod-input": print("SYS_CTRL0 =", hex(c.set_demod_input(args.sel)))
        elif args.cmd == "dac-output":  print("SYS_CTRL0 =", hex(c.set_dac_output(args.sel)))
        elif args.cmd == "carrier":
            fcw, hz = c.set_carrier(args.hz); print(f"ch0 FCW={fcw} -> {hz:g} Hz")
        elif args.cmd == "freq":
            fcw, hz = c.set_freq(args.ch, args.hz); print(f"ch{args.ch} FCW={fcw} -> {hz:g} Hz")
        elif args.cmd == "amp":    print(f"ch{args.ch} amp:", hex(c.set_amp(args.ch, args.val)))
        elif args.cmd == "phase":  print(f"ch{args.ch} phase:", hex(c.set_phase(args.ch, args.poff)))
        elif args.cmd == "channels":
            rpp, per = c.set_channels(args.demod_mask, args.adc, args.tx, args.amp)
            print(f"channels: demod=0x{args.demod_mask:x} adc={args.adc} "
                  f"-> records/packet={rpp}, per-tone amp=0x{per:04x} "
                  f"(stride {c.stride_words(args.demod_mask, args.adc)*4}B)")
        elif args.cmd == "regwrite": print(f"reg{args.reg} <-", hex(c.reg_write(args.reg, args.value)))
        elif args.cmd == "regread":  print(f"reg{args.reg} =", hex(c.reg_read(args.reg)))
        elif args.cmd == "dac-init":
            r = c.dac_init(args.interp)
            print(f"dac-init: interp={r['interp']}x  word mode (16-bit), 2s comp\n"
                  f"  FIFO 0x18(after req)={r['fifo_0x18_after_req']:#04x} "
                  f"(expect 0x07, align_ack={r['align_ack']})\n"
                  f"  0x19 level={r['fifo_0x19_level']:#04x} "
                  f"(expect 0x1f/0x0f/0x07, level_ok={r['level_ok']})\n"
                  f"  0x18 final={r['fifo_0x18_final']:#04x}  "
                  f"warnings_clear={r['warnings_clear']}")
        elif args.cmd == "adc-init": print(c.adc_init(args.pattern))
        elif args.cmd == "dac-write": c.dac_write(args.addr, args.val); print("ok")
        elif args.cmd == "dac-read":  print(hex(c.dac_read(args.addr)))
        elif args.cmd == "adc-write": c.adc_write(args.addr, args.val); print("ok (committed)")
        elif args.cmd == "adc-read":  print(hex(c.adc_read(args.addr)))
        elif args.cmd == "fir-load":
            import fir_design as fd
            taps, width = fd.read_coe(args.coe)
            # Full set by default: the PL loader streams exactly NCOEF values and
            # saturates past the end, so a half-length push loads a wrong filter
            # without reporting anything.
            rset = fd.loader_payload(
                fd.reload_set(taps, symmetric=args.symmetric_half))
            n = c.fir_load(rset, rate=args.rate)
            print(f"fir-load: {args.coe} -> {len(taps)} taps, loaded {n} reload "
                  f"coeffs ({'symmetric half' if args.symmetric_half else 'full set'})")
        elif args.cmd == "fir-design":
            import fir_design as fd
            f = fd.make_filter(args.cutoff, taps=args.taps, atten_db=args.atten,
                               cic_comp=args.cic_comp, mode=args.mode,
                               rate=args.rate)
            if args.save:
                f.write_coe(args.save)
                print(f"wrote {args.save}")
            rset = f.reload_values()
            # Apply the rate the filter was designed for, unless told not to.
            n = c.fir_load(rset, rate=None if args.no_rate else f.rate)
            m, i = f.metrics, f.info
            print(f"fir-design: -3 dB {m['f3_hz']:.4g} Hz, R={f.rate}, "
                  f"{len(f.ints)} taps ({f.method}) -> loaded {n} reload coeffs")
            print(f"  DC gain {i['dc_sum']} = 2^{i['shift']} -> datapath shift "
                  f"{i['shift']} bits; group delay {m['group_delay_s']*1e6:.1f} us")
        elif args.cmd == "trig-off":  c.trig_off(); print("triggering disarmed")
        elif args.cmd == "trig-soft":
            cfg = TrigCfg(
                mode=TRIG_SOFT, arm=1, amp_channel=args.ampch,
                polarity=args.polarity, phase_mask=0, emit_candidates=1,
                amp_threshold=c.mag_to_fix(args.thr),
                min_peak_diff=c.mag_to_fix(args.mindiff),
                baseline_shift=args.shift,
                holdoff_ticks=c.sec_to_ticks(args.holdoff),
                event_ticks=c.sec_to_ticks(args.event),
                delay_mode=DLY_FIXED,
                fixed_delay_ticks=c.sec_to_ticks(args.fixed_delay),
                pulse_width_ticks=c.sec_to_ticks(args.pulse))
            c.trig_send(cfg)
            print(f"soft trigger armed on ch{args.ampch}: thr={args.thr} "
                  f"mindiff={args.mindiff}; events stream to UDP {EVT_PORT}")
    except CtrlError as e:
        sys.exit(f"control error: {e}")


if __name__ == "__main__":
    main()
