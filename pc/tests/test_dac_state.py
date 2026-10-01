"""Run from pc/: python -B -m unittest discover -s tests -v (Qt-free)."""

import unittest

import iza_ctrl
from iza_gui import dac_state as ds

RUNNING = iza_ctrl.SYS_RUN                                   # 0x3F, DAC chip released
HELD = 0x00                                                  # after Stop / Reset
GOOD_INIT = {"align_ack": True, "level_ok": True, "warnings_clear": True}


class DacInitTrackerTests(unittest.TestCase):
    def setUp(self):
        self.t = ds.DacInitTracker()

    def poll(self, r0, fmt):
        """One status poll: SYS_CTRL0 then (only if released) DAC 0x03."""
        a = self.t.on_sys_ctrl(r0)
        b = self.t.on_format(fmt if r0 & (1 << iza_ctrl.B_DAC_CHIP_NRST) else None)
        return a or b

    def test_connect_to_initialized_board_is_ok_without_attention(self):
        self.assertEqual(self.t.state, ds.UNKNOWN)
        self.assertTrue(self.poll(RUNNING, 0x01))
        self.assertEqual(self.t.state, ds.OK)
        self.assertFalse(self.t.needs_attention)

    def test_connect_to_uninitialized_board_needs_init(self):
        self.poll(RUNNING, 0x00)
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.LOST))

    def test_stop_start_without_init_is_flagged_until_initialize(self):
        self.poll(RUNNING, 0x01)
        self.assertTrue(self.t.on_reset_command())
        self.assertEqual(self.t.reason, ds.HELD)
        self.assertFalse(self.poll(HELD, None))          # same state: no churn
        self.poll(RUNNING, 0x00)                          # Start: chip at defaults
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.LOST))
        self.assertTrue(self.t.on_init_result(GOOD_INIT))
        self.assertEqual(self.t.state, ds.OK)
        self.assertFalse(self.poll(RUNNING, 0x01))

    def test_reset_between_polls_is_caught_by_the_format_probe(self):
        self.poll(RUNNING, 0x01)
        # reset + run from outside the GUI, both inside one poll interval
        self.poll(RUNNING, 0x00)
        self.assertTrue(self.t.needs_attention)

    def test_no_spi_reply_has_its_own_reason(self):
        self.poll(RUNNING, 0x01)
        self.poll(RUNNING, 0xFF)
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.NO_REPLY))
        self.assertEqual(self.t.short_text, "⚠ DAC not answering")
        self.poll(RUNNING, 0x01)                         # answering again, setup intact
        self.assertEqual(self.t.state, ds.OK)

    def test_suspect_survives_a_not_answering_spell(self):
        self.poll(RUNNING, 0x00)
        self.t.on_init_result(dict(GOOD_INIT, align_ack=False))
        suspect = self.t.reason
        self.poll(RUNNING, 0xFF)                         # glitch: no SPI reply
        self.assertEqual(self.t.reason, ds.NO_REPLY)
        self.poll(RUNNING, 0xFF)
        self.poll(RUNNING, 0x01)                         # answers again: still suspect
        self.assertEqual((self.t.state, self.t.reason), (ds.SUSPECT, suspect))
        self.t.on_init_result(GOOD_INIT)
        self.assertEqual(self.t.state, ds.OK)

    def test_reset_during_a_not_answering_spell_forgets_the_suspect(self):
        self.t.on_init_error("no response from board")
        self.poll(RUNNING, 0xFF)
        self.poll(0x00, None)                            # a real reset happened
        self.poll(RUNNING, 0x01)                         # then an init (e.g. CLI)
        self.assertEqual(self.t.state, ds.OK)

    def test_release_from_reset_moves_held_to_lost_even_if_probe_is_lost(self):
        self.t.on_reset_command()
        self.poll(HELD, None)
        self.t.on_sys_ctrl(RUNNING)                      # Start ...
        self.t.on_format(None)                           # ... but the probe is lost
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.LOST))
        self.assertTrue(self.poll(RUNNING, 0x01))        # e.g. CLI init in between
        self.assertEqual(self.t.state, ds.OK)

    def test_init_refused_while_held_keeps_the_start_advice(self):
        held_msg = ("DAC chip held in reset (SYS_CTRL0 bit4=0) — run 'run' "
                    "before dac-init or the SPI path is dead")
        self.t.on_reset_command()
        self.assertFalse(self.t.on_init_error(held_msg))
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.HELD))
        self.poll(RUNNING, 0x01)                         # from OK, reset outside the GUI
        self.t.on_init_error(held_msg)
        self.assertEqual(self.t.reason, ds.HELD)

    def test_link_lost_greys_ok_but_keeps_warnings(self):
        self.poll(RUNNING, 0x01)
        self.assertTrue(self.t.on_link_lost())
        self.assertEqual((self.t.state, self.t.reason), (ds.UNKNOWN, ds.NO_LINK))
        self.assertFalse(self.t.needs_attention)
        self.poll(RUNNING, 0x01)                         # brief blip: back to OK
        self.assertEqual(self.t.state, ds.OK)
        self.t.on_init_result(dict(GOOD_INIT, level_ok=False))
        self.assertFalse(self.t.on_link_lost())          # SUSPECT survives a blip
        self.poll(RUNNING, 0x01)
        self.assertEqual(self.t.state, ds.SUSPECT)

    def test_short_text_names_the_next_step(self):
        self.assertEqual(self.t.short_text, "")
        self.t.on_reset_command()
        self.assertEqual(self.t.short_text, "⚠ DAC in reset: ▶ Start, then ① Initialize")
        self.poll(RUNNING, 0x00)
        self.assertEqual(self.t.short_text, "⚠ DAC needs ① Initialize")
        self.t.on_init_result(GOOD_INIT)
        self.assertEqual(self.t.short_text, "")

    def test_lost_probe_keeps_previous_state(self):
        self.poll(RUNNING, 0x01)
        self.assertFalse(self.t.on_format(None))
        self.assertEqual(self.t.state, ds.OK)

    def test_init_from_cli_clears_needs_init(self):
        self.poll(RUNNING, 0x00)
        self.poll(RUNNING, 0x01)
        self.assertEqual(self.t.state, ds.OK)

    def test_failed_alignment_stays_suspect_until_clean_init(self):
        self.poll(RUNNING, 0x00)
        bad = dict(GOOD_INIT, align_ack=False)
        self.t.on_init_result(bad)
        self.assertEqual(self.t.state, ds.SUSPECT)
        self.poll(RUNNING, 0x01)                          # byte mode alone isn't enough
        self.assertEqual(self.t.state, ds.SUSPECT)
        self.t.on_init_result(GOOD_INIT)
        self.assertEqual(self.t.state, ds.OK)

    def test_init_error_is_suspect_and_a_later_reset_downgrades(self):
        self.t.on_init_error("no response from board")
        self.assertEqual(self.t.state, ds.SUSPECT)
        self.assertIn("no response", self.t.reason)
        self.poll(RUNNING, 0x00)
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.LOST))
        self.t.on_init_error("x")
        self.poll(HELD, None)
        self.assertEqual((self.t.state, self.t.reason), (ds.NEEDS_INIT, ds.HELD))

    def test_disconnect_forgets(self):
        self.poll(RUNNING, 0x00)
        self.assertTrue(self.t.reset())
        self.assertEqual(self.t.state, ds.UNKNOWN)
        self.assertFalse(self.t.needs_attention)

    def test_init_checks(self):
        self.assertTrue(ds.init_checks_passed(GOOD_INIT))
        self.assertFalse(ds.init_checks_passed(dict(GOOD_INIT, level_ok=False)))
        self.assertFalse(ds.init_checks_passed("adc_init: ok"))
        self.assertFalse(ds.init_checks_passed(None))


if __name__ == "__main__":
    unittest.main()
