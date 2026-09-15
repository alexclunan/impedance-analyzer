"""register_map.py — register catalogs for the Registers tab.

Three devices:
  * FPGA — the 16 AXI control registers of the signal-processing pipeline
    (rasterized-DDS bitstream; map documented in iza_ctrl.py).
  * DAC  — Analog Devices AD9122 (SPI), Table 10 of the datasheet (Rev. C).
  * ADC  — Analog Devices AD9467 (SPI), Table 13 of the datasheet (Rev. E).

Each register carries a plain-English description and (where useful) a
bitfield decoder used for the value tooltip, so users who are not familiar
with the internals can still read the state.
"""

from collections import namedtuple

# hi/lo — bit range (inclusive); decode — dict {value: meaning}, a callable
# value -> str, or None (show the raw number).
Field = namedtuple("Field", "hi lo name decode")

# writable=False → the Set button is disabled (status / ID registers).
RegDef = namedtuple("RegDef", "addr name brief fields writable")


def _f(hi, lo, name, decode=None):
    return Field(hi, lo, name, decode)


ONOFF = {0: "off", 1: "on"}
YESNO = {0: "no", 1: "yes"}


def extract(value, hi, lo):
    return (value >> lo) & ((1 << (hi - lo + 1)) - 1)


def layout_tooltip(reg):
    """Static description tooltip: brief + the exact bit mapping."""
    lines = [f"0x{reg.addr:02X}  {reg.name}", reg.brief]
    if reg.fields:
        lines.append("Bit map:")
        for f in reg.fields:
            bits = f"[{f.hi}]" if f.hi == f.lo else f"[{f.hi}:{f.lo}]"
            line = f"  {bits} {f.name}"
            if isinstance(f.decode, dict):
                opts = ", ".join(f"{k}={v}" for k, v in sorted(f.decode.items()))
                if len(line) + len(opts) > 76:      # keep tooltip lines readable
                    line += ":\n" + "\n".join(
                        f"        {k} = {v}" for k, v in sorted(f.decode.items()))
                else:
                    line += f"  ({opts})"
            lines.append(line)
    if not reg.writable:
        lines.append("(read-only — cannot be set)")
    return "\n".join(lines)


def decode_tooltip(reg, value):
    """Multi-line text decoding `value` against the register's bitfields."""
    lines = [f"{reg.name} = 0x{value:X}  ({value})"]
    for f in reg.fields:
        v = extract(value, f.hi, f.lo)
        bits = f"[{f.hi}]" if f.hi == f.lo else f"[{f.hi}:{f.lo}]"
        if callable(f.decode):
            meaning = f" — {f.decode(v)}"
        elif isinstance(f.decode, dict):
            meaning = f" — {f.decode[v]}" if v in f.decode else ""
        else:
            meaning = ""
        lines.append(f"  {bits} {f.name} = {v}{meaning}")
    return "\n".join(lines)


# ===========================================================================
# FPGA — AXI control registers (index 0..15)
# ===========================================================================
def _pga_db(code):
    return f"{26 - 2 * code} dB input gain"


def _fcw_hz(fcw):
    return f"{fcw * 12500 / 1e3:g} kHz output"


def _amp_pct(a):
    return f"{a / 0x8000 * 100:.1f} % of full scale"


def _poff_deg(p):
    return f"{p / 16000 * 360:.1f}° phase offset"


def _ticks_us(t):
    return f"{t / 200.0:.3f} µs (at 5 ns/count)"


def _chfa(ch):
    return RegDef(
        5 + ch, f"CH{ch}_FREQ_AMP",
        f"Tone {ch}: output frequency (steps of 12.5 kHz) and amplitude.",
        [_f(13, 0, "Frequency word (x12.5 kHz)", _fcw_hz),
         _f(31, 16, "Amplitude (0x8000 = 100 %)", _amp_pct)],
        True)


