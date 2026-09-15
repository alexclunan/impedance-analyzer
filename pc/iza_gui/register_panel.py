"""register_panel.py — the Registers tab.

One compact table per device (FPGA / DAC AD9122 / ADC AD9467) listing every
documented register: address, name, live value, and a per-row refresh button.
Editing a value cell and pressing Enter writes the register (then reads it
back).  Hovering a value shows the decoded bitfields; hovering a name shows
the register's description.

Update policy (per user spec): all registers are read once when the board is
connected; after that a register is re-read only when (a) a GUI command that
affects it completes, (b) its row refresh button is clicked, or (c) a
device-wide "Read all" is requested.
"""

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from . import register_map as rm
from . import theme
from .widgets import CollapsibleSection

_DEVICES = ("fpga", "dac", "adc")
_REGS = {"fpga": rm.FPGA_REGS, "dac": rm.DAC_REGS, "adc": rm.ADC_REGS}
_HEXW = {"fpga": 8, "dac": 2, "adc": 2}     # value width in hex digits

COL_ADDR, COL_NAME, COL_VAL, COL_BTN = range(4)


def _reader(dev, ctrl, addr):
    if dev == "fpga":
        return ctrl.reg_read(addr)
    if dev == "dac":
        return ctrl.dac_read(addr)
    return ctrl.adc_read(addr)


def _writer(dev, ctrl, addr, val):
    if dev == "fpga":
        ctrl.reg_write(addr, val)
    elif dev == "dac":
        ctrl.dac_write(addr, val)
    else:
        ctrl.adc_write(addr, val)
    return _reader(dev, ctrl, addr)          # read back the result


class _RegTable(QtWidgets.QTableWidget):
    """Compact register table for one device."""

    write_requested = QtCore.Signal(int, int)    # (addr, value)
    refresh_requested = QtCore.Signal(int)       # (addr)

    def __init__(self, dev, parent=None):
        regs = _REGS[dev]
        super().__init__(len(regs), 4, parent)
        self.dev = dev
        self.regs = {r.addr: r for r in regs}
        self._row_of = {r.addr: i for i, r in enumerate(regs)}
        self._updating = False

        self.setHorizontalHeaderLabels(["Addr", "Register", "Value", ""])
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(22)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked
                             | QtWidgets.QAbstractItemView.SelectedClicked
                             | QtWidgets.QAbstractItemView.AnyKeyPressed)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

        mono = QtGui.QFont("Consolas")
        for i, r in enumerate(regs):
            a = QtWidgets.QTableWidgetItem(f"0x{r.addr:02X}")
            a.setFont(mono)
            a.setFlags(QtCore.Qt.ItemIsEnabled)
            n = QtWidgets.QTableWidgetItem(r.name)
            n.setFlags(QtCore.Qt.ItemIsEnabled)
            v = QtWidgets.QTableWidgetItem("—")
            v.setFont(mono)
            if r.writable:
                v.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                           | QtCore.Qt.ItemIsSelectable)
            else:
                v.setFlags(QtCore.Qt.ItemIsEnabled)
                v.setForeground(QtGui.QColor(theme.TEXT_DIM))
            tip = rm.layout_tooltip(r)
            for it in (a, n, v):
                it.setToolTip(tip)
            self.setItem(i, COL_ADDR, a)
            self.setItem(i, COL_NAME, n)
            self.setItem(i, COL_VAL, v)

            btn = QtWidgets.QToolButton()
            btn.setText("⟳")
            btn.setToolTip(f"Re-read {r.name} from the board")
            btn.setAutoRaise(True)
            btn.clicked.connect(
                lambda _c=False, addr=r.addr: self.refresh_requested.emit(addr))
            self.setCellWidget(i, COL_BTN, btn)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(COL_ADDR, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_NAME, QtWidgets.QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_VAL, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_BTN, QtWidgets.QHeaderView.ResizeToContents)
        self.setMinimumWidth(360)
        self._fit_height()

        self.itemChanged.connect(self._on_item_changed)

    def _fit_height(self):
        h = self.horizontalHeader().height() + 4
        for i in range(self.rowCount()):
            h += self.rowHeight(i)
        self.setFixedHeight(h)

    # ---- value display ----------------------------------------------------
    def set_value(self, addr, value):
        """Show a freshly read value (None = read failed)."""
        row = self._row_of.get(addr)
        if row is None:
            return
        item = self.item(row, COL_VAL)
        reg = self.regs[addr]
        self._updating = True
        try:
            if value is None:
                item.setText("?")
                item.setToolTip("(read failed)\n\n" + rm.layout_tooltip(reg))
            else:
                item.setText(f"0x{value:0{_HEXW[self.dev]}X}")
                tip = rm.decode_tooltip(reg, value)
                if not reg.writable:
                    tip += "\n(read-only — cannot be set)"
                item.setToolTip(tip)
        finally:
            self._updating = False

    def mark_stale(self):
        """Grey every value (link lost / not yet read)."""
        self._updating = True
        try:
            for i in range(self.rowCount()):
                self.item(i, COL_VAL).setText("—")
        finally:
            self._updating = False

    # ---- edits ------------------------------------------------------------
    def _on_item_changed(self, item):
        if self._updating or item.column() != COL_VAL:
            return
        row = item.row()
        addr = int(self.item(row, COL_ADDR).text(), 16)
        try:
            val = int(item.text().strip(), 0)
        except ValueError:
            self.set_value(addr, None)
            return
        maxv = (1 << (4 * _HEXW[self.dev])) - 1
        self.write_requested.emit(addr, val & maxv)


