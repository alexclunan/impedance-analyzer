"""Run from pc/: python -B -m unittest discover -s tests -v

Frequency parsing/formatting (Qt-free) and the FreqSpinBox widget (needs Qt;
skipped if no binding is installed)."""

import os
import unittest

from iza_gui.units import format_hz, is_partial_hz, parse_hz, search_hz


class ParseTests(unittest.TestCase):
    def test_accepted_spellings(self):
        cases = {
            "750000": 750000.0, "500k": 500e3, "500 kHz": 500e3,
            "500khz": 500e3, "1.5M": 1.5e6, "1.5 MHz": 1.5e6, "1.5mhz": 1.5e6,
            "2e6": 2e6, "2E6 Hz": 2e6, " 12.5 kHz ": 12500.0, ".5M": 5e5,
            "200 Hz": 200.0, "0": 0.0, "1.0125 MHz": 1012500.0,
        }
        for text, hz in cases.items():
            with self.subTest(text=text):
                self.assertAlmostEqual(parse_hz(text), hz)

    def test_rejected(self):
        for text in ("", "k", "abc", "1.2.3", "5 kHz extra", "-5k", "5 kk", "2e"):
            with self.subTest(text=text):
                self.assertIsNone(parse_hz(text))

    def test_partial_entries_are_intermediate(self):
        for text in ("", "1.", ".", "2e", "2e-", "500 k", "500 kH", "1.5 M"):
            with self.subTest(text=text):
                self.assertTrue(is_partial_hz(text))
        for text in ("abc", "5 kHz x", "1.2.3", "-5"):
            with self.subTest(text=text):
                self.assertFalse(is_partial_hz(text))

    def test_search_reads_rec_rate_presets_and_typed_values(self):
        cases = {
            "100 khz  (÷2)": 100e3, "1 khz  (÷200)": 1e3, "7500": 7500.0,
            "5 khz": 5e3, "5k": 5e3, "200 hz": 200.0, "5e3": 5e3,
        }
        for text, hz in cases.items():
            with self.subTest(text=text):
                self.assertAlmostEqual(search_hz(text), hz)
        self.assertIsNone(search_hz("full"))


class FormatTests(unittest.TestCase):
    def test_units_and_trailing_zeros(self):
        cases = {
            0: "0 Hz", 750: "750 Hz", 12500: "12.5 kHz", 500000: "500 kHz",
            1e6: "1 MHz", 1012500: "1.0125 MHz", 8e6: "8 MHz",
            999999.6: "1 MHz",           # rounds to whole Hz before picking a unit
        }
        for hz, text in cases.items():
            with self.subTest(hz=hz):
                self.assertEqual(format_hz(hz), text)

    def test_round_trips_every_tone_grid_point(self):
        for fcw in range(0, 641):           # 0 .. 8 MHz on the 12.5 kHz grid
            hz = fcw * 12500.0
            self.assertEqual(parse_hz(format_hz(hz)), hz)

    def test_decimals_keep_sub_hz_resolution(self):
        self.assertEqual(format_hz(250.5, decimals=2), "250.5 Hz")
        self.assertEqual(format_hz(1234.56, decimals=2), "1.23456 kHz")
        self.assertAlmostEqual(parse_hz(format_hz(1234.56, 2)), 1234.56)


class ExtremeInputTests(unittest.TestCase):
    """Absurd exponents must never raise (the old rec-rate regex never did)."""

    def test_huge_exponents_are_infinite_not_errors(self):
        for text in ("1e9999999", "1e999999k", "999e999998",
                     "1e99999999999999999999"):
            with self.subTest(text=text):
                self.assertEqual(parse_hz(text), float("inf"))
                self.assertEqual(search_hz(text), float("inf"))

    def test_tiny_exponents_and_zero_mantissas_are_zero(self):
        for text in ("1e-9999999", "1e-99999999999999999999",
                     "0e99999999999999999999", "0.0e99999999999999999999k"):
            with self.subTest(text=text):
                self.assertEqual(parse_hz(text), 0.0)

    def test_long_runs_of_spaces_do_not_backtrack(self):
        import time
        t0 = time.perf_counter()
        for n in (200, 2000):
            self.assertFalse(is_partial_hz(" " * n + "x"))
            self.assertIsNone(parse_hz("1" + " " * n + "x"))
            self.assertIsNone(parse_hz("1" * n + "x"))
        self.assertLess(time.perf_counter() - t0, 0.5)


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from pyqtgraph.Qt import QtCore, QtGui, QtTest, QtWidgets
    from iza_gui.widgets import FreqSpinBox
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
except Exception as e:                       # no Qt binding: skip widget tests
    _QT_ERROR = e
else:
    _QT_ERROR = None