FPGA_REGS = [
    RegDef(0, "SYS_CTRL0",
           "Master control: reset lines (1 = released), run, and signal "
           "routing. 0x3F = normal running state.",
           [_f(0, 0, "DDS reset released", YESNO),
            _f(1, 1, "Pipeline reset released", YESNO),
            _f(2, 2, "DAC-path reset released", YESNO),
            _f(3, 3, "FIFO reset released", YESNO),
            _f(4, 4, "DAC chip out of reset", YESNO),
            _f(5, 5, "RUN (measurement running)", YESNO),
            _f(6, 6, "Measurement input (demod)",
               {0: "analog input (ADC)",
                1: "internal loopback (am_modulator / replay)"}),
            _f(7, 7, "(unused — no hardware effect)"),
            _f(8, 8, "DAC output source",
               {0: "signal generator tones (dds_cos)",
                1: "internal test / replay signal"})],
           True),
    RegDef(1, "ANALOG1",
           "Input amplifier (PGA) gain code. Code is inverse to gain: "
           "gain = 26 − 2×code dB (code 0 = 26 dB … code 10 = 6 dB).",
           [_f(3, 0, "PGA gain code", _pga_db)],
           True),
    RegDef(2, "CHANNEL_EN",
           "Which tone generators and measurement channels are active.",
           [_f(3, 0, "TX tone enables (bit per tone 0-3)"),
            _f(7, 4, "Demodulator enables (bit per channel 0-3)"),
            _f(8, 8, "Stream raw ADC samples", ONOFF)],
           True),
    RegDef(3, "FIR_COEFF_CMD",
           "Reloadable FIR coefficient loader command. The PC writes coefficients "
           "one at a time here; the PL stages them and, on commit, streams them "
           "into all four demod FIRs. Written by the FIR loader — not a normal "
           "data register.\n"
           "Exactly 999 coefficients must be pushed per commit (NCOEF in "
           "fir_coeff_loader.v, hardcoded to match the 999-tap non-symmetric "
           "FIR). Commit always streams NCOEF beats and the write pointer "
           "saturates past the end, so a wrong count silently loads a different "
           "filter rather than reporting an error.",
           [_f(15, 0, "Coefficient (signed 16-bit)"),
            _f(17, 16, "Opcode",
               {0: "nop", 1: "reset index", 2: "push coeff", 3: "commit (reload)"}),
            _f(30, 18, "CIC decimation rate 1000..8000 (0 = leave unchanged; "
                       "applied on commit only)"),
            _f(31, 31, "Strobe toggle (flips each write)")],
           True),
    RegDef(4, "PKT_CFG",
           "Network packet sizing: how many measurement records are packed "
           "into each UDP packet.",
           [_f(7, 0, "Records per packet")],
           True),
    _chfa(0), _chfa(1), _chfa(2), _chfa(3),
    RegDef(9, "TRIG1_T_LO",
           "Trigger output 1 fire timestamp, low 32 bits (PL counts, 5 ns "
           "each). Written by the firmware when a hardware trigger fires. "
           "(Was the unused tone 0/1 phase offset.)",
           [_f(31, 0, "Fire time low word", _ticks_us)], True),
    RegDef(10, "TRIG1_T_HI",
           "Trigger output 1 fire timestamp, high 32 bits.",
           [_f(31, 0, "Fire time high word")], True),
    RegDef(11, "TRIG1_W",
           "Trigger output 1 pulse width (PL counts, 5 ns each; 0 = output 1 "
           "disabled).",
           [_f(31, 0, "Pulse width", _ticks_us)], True),
    RegDef(12, "TRIG_T_LO",
           "Trigger fire target timestamp, low 32 bits (PL counts, 5 ns each). "
           "Written by the firmware when a hardware trigger fires.",
           [_f(31, 0, "Fire time low word", _ticks_us)], True),
    RegDef(13, "TRIG_T_HI",
           "Trigger fire target timestamp, high 32 bits.",
           [_f(31, 0, "Fire time high word")], True),
    RegDef(14, "TRIG_W",
           "Actuation output pulse width (PL counts, 5 ns each).",
           [_f(31, 0, "Pulse width", _ticks_us)], True),
    RegDef(15, "TRIG_CMD",
           "PL fire-engine command (Stage 2). Written by the firmware; spare "
           "in the Stage-1 bitstream.",
           [_f(0, 0, "Armed", YESNO),
            _f(1, 1, "Mode (0 soft, 1 hardware)"),
            _f(8, 8, "Fire strobe", YESNO)], True),
]


