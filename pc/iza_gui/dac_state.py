"""dac_state.py — tracks whether the AD9122 DAC still holds its dac_init setup.

SYS_CTRL0 bit 4 holds the DAC chip in reset while it is 0, and that reset puts
the chip's SPI registers back to power-on defaults (word mode instead of byte
mode, interpolation and FIFO alignment lost).  'Start' releases the reset but
does not re-run dac_init, so without this check the GUI reads RUNNING while the
TX output is wrong (seen as a ~+3.35 V DC level on SMA1 with the tones off).

The tracker is fed from the 1 s status poll (SYS_CTRL0 plus a read of the DAC's
Data-format register, 0x03) and from the GUI's own commands.  It is Qt-free so
it can be unit-tested.
"""

import iza_ctrl

FORMAT_REG = 0x03        # AD9122 Data format
BUS_WIDTH_MASK = 0x03    # 0x03[1:0]: 00 word (power-on default), 01 byte, 11 invalid
BYTE_MODE = 0x01         # what dac_init writes

UNKNOWN = "unknown"         # not connected, or not polled yet
OK = "ok"                   # dac_init setup is in place
NEEDS_INIT = "needs-init"   # reset or never initialized
SUSPECT = "suspect"         # init failed or its FIFO checks did not pass

HELD = ("DAC held in reset (stopped). Press ▶ Start, then "
        "① Initialize DAC + ADC.")
LOST = ("DAC lost its setup (it was reset). Press ① Initialize DAC + ADC.")
NO_REPLY = ("DAC not answering on SPI (reads 0xFF). Check the DAC board and its "
            "power; Initialize can't work until it answers.")
NO_LINK = "no control link"

# iza_ctrl.dac_init's refusal while SYS_CTRL0 bit 4 is 0
_HELD_ERROR = "held in reset"


def init_checks_passed(result):
    """True if a dac_init() return value reports a clean FIFO alignment."""
    if not isinstance(result, dict):
        return False
    return all(result.get(k) for k in ("align_ack", "level_ok", "warnings_clear"))


class DacInitTracker:
    """Each on_* method returns True when the state or its reason changed."""

    def __init__(self):
        self.state = UNKNOWN
        self.reason = ""
        # the SUSPECT reason a not-answering spell interrupted: if the DAC
        # answers again in byte mode it goes back to SUSPECT, not to OK
        self._suspect_reason = None

    @property
    def needs_attention(self):
        return self.state in (NEEDS_INIT, SUSPECT)

    @property
    def short_text(self):
        """One-line status-bar text naming the next step ('' if none)."""
        if not self.needs_attention:
            return ""
        if self.reason == HELD:
            return "⚠ DAC in reset: ▶ Start, then ① Initialize"
        if self.reason == NO_REPLY:
            return "⚠ DAC not answering"
        return "⚠ DAC needs ① Initialize"

    def _set(self, state, reason=""):
        if reason != NO_REPLY:
            self._suspect_reason = None     # any other verdict ends the spell
        if (state, reason) == (self.state, self.reason):
            return False
        self.state, self.reason = state, reason
        return True

    def reset(self):
        """(Dis)connected: nothing is known until the next poll."""
        return self._set(UNKNOWN)

    def on_link_lost(self):
        """The control link is down (e.g. the board is rebooting). A reboot
        can wipe the DAC setup, so stop claiming OK; warnings stay up."""
        if self.state == OK:
            return self._set(UNKNOWN, NO_LINK)
        return False

    def on_sys_ctrl(self, r0):
        """A status poll's SYS_CTRL0 value."""
        if not r0 & (1 << iza_ctrl.B_DAC_CHIP_NRST):
            return self._set(NEEDS_INIT, HELD)
        if self.reason == HELD:
            # released since (Start): the reset is over but its damage isn't,
            # whether or not this poll's 0x03 probe gets through
            return self._set(NEEDS_INIT, LOST)
        return False

    def on_format(self, fmt):
        """A status poll's DAC 0x03 readback (None = not read: chip held in
        reset, or the probe was lost)."""
        if fmt is None:
            return False
        if fmt == 0xFF:                           # SPI not answering at all
            if self.state == SUSPECT:
                self._suspect_reason = self.reason
            return self._set(NEEDS_INIT, NO_REPLY)
        if (fmt & BUS_WIDTH_MASK) != BYTE_MODE:   # 0x00 = power-on defaults
            return self._set(NEEDS_INIT, LOST)
        # Byte mode means the setup survived, or was redone (e.g. from the CLI).
        # A failed or suspect GUI init only clears with a clean one.
        if self._suspect_reason is not None:
            return self._set(SUSPECT, self._suspect_reason)
        if self.state in (UNKNOWN, NEEDS_INIT):
            return self._set(OK)
        return False

    def on_init_result(self, result):
        """A dac_init() return value from the GUI."""
        if init_checks_passed(result):
            return self._set(OK)
        return self._set(SUSPECT, "DAC FIFO alignment check failed. "
                                  "Re-run ① Initialize DAC + ADC.")

    def on_init_error(self, msg):
        """dac_init() raised on the board link (e.g. a lost reply, or it
        refused because the chip is held in reset)."""
        if _HELD_ERROR in msg:
            return self._set(NEEDS_INIT, HELD)    # Start is the next step
        return self._set(SUSPECT, f"DAC initialize failed ({msg}). "
                                  "Re-run ① Initialize DAC + ADC.")

    def on_reset_command(self):
        """The GUI's Stop / Reset succeeded: the DAC chip is now in reset."""
        return self._set(NEEDS_INIT, HELD)