@unittest.skipIf(_QT_ERROR is not None, f"Qt unavailable: {_QT_ERROR}")
class FreqSpinBoxTests(unittest.TestCase):
    def setUp(self):
        self.box = self.make_box(QtCore.QLocale(QtCore.QLocale.English,
                                                QtCore.QLocale.UnitedStates))
        self.finished = []
        self.box.editingFinished.connect(lambda: self.finished.append(self.box.value()))

    @staticmethod
    def make_box(locale):
        box = FreqSpinBox(0, 8_000_000, 12500, 500000)
        box.setLocale(locale)
        box.setValue(250000)
        box.setValue(500000)                 # re-render in this locale
        return box

    def type_text(self, text, box=None):
        """Select all, type key by key (the real per-keystroke path), Return."""
        box = box or self.box
        box.lineEdit().selectAll()
        QtTest.QTest.keyClicks(box, text)
        QtTest.QTest.keyClick(box, QtCore.Qt.Key_Return)

    def test_shows_value_with_units(self):
        self.assertEqual(self.box.text(), "500 kHz")
        self.box.setValue(1012500)
        self.assertEqual(self.box.text(), "1.0125 MHz")

    def test_typed_units_set_hz(self):
        for text, hz in (("1.5 MHz", 1.5e6), ("750000", 750000), ("2e6", 2e6),
                         ("625k", 625000), ("1.5M", 1.5e6)):
            with self.subTest(text=text):
                self.type_text(text)
                self.assertEqual(self.box.value(), hz)
                self.assertEqual(self.finished[-1], hz)

    def test_keystrokes_do_not_commit_prefixes(self):
        changes = []
        self.box.valueChanged.connect(changes.append)
        self.type_text("1.5 MHz")
        self.assertEqual(changes, [1.5e6])     # only the finished entry

    def test_out_of_range_clamps(self):
        self.type_text("9 MHz")
        self.assertEqual(self.box.value(), 8e6)
        self.assertEqual(self.box.text(), "8 MHz")
        self.type_text("1e9999999")             # absurd exponent: clamped, no error
        self.assertEqual(self.box.value(), 8e6)

    def test_unfinished_or_bad_text_reverts_to_previous_value(self):
        for text in ("2e", "2e-", "abc", ""):
            with self.subTest(text=text):
                self.box.setValue(500000)
                self.type_text(text)
                self.assertEqual(self.box.value(), 500000)
                self.assertEqual(self.box.text(), "500 kHz")
        self.assertEqual(self.box.valueFromText("garbage"), 500000)

    def test_half_typed_unit_is_completed(self):
        self.type_text("625 kH")
        self.assertEqual(self.box.value(), 625000)
        self.type_text("1.5 MH")
        self.assertEqual(self.box.value(), 1.5e6)

    def test_value_matches_displayed_text(self):
        self.type_text("18749.6")               # box shows whole Hz
        self.assertEqual(self.box.value(), 18750)
        self.assertEqual(self.box.text(), "18.75 kHz")

    def test_validator_states(self):
        V = QtGui.QValidator
        self.assertEqual(self.box.validate("1.5 MHz", 0)[0], V.Acceptable)
        self.assertEqual(self.box.validate("1.5 M", 0)[0], V.Acceptable)
        self.assertEqual(self.box.validate("1.", 0)[0], V.Acceptable)     # 1 Hz
        self.assertEqual(self.box.validate("2e", 0)[0], V.Intermediate)
        self.assertEqual(self.box.validate("500 kH", 0)[0], V.Intermediate)
        self.assertEqual(self.box.validate("9 MHz", 0)[0], V.Intermediate)
        self.assertEqual(self.box.validate("1e9999999", 0)[0], V.Intermediate)
        self.assertEqual(self.box.validate("abc", 0)[0], V.Invalid)
        self.assertEqual(self.box.validate("1,5", 0)[0], V.Invalid)      # not here

    def test_arrow_step_is_one_grid_step(self):
        self.box.stepBy(1)
        self.assertEqual(self.box.value(), 512500)
        self.assertEqual(self.box.text(), "512.5 kHz")

    def test_typed_value_can_step_away_from_a_range_edge(self):
        for start, key, want in ((0, QtCore.Qt.Key_Down, 987500),
                                 (8e6, QtCore.Qt.Key_Up, 1012500)):
            with self.subTest(start=start):
                self.box.setValue(start)
                self.box.lineEdit().selectAll()
                QtTest.QTest.keyClicks(self.box, "1 MHz")   # not committed yet
                QtTest.QTest.keyClick(self.box, key)
                self.assertEqual(self.box.value(), want)

    def test_input_length_is_capped(self):
        self.assertEqual(self.box.lineEdit().maxLength(), 32)

    def test_comma_decimal_locale(self):
        box = self.make_box(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))
        box.setValue(1012500)
        self.assertEqual(box.text(), "1,0125 MHz")
        for text, hz in (("1,5 MHz", 1.5e6),
                         ("2.5 MHz", 2.5e6),         # a lone '.' is still decimal
                         ("1.000,5 kHz", 1000500),   # '.' grouping with ',' decimal
                         ("1.000.000", 1e6)):        # several '.' = grouping
            with self.subTest(text=text):
                self.type_text(text, box)
                self.assertEqual(box.value(), hz)


if __name__ == "__main__":
    unittest.main()