# ===========================================================================
# DAC — AD9122 (SPI), datasheet Table 10 (Rev. C)
# ===========================================================================
DAC_REGS = [
    RegDef(0x00, "Comm",
           "Serial-port setup and software reset.",
           [_f(7, 7, "SDIO bidirectional", YESNO),
            _f(6, 6, "LSB first", YESNO),
            _f(5, 5, "Reset (1 = held in reset)", YESNO)],
           True),
    RegDef(0x01, "Power control",
           "Power-down switches for the DAC cores and data receiver.",
           [_f(7, 7, "I DAC powered down", YESNO),
            _f(6, 6, "Q DAC powered down", YESNO),
            _f(5, 5, "Data receiver powered down", YESNO),
            _f(4, 4, "Aux ADC (temp sensor) powered down", YESNO)],
           True),
    RegDef(0x03, "Data format",
           "Input data format and bus width. This board uses byte mode "
           "(8-bit bus) with twos-complement data → correct value 0x01.",
           [_f(7, 7, "Data format",
               {0: "twos complement", 1: "unsigned binary"}),
            _f(6, 6, "Q data first", YESNO),
            _f(5, 5, "MSB swap", YESNO),
            _f(1, 0, "Bus width",
               {0: "word mode (16-bit)", 1: "byte mode (8-bit) — correct "
                "for this board", 2: "nibble mode (4-bit)", 3: "invalid"})],
           True),
    RegDef(0x04, "Interrupt enable",
           "Enable interrupts for PLL / sync / FIFO events.",
           [_f(7, 7, "PLL lock lost IRQ", ONOFF),
            _f(6, 6, "PLL locked IRQ", ONOFF),
            _f(5, 5, "Sync lost IRQ", ONOFF),
            _f(4, 4, "Sync locked IRQ", ONOFF),
            _f(1, 1, "FIFO Warning 1 IRQ", ONOFF),
            _f(0, 0, "FIFO Warning 2 IRQ", ONOFF)],
           True),
    RegDef(0x05, "Interrupt enable 2",
           "Enable interrupts for AED/SED data-pattern compare events.",
           [_f(4, 4, "AED compare pass IRQ", ONOFF),
            _f(3, 3, "AED compare fail IRQ", ONOFF),
            _f(2, 2, "SED compare fail IRQ", ONOFF)],
           True),
    RegDef(0x06, "Event flag",
           "Latched status: PLL, sync and FIFO warnings.",
           [_f(7, 7, "PLL lock lost", YESNO),
            _f(6, 6, "PLL locked", YESNO),
            _f(5, 5, "Sync signal lost", YESNO),
            _f(4, 4, "Sync signal locked", YESNO),
            _f(3, 3, "FIFO Warning 1", YESNO),
            _f(2, 2, "FIFO Warning 2", YESNO)],
           True),
    RegDef(0x07, "Event flag 2",
           "Latched status: data-pattern compare results.",
           [_f(7, 7, "AED compare pass", YESNO),
            _f(6, 6, "AED compare fail", YESNO),
            _f(5, 5, "SED compare fail", YESNO)],
           True),
    RegDef(0x08, "Clock receiver control",
           "DACCLK/REFCLK duty-cycle and crossing corrections (default 0x3F).",
           [_f(7, 7, "DACCLK duty correction", ONOFF),
            _f(6, 6, "REFCLK duty correction", ONOFF),
            _f(5, 5, "DACCLK cross-correction", ONOFF),
            _f(4, 4, "REFCLK cross-correction", ONOFF)],
           True),
    RegDef(0x0A, "PLL control",
           "Clock-multiplier PLL enable and manual VCO band.",
           [_f(7, 7, "PLL enable", ONOFF),
            _f(6, 6, "PLL manual enable", ONOFF),
            _f(5, 0, "Manual VCO band")],
           True),
    RegDef(0x0C, "PLL control 2",
           "PLL loop bandwidth and charge-pump current.",
           [_f(7, 6, "Loop bandwidth"),
            _f(4, 0, "Charge-pump current")],
           True),
    RegDef(0x0D, "PLL control 3",
           "PLL divider settings (N0/N1/N2) and cross-control enable.",
           [_f(7, 6, "N2"), _f(5, 5, "Cross-control enable", ONOFF),
            _f(3, 2, "N0"), _f(1, 0, "N1")],
           True),
    RegDef(0x0E, "PLL status",
           "Read-only: PLL lock state and VCO control voltage.",
           [_f(7, 7, "PLL locked", YESNO),
            _f(4, 1, "VCO control voltage")],
           False),
    RegDef(0x0F, "PLL status 2",
           "Read-only: VCO band readback.",
           [_f(5, 0, "VCO band readback")],
           False),
    RegDef(0x10, "Sync control",
           "Multi-chip sync enable, edge selection and averaging.",
           [_f(7, 7, "Sync enable", ONOFF),
            _f(6, 6, "Data/FIFO rate toggle"),
            _f(3, 3, "Rising-edge sync", YESNO),
            _f(2, 0, "Sync averaging")],
           True),
    RegDef(0x11, "Sync control 2",
           "Requested sync phase.",
           [_f(5, 0, "Sync phase request")],
           True),
    RegDef(0x12, "Sync status",
           "Read-only: sync lock state.",
           [_f(7, 7, "Sync lost", YESNO),
            _f(6, 6, "Sync locked", YESNO)],
           False),
    RegDef(0x13, "Sync status 2",
           "Read-only: sync phase readback (6.2 format).",
           [_f(7, 0, "Sync phase readback")],
           False),
    RegDef(0x15, "Data receiver status",
           "Read-only: LVDS input signal levels (FRAME/DCI/data high-low).",
           [_f(7, 7, "FRAME level high"), _f(6, 6, "FRAME level low"),
            _f(5, 5, "DCI level high"), _f(4, 4, "DCI level low"),
            _f(3, 3, "Data level high"), _f(2, 2, "Data level low")],
           False),
    RegDef(0x16, "DCI delay",
           "Delay applied to the DCI input clock.",
           [_f(1, 0, "DCI delay")],
           True),
    RegDef(0x17, "FIFO control",
           "Requested FIFO phase offset (data-interface FIFO depth point).",
           [_f(2, 0, "FIFO phase offset")],
           True),
    RegDef(0x18, "FIFO status",
           "FIFO warnings and soft-align handshake (dac-init uses this).",
           [_f(7, 7, "FIFO Warning 1", YESNO),
            _f(6, 6, "FIFO Warning 2", YESNO),
            _f(1, 1, "Soft-align acknowledge", YESNO),
            _f(0, 0, "Soft-align request", YESNO)],
           True),
    RegDef(0x19, "FIFO level",
           "Read-only: thermometer-coded FIFO fill level (expect 0x0F).",
           [_f(7, 0, "FIFO level")],
           False),
    RegDef(0x1B, "Datapath control",
           "Digital datapath feature bypasses (premod, sinc⁻¹, NCO…).",
           [_f(7, 7, "Bypass premod", YESNO),
            _f(6, 6, "Bypass sinc⁻¹ filter", YESNO),
            _f(5, 5, "Bypass NCO", YESNO),
            _f(3, 3, "NCO gain", ONOFF),
            _f(2, 2, "Bypass phase comp / dc offset", YESNO),
            _f(1, 1, "Select sideband"),
            _f(0, 0, "Send I data to Q DAC", YESNO)],
           True),
    RegDef(0x1C, "HB1 control",
           "First half-band interpolation filter: mode and bypass.",
           [_f(2, 1, "HB1 mode"), _f(0, 0, "Bypass HB1", YESNO)],
           True),
    RegDef(0x1D, "HB2 control",
           "Second half-band interpolation filter: mode and bypass.",
           [_f(6, 1, "HB2 mode"), _f(0, 0, "Bypass HB2", YESNO)],
           True),
    RegDef(0x1E, "HB3 control",
           "Third half-band interpolation filter: mode and bypass.",
           [_f(6, 1, "HB3 mode"), _f(0, 0, "Bypass HB3", YESNO)],
           True),
    RegDef(0x1F, "Chip ID",
           "Read-only: chip identifier (AD9122 = 0x08).",
           [_f(7, 0, "Chip ID")],
           False),
    RegDef(0x30, "FTW byte 0 (LSB)",
           "NCO frequency tuning word, bits [7:0].", [], True),
    RegDef(0x31, "FTW byte 1",
           "NCO frequency tuning word, bits [15:8].", [], True),
    RegDef(0x32, "FTW byte 2",
           "NCO frequency tuning word, bits [23:16].", [], True),
    RegDef(0x33, "FTW byte 3 (MSB)",
           "NCO frequency tuning word, bits [31:24].", [], True),
    RegDef(0x34, "NCO phase offset LSB",
           "NCO phase offset, bits [7:0].", [], True),
    RegDef(0x35, "NCO phase offset MSB",
           "NCO phase offset, bits [15:8].", [], True),
    RegDef(0x36, "NCO FTW update",
           "Handshake to latch a new NCO frequency word.",
           [_f(3, 3, "FRAME FTW acknowledge", YESNO),
            _f(2, 2, "FRAME FTW request", YESNO),
            _f(1, 1, "Update FTW acknowledge", YESNO),
            _f(0, 0, "Update FTW request", YESNO)],
           True),
    RegDef(0x38, "I phase adj LSB",
           "I-channel phase correction, bits [7:0].", [], True),
    RegDef(0x39, "I phase adj MSB",
           "I-channel phase correction, bits [9:8].", [], True),
    RegDef(0x3A, "Q phase adj LSB",
           "Q-channel phase correction, bits [7:0].", [], True),
    RegDef(0x3B, "Q phase adj MSB",
           "Q-channel phase correction, bits [9:8].", [], True),
    RegDef(0x3C, "I DAC offset LSB",
           "I-channel dc offset, bits [7:0].", [], True),
    RegDef(0x3D, "I DAC offset MSB",
           "I-channel dc offset, bits [15:8].", [], True),
    RegDef(0x3E, "Q DAC offset LSB",
           "Q-channel dc offset, bits [7:0].", [], True),
    RegDef(0x3F, "Q DAC offset MSB",
           "Q-channel dc offset, bits [15:8].", [], True),
    RegDef(0x40, "I DAC FS adjust",
           "I-channel full-scale output current adjust, bits [7:0].", [], True),
    RegDef(0x41, "I DAC control",
           "I DAC sleep + full-scale adjust MSBs.",
           [_f(7, 7, "I DAC sleep", YESNO), _f(1, 0, "FS adjust [9:8]")],
           True),
    RegDef(0x42, "I aux DAC data",
           "Auxiliary I DAC output value, bits [7:0].", [], True),
    RegDef(0x43, "I aux DAC control",
           "Auxiliary I DAC sign / direction / sleep + data MSBs.",
           [_f(7, 7, "Sign"), _f(6, 6, "Current direction"),
            _f(5, 5, "Sleep", YESNO), _f(1, 0, "Aux DAC [9:8]")],
           True),
    RegDef(0x44, "Q DAC FS adjust",
           "Q-channel full-scale output current adjust, bits [7:0].", [], True),
    RegDef(0x45, "Q DAC control",
           "Q DAC sleep + full-scale adjust MSBs.",
           [_f(7, 7, "Q DAC sleep", YESNO), _f(1, 0, "FS adjust [9:8]")],
           True),
    RegDef(0x46, "Q aux DAC data",
           "Auxiliary Q DAC output value, bits [7:0].", [], True),
    RegDef(0x47, "Q aux DAC control",
           "Auxiliary Q DAC sign / direction / sleep + data MSBs.",
           [_f(7, 7, "Sign"), _f(6, 6, "Current direction"),
            _f(5, 5, "Sleep", YESNO), _f(1, 0, "Aux DAC [9:8]")],
           True),
    RegDef(0x48, "Die temp range control",
           "Temperature-sensor bias currents and capacitor value.",
           [_f(6, 4, "FS current"), _f(3, 1, "Reference current"),
            _f(0, 0, "Capacitor value")],
           True),
    RegDef(0x49, "Die temp LSB",
           "Read-only: die temperature, bits [7:0].", [], False),
    RegDef(0x4A, "Die temp MSB",
           "Read-only: die temperature, bits [15:8].", [], False),
    RegDef(0x67, "SED control",
           "Sample-error-detection compare enable and results.",
           [_f(7, 7, "SED compare enable", ONOFF),
            _f(5, 5, "Sample error detected", YESNO),
            _f(3, 3, "Autoclear enable", ONOFF),
            _f(1, 1, "Compare fail", YESNO),
            _f(0, 0, "Compare pass", YESNO)],
           True),
    RegDef(0x68, "SED compare I0 LSB", "Expected pattern I0 [7:0].", [], True),
    RegDef(0x69, "SED compare I0 MSB", "Expected pattern I0 [15:8].", [], True),
    RegDef(0x6A, "SED compare Q0 LSB", "Expected pattern Q0 [7:0].", [], True),
    RegDef(0x6B, "SED compare Q0 MSB", "Expected pattern Q0 [15:8].", [], True),
    RegDef(0x6C, "SED compare I1 LSB", "Expected pattern I1 [7:0].", [], True),
    RegDef(0x6D, "SED compare I1 MSB", "Expected pattern I1 [15:8].", [], True),
    RegDef(0x6E, "SED compare Q1 LSB", "Expected pattern Q1 [7:0].", [], True),
    RegDef(0x6F, "SED compare Q1 MSB", "Expected pattern Q1 [15:8].", [], True),
    RegDef(0x70, "SED errors I LSB",
           "Read-only: bit errors detected on I, bits [7:0].", [], False),
    RegDef(0x71, "SED errors I MSB",
           "Read-only: bit errors detected on I, bits [15:8].", [], False),
    RegDef(0x72, "SED errors Q LSB",
           "Read-only: bit errors detected on Q, bits [7:0].", [], False),
    RegDef(0x73, "SED errors Q MSB",
           "Read-only: bit errors detected on Q, bits [15:8].", [], False),
    RegDef(0x7F, "Revision",
           "Read-only: die revision.",
           [_f(5, 2, "Revision")],
           False),
]


