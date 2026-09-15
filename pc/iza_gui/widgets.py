"""Small shared widgets: collapsible section and status LED."""

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from . import theme


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
