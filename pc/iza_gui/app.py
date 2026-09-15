"""app.py — the main window.

Assembles the LabOne-style layout: a top connection bar, a scrollable control
column (control_panel), and a tabbed work area (scope + numeric).  Owns the
DataStream (UDP 7100) and ControlClient (UDP 7202) and wires their signals to
the panels.
"""

import re
import sys

from pyqtgraph.Qt import QtCore, QtWidgets

from . import theme
from .console_panel import ConsolePanel
from .control_client import ControlClient
from .control_panel import ControlPanel
from .data_stream import DataStream
from .filter_panel import FilterPanel, current_output_hz
from .numeric_panel import NumericPanel
from .recorder import ZiBinRecorder
from .register_panel import RegisterPanel
from .scope_panel import ScopePanel
from .trigger_panel import TriggerPanel
from .widgets import Led

import iza_ctrl

DEFAULT_IP = "192.168.0.80"
DATA_PORT = 7100


def _fmt_hz(hz):
    return f"{hz / 1000:.4g} kHz" if hz >= 1000 else f"{hz:.0f} Hz"


class _RecRateCombo(QtWidgets.QComboBox):
    """Editable rec-rate combo whose preset list is rebuilt from a callback each
    time it opens, so it always shows the rates achievable at the current CIC
    output rate — while still accepting a typed value."""

    def __init__(self, refresh, parent=None):
        super().__init__(parent)
        self._refresh = refresh

    def showPopup(self):
        self._refresh()
        super().showPopup()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iza — impedance analyzer")

        self.client = ControlClient(self)
        self.data = DataStream(self)
        self.recorder = ZiBinRecorder()
        self._status_misses = 0     # consecutive failed status polls
        self._link_up = False       # for down->up recovery resync
        self.settings = QtCore.QSettings("iza", "iza_gui")

        self._build_ui()
        self._wire()
        self._restore_settings()

        # scope redraw pump (decoupled from ingest rate)
        self._redraw = QtCore.QTimer(self)
        self._redraw.timeout.connect(self.scope.redraw)
        self._redraw.start(33)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        outer.addWidget(self._build_conn_bar())

        vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        outer.addWidget(vsplit, 1)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        vsplit.addWidget(split)

        # left: scrollable control column
        self.control = ControlPanel(self.client)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.control)
        scroll.setMinimumWidth(340)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        split.addWidget(scroll)

        # right: tabs
        self.scope = ScopePanel()
        self.numeric = NumericPanel()
        self.registers = RegisterPanel(self.client)
        self.trigger = TriggerPanel(self.client)
        self.filters = FilterPanel(self.client)
        self.trigger.set_filter_source(self.filters)   # for the latency estimate
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.scope, "Scope")
        tabs.addTab(self.numeric, "Numeric")
        tabs.addTab(self.trigger, "Triggering")
        tabs.addTab(self.filters, "Filter")
        tabs.addTab(self.registers, "Registers")
        tabs.setTabToolTip(0, "Live plots of the measurements")
        tabs.setTabToolTip(1, "Large live numeric readouts per channel")
        tabs.setTabToolTip(
            2, "Detect events (amplitude + phase) and fire an actuation "
               "output; live event log with timing statistics")
        tabs.setTabToolTip(
            3, "Design the CIC + FIR decimation filter, see its response, "
               "group delay and settling, and load it to the FPGA")
        tabs.setTabToolTip(
            4, "Every hardware register (FPGA, DAC, ADC) with its live "
               "value — read, decode, and set them individually")
        split.addWidget(tabs)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([360, 940])

        # bottom: Vivado-style command log
        self.console = ConsolePanel(self.client)
        vsplit.addWidget(self.console)
        vsplit.setStretchFactor(0, 1)
        vsplit.setStretchFactor(1, 0)
        vsplit.setSizes([620, 160])

        self.statusBar().showMessage("Not connected")

    def _build_conn_bar(self):
        bar = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(8)

        lay.addWidget(QtWidgets.QLabel("Board IP address"))
        self.ip_edit = QtWidgets.QLineEdit(DEFAULT_IP)
        self.ip_edit.setMaximumWidth(160)
        self.ip_edit.setToolTip("Network address of the impedance-analyzer "
                                "board (default 192.168.0.80)")
        self.ip_edit.returnPressed.connect(self._connect)
        lay.addWidget(self.ip_edit)

        self.btn_conn = QtWidgets.QPushButton("Connect")
        self.btn_conn.setProperty("accent", True)
        self.btn_conn.setToolTip("Open the control and data links to the board")
        self.btn_conn.clicked.connect(self._connect)
        self.btn_disc = QtWidgets.QPushButton("Disconnect")
        self.btn_disc.setEnabled(False)
        self.btn_disc.setToolTip("Close both links (the board keeps running)")
        self.btn_disc.clicked.connect(self._disconnect)
        lay.addWidget(self.btn_conn)
        lay.addWidget(self.btn_disc)

        lay.addSpacing(16)
        self.led_ctrl = Led()
        self.led_ctrl.setToolTip(
            "Control link: green = board answers commands, red = timeout")
        self.led_data = Led()
        self.led_data.setToolTip(
            "Data link: green = measurement data is arriving from the board")
        lbl_ctrl = QtWidgets.QLabel("control")
        lbl_ctrl.setToolTip(self.led_ctrl.toolTip())
        lbl_data = QtWidgets.QLabel("data")
        lbl_data.setToolTip(self.led_data.toolTip())
        self.led_or = Led()
        self.led_or.setToolTip(
            "ADC over-range: red = the analog input is clipping (reduce the "
            "input level or the PGA gain). This is instrument-wide — the ADC "
            "input is shared by all measurement channels.")
        lbl_or = QtWidgets.QLabel("over-range")
        lbl_or.setToolTip(self.led_or.toolTip())
        lay.addWidget(self.led_ctrl)
        lay.addWidget(lbl_ctrl)
        lay.addWidget(self.led_data)
        lay.addWidget(lbl_data)
        lay.addWidget(self.led_or)
        lay.addWidget(lbl_or)

        lay.addSpacing(16)
        lay.addWidget(QtWidgets.QLabel("Rec rate"))
        self.cmb_recrate = _RecRateCombo(self._refresh_recrates)
        self.cmb_recrate.setEditable(True)   # live presets + free entry
        self.cmb_recrate.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.cmb_recrate.setMinimumWidth(150)
        self.cmb_recrate.lineEdit().setPlaceholderText("e.g. 5 kHz or 7500")
        self.cmb_recrate.setToolTip(
            "Recording rate. The list shows the rates available at the current "
            "CIC output (200 MHz / R) and refreshes when you open it. You can also "
            "TYPE any rate, e.g. '5 kHz', '7500', '200 Hz' — it is rounded to the "
            "nearest whole division and CANNOT exceed the CIC output (a higher "
            "request is capped). Set before starting a recording.")
        self._refresh_recrates()
        lay.addWidget(self.cmb_recrate)

        self.btn_rec = QtWidgets.QPushButton("● Record")
        self.btn_rec.setCheckable(True)
        self.btn_rec.setToolTip(
            "Record incoming measurements to disk in Zurich Instruments format "
            "(Freq<N>.ziBin per channel + meta.json + raw ADC) at the selected "
            "Rec rate. You pick the destination folder on start; a timestamped "
            "session folder is created inside it.")
        self.btn_rec.toggled.connect(self._on_record)
        lay.addWidget(self.btn_rec)
        self.rec_lbl = QtWidgets.QLabel("")
        self.rec_lbl.setStyleSheet(f"color: {theme.BAD};")
        lay.addWidget(self.rec_lbl)

        lay.addStretch(1)
        self.rate_lbl = QtWidgets.QLabel("— rec/s   — Mbps")
        self.rate_lbl.setProperty("dim", True)
        self.rate_lbl.setToolTip("Incoming data rate: measurement records "
                                 "per second and megabits per second")
        lay.addWidget(self.rate_lbl)
        return bar

    # --------------------------------------------------------------- wiring
    def _wire(self):
        self.client.connected.connect(self._on_connected)
        self.client.status.connect(self._on_status)
        self.client.result.connect(self._on_result)
        self.client.error.connect(self._on_error)

        self.data.batch.connect(self.scope.on_batch)
        self.data.batch.connect(self.numeric.on_batch)
        self.data.batch.connect(self.recorder.on_batch)   # undecimated feed
        self.data.stats.connect(self._on_stats)

        # scope show-channel checkboxes drive the board's demod enables
        self.scope.channel_show_changed.connect(
            lambda ch, on: self.control.set_rx_enabled(ch, on)
            if self.client.is_connected() else None)

        # trigger events -> scope markers + console line (the TriggerPanel wires
        # its own table/stats to the same signal)
        self.client.trigger_event.connect(self.scope.on_trigger)
        self.client.trigger_event.connect(self._on_trigger_evt)

        # trigger threshold -> scope overlay guide lines
        self.trigger.overlay_changed.connect(
            lambda o: self.scope.set_trigger_overlay(
                o["ch"], o["thr"], o["mindiff"], o["show"]))

    # --------------------------------------------------------------- actions
    def _connect(self):
        if self.client.is_connected():
            return
        ip = self.ip_edit.text().strip()
        if not ip:
            self.statusBar().showMessage("Enter a board IP")
            return
        try:
            self.data.start(DATA_PORT)
        except OSError as e:
            self.statusBar().showMessage(f"Data port {DATA_PORT} busy: {e}")
            return
        self.client.connect_board(ip)
        self._link_up = True    # optimistic: avoids a duplicate initial sweep
        self.led_ctrl.set_color(theme.WARN)
        self.statusBar().showMessage(f"Connecting to {ip}…")

    def _disconnect(self):
        self._link_up = False
        self.client.disconnect_board()
        self.data.stop()
        self.control.reset_sync()
        self.numeric.clear()
        self.led_ctrl.set_color(theme.TEXT_DIM)
        self.led_data.set_color(theme.TEXT_DIM)
        self.led_or.set_color(theme.TEXT_DIM)
        self.rate_lbl.setText("— rec/s   — Mbps")
        self.statusBar().showMessage("Disconnected")

    # --------------------------------------------------------------- signals
    def _on_connected(self, ok):
        self.btn_conn.setEnabled(not ok)
        self.btn_disc.setEnabled(ok)
        self.ip_edit.setEnabled(not ok)

    def _on_status(self, regs):
        if not regs:
            # Debounce: one failed poll is just a lost UDP datagram or a busy
            # board; only two consecutive failures mean the link is down.
            self._status_misses += 1
            if self._status_misses >= 2 and self.client.is_connected():
                self._link_up = False
                self.control.apply_status({})
                self.led_ctrl.set_color(theme.BAD)
                self.statusBar().showMessage(
                    "Control link down — retrying every second (board "
                    "rebooting?). Widgets resync automatically on recovery.")
            # the board auto-disarms after its safety timeout with no heartbeat;
            # once we've missed enough polls to be past it, mirror that in the UI
            if self._status_misses >= 4:
                self.trigger.reflect_disarmed()
            return
        self._status_misses = 0
        if not self._link_up:
            # link (re)established — e.g. after a board reboot the registers
            # are back at defaults, so resync widgets and re-read the tables
            self._link_up = True
            self.control.reset_sync()
            self.registers.read_everything()
            self.statusBar().showMessage("Control link up", 3000)
        self.control.apply_status(regs)
        self.led_ctrl.set_color(theme.GOOD)
        # mirror the board's demod enables into the scope's show boxes
        r2 = regs.get(2, 0)
        for ch in range(4):
            self.scope.set_show(ch, bool(r2 & (1 << (ch + 4))))

    def _on_trigger_evt(self, evt):
        passed = bool(evt.get("flags", 0) & iza_ctrl.EVF_PASS)
        t = evt["peak_ts"] / iza_ctrl.PL_TICK_HZ
        lat = evt["latency_ticks"] / iza_ctrl.PL_TICK_HZ * 1e3
        kind = "ok" if passed else "warn"
        word = "FIRE" if passed else "candidate"
        self.console.append(
            kind, f"trigger {word} #{evt['seq']} @ {t:.6f}s  "
                  f"latency {lat:.3f} ms  chans "
                  f"0x{evt['matched']:X}")

    def _on_stats(self, s):
        alive = s.get("alive")
        self.led_data.set_color(theme.GOOD if alive else theme.BAD)
        if not alive:
            self.led_or.set_color(theme.TEXT_DIM)
        else:
            self.led_or.set_color(theme.BAD if s.get("over") else theme.GOOD)
        txt = f"{s.get('records_per_s', 0):,.0f} rec/s   {s.get('mbps', 0):.1f} Mbps"
        drops = s.get("drops", 0)
        if drops:                       # datagrams missed (seq gaps) this window
            txt += f"   ⚠ {drops} dropped"
            self.rate_lbl.setStyleSheet(f"color: {theme.BAD};")
        else:
            self.rate_lbl.setStyleSheet("")
        self.rate_lbl.setText(txt)
        self.rec_lbl.setText(self.recorder.status_text())

    # ------------------------------------------------------------ recording
    _RECRATE_FACTORS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)

    def _refresh_recrates(self):
        """Rebuild the Rec-rate presets from the current CIC output rate, keeping
        whatever the user has typed. Called on open and at startup."""
        native = current_output_hz()                 # 200 MHz / R
        keep = self.cmb_recrate.currentText()
        items = []
        for n in self._RECRATE_FACTORS:
            r = native / n
            if r < 1:
                break
            items.append(f"Full ({_fmt_hz(native)})" if n == 1
                         else f"{_fmt_hz(r)}  (÷{n})")
        self.cmb_recrate.clear()
        self.cmb_recrate.addItems(items)
        if keep:
            self.cmb_recrate.setEditText(keep)

    def _recrate_decim(self):
        """Parse the (editable) Rec-rate field into (decim, actual_hz, capped).

        The native rate is the CIC output (200 MHz / R) for the filter the board
        is running, so a recording can never be faster than that. A request above
        the CIC output is capped to it (decim 1); otherwise the request is rounded
        to the nearest whole division. `capped` is True when the request was
        clamped. Full rate on blank/bad input."""
        native = current_output_hz()                # CIC output = 200 MHz / R
        txt = self.cmb_recrate.currentText().strip().lower()
        if not txt or txt.startswith("full"):
            return 1, native, False
        m = re.search(r"([0-9]*\.?[0-9]+)\s*([kmg])?", txt)
        if not m:
            return 1, native, False
        target = float(m.group(1)) * {"k": 1e3, "m": 1e6, "g": 1e9}.get(m.group(2), 1.0)
        if target <= 0:
            return 1, native, False
        if target > native:                         # cannot exceed the CIC output
            return 1, native, True
        decim = int(max(1, min(1_000_000, round(native / target))))
        return decim, native / decim, False

    def _on_record(self, on):
        if on:
            base = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Choose where to save the recording session",
                self.settings.value("record_dir", "", str))
            if not base:
                self.btn_rec.setChecked(False)
                return
            self.settings.setValue("record_dir", base)
            decim, actual, capped = self._recrate_decim()
            d = self.recorder.start(base, self.control.current_freqs(), decim)
            self.btn_rec.setText("■ Stop rec")
            rate = ("full rate" if decim == 1
                    else f"~{actual:,.0f} Hz (1/{decim})")
            if capped:
                self.client.log.emit(
                    "warn", f"record rate capped to the CIC output "
                            f"(~{actual:,.0f} Hz) — it can't exceed 200 MHz / R.")
            self.statusBar().showMessage(f"Recording ({rate}) to {d}", 5000)
        else:
            d = self.recorder.stop()
            self.btn_rec.setText("● Record")
            self.rec_lbl.setText("")
            if d:
                self.statusBar().showMessage(f"Recording saved: {d}", 8000)

    # ------------------------------------------------------------- settings
    def _restore_settings(self):
        s = self.settings
        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        ip = s.value("board_ip", "", str)
        if ip:
            self.ip_edit.setText(ip)
        win = s.value("scope_window_s", 0.0, float)
        if win:
            self.scope.spin_win.setValue(win)
        if not s.value("dec_auto", True, bool):
            self.scope.chk_dec_auto.setChecked(False)
            self.scope.spin_dec.setValue(s.value("dec_value", 10, int))
        self.scope.cmb_content.setCurrentIndex(
            s.value("scope_content", 0, int))
        rr = s.value("rec_rate_text", "", str)
        if rr:
            self.cmb_recrate.setCurrentText(rr)
        self.trigger.load_settings(s)

    def _save_settings(self):
        s = self.settings
        s.setValue("geometry", self.saveGeometry())
        s.setValue("board_ip", self.ip_edit.text().strip())
        s.setValue("scope_window_s", self.scope.window_s)
        s.setValue("dec_auto", self.scope.chk_dec_auto.isChecked())
        s.setValue("dec_value", self.scope.spin_dec.value())
        s.setValue("scope_content", self.scope.cmb_content.currentIndex())
        s.setValue("rec_rate_text", self.cmb_recrate.currentText())
        self.trigger.save_settings(s)

    def _on_result(self, label, value):
        if not label.startswith("__"):
            self.statusBar().showMessage(f"{label}: ok", 2500)

    def _on_error(self, label, msg):
        self.statusBar().showMessage(f"{label}: {msg}", 5000)

    def closeEvent(self, e):
        self.recorder.stop()        # flush + write meta.json if recording
        self._save_settings()
        # never leave the board armed when the GUI exits
        if self.client.is_connected():
            try:
                self.client.ctrl.trig_off()
            except Exception:
                pass
        self.data.stop()
        self.client.disconnect_board()
        super().closeEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("iza")
    theme.apply(app)
    win = MainWindow()
    win.resize(1300, 820)
    win.show()
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())


if __name__ == "__main__":
    main()