# ===========================================================================
# ADC — AD9467 (SPI), datasheet Table 13 (Rev. E)
# ===========================================================================
def _adc_fsr(v):
    return {0: "2.0 V p-p", 6: "2.1 V p-p", 7: "2.2 V p-p", 8: "2.3 V p-p",
            9: "2.4 V p-p", 10: "2.5 V p-p (default)"}.get(v, "reserved")


def _adc_buf(v):
    if v == 0:
        return "nominal (0 %)"
    return f"{v * 10 if v <= 0x35 else (v - 0x40) * 10:+d} %"


ADC_REGS = [
    RegDef(0x00, "chip_port_config",
           "Serial-port setup and soft reset (bit pattern is mirrored in "
           "both nibbles; default 0x18).",
           [_f(6, 6, "LSB first", ONOFF),
            _f(5, 5, "Soft reset", ONOFF)],
           True),
    RegDef(0x01, "chip_id",
           "Read-only: chip identifier (AD9467 = 0x50).",
           [_f(7, 0, "Chip ID")],
           False),
    RegDef(0x02, "chip_grade",
           "Read-only: speed-grade variant.",
           [_f(6, 4, "Child ID", {1: "200 MSPS", 2: "250 MSPS"})],
           False),
    RegDef(0x08, "modes",
           "Chip power mode.",
           [_f(1, 0, "Power mode",
               {0: "chip run (normal)", 1: "full power-down"})],
           True),
    RegDef(0x0D, "test_io",
           "Digital output test pattern (replaces real samples when set).",
           [_f(5, 5, "Reset PN-long generator", ONOFF),
            _f(4, 4, "Reset PN-short generator", ONOFF),
            _f(3, 0, "Output test mode",
               {0: "off (normal data)", 1: "midscale short", 2: "+FS short",
                3: "−FS short", 4: "checkerboard", 5: "PN 23 sequence",
                6: "PN 9 sequence", 7: "one/zero word toggle"})],
           True),
    RegDef(0x0F, "adc_input",
           "Analog input options.",
           [_f(6, 6, "External VREF", ONOFF),
            _f(2, 2, "Analog disconnect", ONOFF)],
           True),
    RegDef(0x10, "offset",
           "Digital offset adjustment in LSBs (twos complement, ±127).",
           [_f(7, 0, "Offset (twos complement)",
               lambda v: f"{v - 256 if v > 127 else v} LSB")],
           True),
    RegDef(0x14, "output_mode",
           "Output data format and enable. This design uses twos "
           "complement (value 0x09 after adc-init).",
           [_f(4, 4, "Digital outputs disabled", YESNO),
            _f(2, 2, "Output invert", ONOFF),
            _f(1, 0, "Data format",
               {0: "offset binary", 1: "twos complement — used here",
                2: "Gray code"})],
           True),
    RegDef(0x15, "output_adjust",
           "LVDS output drive-current adjustment.",
           [_f(3, 3, "Coarse LVDS adjust",
               {0: "3.0 mA", 1: "1.71 mA"}),
            _f(2, 0, "Drive current",
               {1: "3.0 mA", 2: "2.79 mA", 3: "2.57 mA", 4: "2.35 mA",
                5: "2.14 mA", 6: "1.93 mA", 7: "1.71 mA"})],
           True),
    RegDef(0x16, "output_phase",
           "Output clock (DCO) phase.",
           [_f(7, 7, "DCO output invert", ONOFF)],
           True),
    RegDef(0x18, "vref",
           "Input full-scale voltage range.",
           [_f(3, 0, "Full-scale range", _adc_fsr)],
           True),
    RegDef(0x2C, "analog_input",
           "Input coupling mode.",
           [_f(2, 2, "Coupling",
               {0: "AC coupling", 1: "DC coupling"})],
           True),
    RegDef(0x36, "buffer_current_1",
           "Analog input buffer bias current 1 (tune for linearity).",
           [_f(7, 2, "Buffer current", _adc_buf)],
           True),
    RegDef(0x107, "buffer_current_2",
           "Analog input buffer bias current 2 (tune for linearity).",
           [_f(7, 2, "Buffer current", _adc_buf)],
           True),
    RegDef(0xFF, "device_update",
           "Write 0x01 to commit buffered register writes to the chip "
           "(the driver does this automatically after each write).",
           [_f(0, 0, "Transfer buffered writes", ONOFF)],
           True),
]
