"""console_panel.py — Vivado-Tcl-style command log.

Shows every command the GUI sends to the board and the board's response,
timestamped and color-coded:
  * cyan  ">"  — a command was issued
  * plain      — a transaction and its response (writes end in "verified"
                 because every written register is read back and compared)
  * amber      — a write whose readback did NOT match the value sent
  * red        — a failed transaction (timeout / board error)
"""

import time

from pyqtgraph.Qt import QtGui, QtWidgets

from . import theme

MAX_LINES = 5000

_COLOR = {
    "cmd": theme.ACCENT_HI,
    "ok": theme.TEXT,
    "warn": theme.WARN,
    "err": theme.BAD,
}
_PREFIX = {"cmd": "> ", "ok": "  ", "warn": "! ", "err": "✗ "}


class ConsolePanel(QtWidgets.QWidget):
    """Bottom command-log pane; feed it with append(kind, text)."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)

        head = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Command log")
        title.setProperty("heading", True)
        title.setToolTip(
            "Every command sent to the board and its response. Writes are "
            "read back and marked “verified” when the value matches.")
        head.addWidget(title)
        head.addSpacing(12)

        self.chk_poll = QtWidgets.QCheckBox("Show status polling")
        self.chk_poll.setToolTip(
            "Also log the automatic once-per-second register poll that keeps "
            "the indicators fresh (11 reads/s — noisy, off by default)")
        self.chk_poll.toggled.connect(
            lambda on: setattr(self.client, "log_polling", on))
        head.addWidget(self.chk_poll)

        head.addStretch(1)
        btn_clear = QtWidgets.QPushButton("Clear")
        btn_clear.setToolTip("Empty the command log")
        btn_clear.clicked.connect(lambda: self.text.clear())
        head.addWidget(btn_clear)
        lay.addLayout(head)

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(MAX_LINES)
        font = QtGui.QFont("Consolas")
        font.setPointSize(9)
        self.text.setFont(font)
        self.text.setStyleSheet(
            f"background: {theme.PLOT_BG}; border: 1px solid {theme.BORDER};")
        lay.addWidget(self.text, 1)

        client.log.connect(self.append)
        client.error.connect(self._on_error)

    def append(self, kind, text):
        ts = time.strftime("%H:%M:%S")
        color = _COLOR.get(kind, theme.TEXT)
        prefix = _PREFIX.get(kind, "  ")
        safe = (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))
        sb = self.text.verticalScrollBar()
        stick = sb.value() >= sb.maximum() - 4      # keep following the tail
        self.text.appendHtml(
            f'<span style="color:{theme.TEXT_DIM}">{ts}</span> '
            f'<span style="color:{color}">{prefix}{safe}</span>')
        if stick:
            sb.setValue(sb.maximum())

    def _on_error(self, label, msg):
        # high-level failures (e.g. "not connected") that never reached a
        # transaction; transaction failures are already logged by the ctrl
        if label.startswith("__"):
            return
        self.append("err", f"{label}: {msg}")
