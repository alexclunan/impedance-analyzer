"""Small shared widgets: collapsible section, status LED, frequency spin box."""

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from . import theme
from .units import format_hz, is_partial_hz, parse_hz


class Led(QtWidgets.QLabel):
    """A tiny round status light."""

    def __init__(self, diameter=12, parent=None):
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter, diameter)
        self._color = QtGui.QColor(theme.TEXT_DIM)

    def set_color(self, color):
        self._color = QtGui.QColor(color)
        self.update()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(0, 0, self._d, self._d)


class FreqSpinBox(QtWidgets.QDoubleSpinBox):
    """A frequency spin box that holds Hz but accepts and shows SI units.

    Type '750000', '500k', '500 kHz', '1.5M', '1.5 MHz' or '2e6'; the value is
    shown back as '500 kHz' / '1.0125 MHz'.  A typed value outside the range is
    clamped to it; text that isn't a frequency reverts to the value from before
    the edit.  In a comma-decimal locale ',' is the decimal mark, as in the
    other spin boxes."""

    _WIDEST = "888.8875 kHz"      # sizes the box for the longest typical text

    def __init__(self, lo, hi, step, val, decimals=0, parent=None):
        super().__init__(parent)
        self.setDecimals(decimals)          # Hz resolution of the stored value
        self.setRange(lo, hi)
        self.setSingleStep(step)
        # Commit only the finished text: with tracking on, every parsable
        # prefix ('2' of '2e6') would become the value along the way.
        self.setKeyboardTracking(False)
        self.lineEdit().setMaxLength(32)    # no frequency needs more
        # stepEnabled() follows the typed text: repaint the arrows as it changes
        self.lineEdit().textChanged.connect(self.update)
        self.setValue(val)

    def _comma(self):
        return self.locale().decimalPoint() == ","

    def _norm(self, text):
        """Typed text in the parser's syntax ('.' decimal, no grouping)."""
        if self._comma():
            # with a ',' present, or several '.', a '.' can only be grouping
            if "," in text or text.count(".") > 1:
                text = text.replace(".", "")
            text = text.replace(",", ".")
        return text

    def _parse(self, text):
        return parse_hz(self._norm(text))

    def textFromValue(self, value):
        text = format_hz(value, self.decimals())
        return text.replace(".", ",") if self._comma() else text

    def valueFromText(self, text):
        hz = self._parse(text)
        # round like setValue() does, so value() always matches the text
        return self.value() if hz is None else round(hz, self.decimals())

    def validate(self, text, pos):
        hz = self._parse(text)
        if hz is not None:
            ok = self.minimum() <= hz <= self.maximum()
            state = QtGui.QValidator.Acceptable if ok else QtGui.QValidator.Intermediate
        elif is_partial_hz(self._norm(text)):
            state = QtGui.QValidator.Intermediate
        else:
            state = QtGui.QValidator.Invalid
        return state, text, pos

    def stepEnabled(self):
        # Judge the arrows by the typed text when it parses: with keyboard
        # tracking off the committed value lags it, and Qt checks this before
        # stepBy() reads the text (so '1 MHz' typed over '0 Hz' couldn't step
        # down).
        hz = self._parse(self.lineEdit().text())
        if hz is None or self.isReadOnly() or self.wrapping():
            return super().stepEnabled()
        A = QtWidgets.QAbstractSpinBox
        flags = A.StepEnabledFlag.StepNone if hasattr(A, "StepEnabledFlag") else A.StepNone
        if hz < self.maximum():
            flags |= A.StepUpEnabled
        if hz > self.minimum():
            flags |= A.StepDownEnabled
        return flags

    def fixup(self, text):
        # Qt calls this for text that isn't Acceptable. Clamp an out-of-range
        # entry here (CorrectToNearestValue would bound a zero placeholder, not
        # the typed value) and finish a half-typed unit ('500 kH'). Anything
        # else is returned as-is, so the box reverts to its previous value.
        hz = self._parse(text)
        if hz is None and text.rstrip()[-1:] in ("h", "H"):
            hz = self._parse(text.rstrip() + "z")
        if hz is None:
            return text
        return self.textFromValue(min(max(hz, self.minimum()), self.maximum()))

    def sizeHint(self):
        # the base hint only measures the min/max texts ('0 Hz', '8 MHz')
        hint = super().sizeHint()
        fm = self.fontMetrics()
        base = max(fm.horizontalAdvance(self.textFromValue(self.minimum())),
                   fm.horizontalAdvance(self.textFromValue(self.maximum())))
        extra = fm.horizontalAdvance(self._WIDEST) - base
        if extra > 0:
            hint.setWidth(hint.width() + extra)
        return hint

    def minimumSizeHint(self):
        return self.sizeHint()


class CollapsibleSection(QtWidgets.QWidget):
    """A titled section with a toggle header that shows/hides its body.

    Add child widgets to `.body_layout` (a QVBoxLayout)."""

    def __init__(self, title, expanded=True, parent=None):
        super().__init__(parent)
        self._btn = QtWidgets.QPushButton()
        self._btn.setProperty("toggle", True)
        self._btn.setCheckable(True)
        self._btn.setChecked(expanded)
        self._title = title
        self._btn.clicked.connect(self._on_toggle)

        self._body = QtWidgets.QWidget()
        self.body_layout = QtWidgets.QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(8, 4, 4, 6)
        self.body_layout.setSpacing(6)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._btn)
        lay.addWidget(self._body)
        self._body.setVisible(expanded)
        self._refresh_title()

    def _on_toggle(self):
        self._body.setVisible(self._btn.isChecked())
        self._refresh_title()

    def _refresh_title(self):
        arrow = "▾" if self._btn.isChecked() else "▸"  # ▾ / ▸
        self._btn.setText(f"  {arrow}  {self._title}")

    def add(self, widget):
        self.body_layout.addWidget(widget)

    def add_layout(self, layout):
        self.body_layout.addLayout(layout)


def labeled_row(label, *widgets, stretch_label=90):
    """A QWidget holding [label ...widgets] in a horizontal row."""
    w = QtWidgets.QWidget()
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    lbl = QtWidgets.QLabel(label)
    lbl.setMinimumWidth(stretch_label)
    lbl.setProperty("dim", True)
    lay.addWidget(lbl)
    for wid in widgets:
        lay.addWidget(wid)
    lay.addStretch(1)
    return w