class RegisterPanel(QtWidgets.QWidget):
    """Scrollable Registers tab: FPGA + DAC + ADC tables with live values."""

    _TITLES = {
        "fpga": "FPGA — signal-pipeline control registers",
        "dac": "DAC — AD9122 output converter (SPI)",
        "adc": "ADC — AD9467 input converter (SPI)",
    }

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.tables = {}

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        hint = QtWidgets.QLabel(
            "Double-click a value to edit it, then press Enter to write it to "
            "the board (it is read back to confirm).  Hover a value for the "
            "decoded meaning of each bit.  ⟳ re-reads one register.")
        hint.setProperty("dim", True)
        hint.setWordWrap(True)
        outer.addWidget(hint)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        body = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(body)
        vbox.setSpacing(8)

        for dev in _DEVICES:
            sec = CollapsibleSection(self._TITLES[dev],
                                     expanded=(dev == "fpga"))
            btn = QtWidgets.QPushButton("Read all")
            btn.setToolTip("Re-read every register in this table "
                           "from the board")
            btn.setMaximumWidth(110)
            btn.clicked.connect(lambda _c=False, d=dev: self.read_all(d))
            sec.add(btn)

            tbl = _RegTable(dev)
            tbl.refresh_requested.connect(
                lambda addr, d=dev: self.read_one(d, addr))
            tbl.write_requested.connect(
                lambda addr, val, d=dev: self.write_one(d, addr, val))
            self.tables[dev] = tbl
            sec.add(tbl)
            vbox.addWidget(sec)
        vbox.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        client.result.connect(self._on_result)
        client.error.connect(self._on_error)
        client.connected.connect(self._on_connected)

    # ------------------------------------------------------------ actions
    def read_one(self, dev, addr):
        self.client.submit(f"__reg__:{dev}:{addr}",
                           lambda c, d=dev, a=addr: _reader(d, c, a))

    def write_one(self, dev, addr, val):
        self.client.submit(f"__reg__:{dev}:{addr}",
                           lambda c, d=dev, a=addr, v=val: _writer(d, c, a, v))

    def read_all(self, dev):
        addrs = [r.addr for r in _REGS[dev]]

        def bulk(c, d=dev, aa=tuple(addrs)):
            return {a: _reader(d, c, a) for a in aa}

        self.client.submit(f"__regall__:{dev}", bulk)

    def read_everything(self):
        for dev in _DEVICES:
            self.read_all(dev)

    # ------------------------------------------------------------ wiring
    def _on_connected(self, ok):
        if ok:
            self.read_everything()          # initial read of all devices
        else:
            for t in self.tables.values():
                t.mark_stale()

    def _on_result(self, label, value):
        if label.startswith("__reg__:"):
            _, dev, addr = label.split(":")
            self.tables[dev].set_value(int(addr), value)
        elif label.startswith("__regall__:"):
            dev = label.split(":")[1]
            for addr, val in value.items():
                self.tables[dev].set_value(addr, val)
        elif label.startswith("regread") and label[7:].isdigit():
            # raw read from the Advanced panel: we already have the value
            self.tables["fpga"].set_value(int(label[7:]), value)
        else:
            self._refresh_affected(label)

    def _on_error(self, label, _msg):
        if label.startswith("__reg__:"):
            _, dev, addr = label.split(":")
            self.tables[dev].set_value(int(addr), None)

    # After a control-panel command succeeds, re-read only the registers that
    # command touches, so the tab tracks the board without polling.
    def _refresh_affected(self, label):
        fpga = []
        if label in ("run", "reset", "demod-input", "dac-output"):
            fpga = [0]
        elif label == "pga":
            fpga = [1]
        elif label == "channel_mask":
            fpga = [2, 4]
        elif label == "channels":                 # balanced quick-set
            fpga = [2, 4, 5, 6, 7, 8]
        elif label == "pkt":
            fpga = [4]
        elif label.startswith(("freq", "amp")) and label[-1].isdigit():
            fpga = [5 + int(label[-1])]
        elif label.startswith("regwrite") and label[8:].isdigit():
            fpga = [int(label[8:])]
        elif label == "dac-init":
            self.read_all("dac")
            fpga = [0]                            # init toggles reset bits
        elif label == "adc-init":
            self.read_all("adc")
        elif label == "spi-dac":
            self.read_all("dac")
        elif label == "spi-adc":
            self.read_all("adc")
        for a in fpga:
            self.read_one("fpga", a)
