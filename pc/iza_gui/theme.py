"""Dark, LabOne-flavoured theme: a Qt stylesheet + pyqtgraph colors.

Zurich LabOne uses a clean panelled look with teal/blue accents; we render it
dark (matches the existing pyqtgraph scope and reads well for a live scope).
Colours are exposed as constants so the panels stay consistent.
"""

import os
import tempfile

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

# --- palette ---------------------------------------------------------------
BG        = "#1b1f27"   # window background
PANEL     = "#242a34"   # group boxes / cards
PANEL_HI  = "#2d3540"   # hovered / raised
BORDER    = "#38424f"
TEXT      = "#d7dde5"
TEXT_DIM  = "#8a94a2"
ACCENT    = "#12b5cb"   # ZI-ish teal
ACCENT_HI = "#3fd0e2"
GOOD      = "#3ecf8e"   # green LED / run
WARN      = "#f2b03d"
BAD       = "#e5533c"   # red LED / over-range
PLOT_BG   = "#12151b"

# per demod channel trace colours (match iza_plotter's intent, brighter)
CH_COLORS = [
    (245, 205, 60),    # ch0 amber
    (60, 200, 230),    # ch1 cyan
    (225, 120, 210),   # ch2 magenta
    (120, 220, 130),   # ch3 green
]
ADC_COLOR = (200, 140, 255)
FFT_COLOR = (90, 200, 255)
MATH_COLOR = (255, 255, 255)


def channel_color(ch):
    return CH_COLORS[ch % len(CH_COLORS)]


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def BAD_RGB():
    return _hex_rgb(BAD)


def GOOD_RGB():
    return _hex_rgb(GOOD)


def _make_arrow_icons():
    """Render small spinbox arrow pixmaps to files QSS can reference.

    Qt stylesheets cannot draw CSS border-triangles on the ::up-arrow /
    ::down-arrow subcontrols (they render as filled rectangles); the arrow
    subcontrols only accept an `image:`.  Requires a QApplication.
    """
    d = os.path.join(tempfile.gettempdir(), "iza_gui_icons")
    os.makedirs(d, exist_ok=True)
    shapes = {"up": [(1, 6), (9, 6), (5, 1)],
              "down": [(1, 1), (9, 1), (5, 6)]}
    paths = {}
    for name, pts in shapes.items():
        for suffix, color in (("", TEXT), ("_dim", TEXT_DIM)):
            path = os.path.join(d, f"arrow_{name}{suffix}.png")
            pm = QtGui.QPixmap(10, 8)
            pm.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pm)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(color))
            p.drawPolygon(QtGui.QPolygonF(
                [QtCore.QPointF(x, y) for x, y in pts]))
            p.end()
            pm.save(path, "PNG")
            paths[name + suffix] = path.replace("\\", "/")  # QSS wants /
    return paths


def apply(app):
    """Apply the dark theme to a QApplication and to pyqtgraph globals."""
    pg.setConfigOption("background", PLOT_BG)
    pg.setConfigOption("foreground", TEXT)
    pg.setConfigOptions(antialias=True)
    icons = _make_arrow_icons()
    qss = (_QSS
           .replace("%%ARROW_UP%%", icons["up"])
           .replace("%%ARROW_DOWN%%", icons["down"])
           .replace("%%ARROW_UP_DIM%%", icons["up_dim"])
           .replace("%%ARROW_DOWN_DIM%%", icons["down_dim"]))
    app.setStyleSheet(qss)


_QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-size: 12px;
}}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {BG};
}}
QLabel {{ background: transparent; }}
QLabel[dim="true"] {{ color: {TEXT_DIM}; }}
QLabel[heading="true"] {{ color: {ACCENT_HI}; font-weight: 600; }}

QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 8px 8px 8px 8px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {ACCENT_HI};
}}

QPushButton {{
    background: {PANEL_HI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{ background: {BORDER}; }}
QPushButton:pressed {{ background: {ACCENT}; color: #06232a; }}
QPushButton:disabled {{ color: {TEXT_DIM}; background: {PANEL}; }}
QPushButton[accent="true"] {{
    background: {ACCENT}; color: #06232a; border: 1px solid {ACCENT_HI};
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{ background: {ACCENT_HI}; }}
QPushButton[toggle="true"] {{ text-align: left; padding-left: 8px; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {PLOT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {ACCENT};
}}
/* Explicit up/down button geometry: styling the spinbox body without the
   subcontrols can collapse the up-button's hit region (only the down arrow
   was clickable). */
QSpinBox, QDoubleSpinBox {{
    padding-right: 20px;            /* room for the button column */
    min-height: 22px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px; height: 12px;
    background: {PANEL_HI};
    border-left: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    border-top-right-radius: 4px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px; height: 12px;
    background: {PANEL_HI};
    border-left: 1px solid {BORDER};
    border-bottom-right-radius: 4px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {ACCENT};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("%%ARROW_UP%%");
    width: 10px; height: 8px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("%%ARROW_DOWN%%");
    width: 10px; height: 8px;
}}
QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off,
QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:off {{
    image: url("%%ARROW_UP_DIM%%");
}}
QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off,
QDoubleSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:off {{
    image: url("%%ARROW_DOWN_DIM%%");
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {PANEL}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}
QCheckBox {{ spacing: 6px; background: transparent; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid {BORDER}; background: {PLOT_BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT_HI}; }}

QProgressBar {{
    background: {PLOT_BG}; border: 1px solid {BORDER}; border-radius: 4px;
    text-align: center; height: 14px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; top: -1px; }}
QTabBar::tab {{
    background: {PANEL}; border: 1px solid {BORDER};
    padding: 6px 16px; margin-right: 2px;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
}}
QTabBar::tab:selected {{ background: {ACCENT}; color: #06232a; font-weight: 600; }}

QScrollBar:vertical {{ background: {BG}; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {PANEL_HI}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QSplitter::handle {{ background: {BORDER}; }}
"""
