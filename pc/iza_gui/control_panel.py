"""control_panel.py — LabOne-style control column driving iza_ctrl.IzaCtrl.

Sectioned, collapsible controls mirroring every iza_ctrl command.  Each edit
submits an async control call via ControlClient; the client's status poll keeps
the run indicator and (on first connect) the widget values in sync with the
board.  Widget values are pushed from the board only once per connection so we
never fight the user's typing.
"""

from pyqtgraph.Qt import QtCore, QtWidgets

import iza_ctrl
from . import theme
from .widgets import CollapsibleSection, Led, labeled_row

UNITY = iza_ctrl.AMP_DEFAULT        # 0x8000
RASTER = iza_ctrl.RASTER_HZ         # 12500.0
FCW_MAX = iza_ctrl.FCW_MAX          # 16000


class ControlPanel(QtWidgets.QWidget):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._synced = False        # have we pushed board regs into widgets yet?

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        root.addWidget(self._build_system())
        root.addWidget(self._build_output())
        root.addWidget(self._build_input())
        root.addWidget(self._build_fir())
        root.addWidget(self._build_packetizer())
        root.addWidget(self._build_advanced())
        root.addStretch(1)

        client.result.connect(self._on_result)
        client.error.connect(self._on_error)

    # =====================================================================
    # helpers
    # =====================================================================
    def _submit(self, label, fn):
        self.client.submit(label, fn)

    def _dspin(self, lo, hi, step, val, suffix="", dec=0):
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setDecimals(dec)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        return s

    # =====================================================================
    # System
    # =====================================================================
    def _build_system(self):
        sec = CollapsibleSection("System")

        self.run_led = Led()
        self.run_state = QtWidgets.QLabel("unknown")
        self.run_state.setProperty("dim", True)
        row = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("▶ Start")
        self.btn_run.setProperty("accent", True)
        self.btn_run.setToolTip(
            "Start the instrument: release all internal resets and begin "
            "generating/measuring (SYS_CTRL0 = run)")
        self.btn_reset = QtWidgets.QPushButton("⏹ Stop / Reset")
        self.btn_reset.setToolTip(
            "Stop the instrument and hold all internal processing in reset. "
            "Press Start to resume.")
        self.btn_run.clicked.connect(lambda: self._submit("run", lambda c: c.run()))
        self.btn_reset.clicked.connect(
            lambda: self._submit("reset", lambda c: c.reset_all()))
        row.addWidget(self.btn_run)
        row.addWidget(self.btn_reset)
        row.addWidget(self.run_led)
        row.addWidget(self.run_state)
        row.addStretch(1)
        rw = QtWidgets.QWidget()
        rw.setLayout(row)
        sec.add(rw)

        # Converters MUST be initialised after every board power-up or the
        # analog output/input is garbage — surface it prominently here.
        self.btn_init = QtWidgets.QPushButton("① Initialize DAC + ADC")
        self.btn_init.setProperty("accent", True)
        self.btn_init.setToolTip(
            "Run the AD9122 DAC (2× interpolation) and AD9467 ADC power-up "
            "sequences. REQUIRED after every board power-up — without it the "
            "analog output and input are garbage. Press Start first if the "
            "instrument is stopped.")
        self.btn_init.clicked.connect(self._init_converters)
        warn = QtWidgets.QLabel(
            "⚠ Run once after every board power-up, or the output/input is garbage.")
        warn.setWordWrap(True)
        warn.setStyleSheet(f"color: {theme.WARN};")
        sec.add(self.btn_init)
        sec.add(warn)

        # SYS_CTRL0 bit 6 (mux_0.sel): what the DEMODULATOR listens to.
        self.cmb_demin = QtWidgets.QComboBox()
        self.cmb_demin.addItems(["Analog input (ADC)",
                                 "Internal loopback (replay / test)"])
        self.cmb_demin.setToolTip(
            "What the measurement (demodulator) listens to:\n"
            "• Analog input — the real signal from the front end (normal use)\n"
            "• Internal loopback — the on-board am_modulator output (the PC "
            "replay / self-test signal), looped straight into the demodulator")
        self.cmb_demin.activated.connect(
            lambda i: self._submit("demod-input", lambda c: c.set_demod_input(i)))
        sec.add(labeled_row("Measurement input", self.cmb_demin))

        # SYS_CTRL0 bit 8 (dac_output_wrapper.test_mode): what the DAC OUTPUTS.
        self.cmb_dacout = QtWidgets.QComboBox()
        self.cmb_dacout.addItems(["Signal generator (tones)",
                                  "Internal test / replay signal"])
        self.cmb_dacout.setToolTip(
            "What the analog output (DAC) plays:\n"
            "• Signal generator — the on-board excitation tones (normal use)\n"
            "• Internal test / replay signal — the am_modulator output (the "
            "waveform streamed from the PC, or the built-in test signal)")
        self.cmb_dacout.activated.connect(
            lambda i: self._submit("dac-output", lambda c: c.set_dac_output(i)))
        sec.add(labeled_row("DAC output", self.cmb_dacout))
        return sec

    # =====================================================================
    # Signal Output (DAC)
    # =====================================================================
    def _build_output(self):
        sec = CollapsibleSection("Signal Output — excitation tones")
        self.tx_chk = []
        self.freq_spin = []
        self.freq_actual = []
        self.amp_spin = []
        self.phase_spin = []

        for ch in range(4):
            box = QtWidgets.QGroupBox(f"Tone {ch}")
            v = QtWidgets.QVBoxLayout(box)
            v.setSpacing(4)

            chk = QtWidgets.QCheckBox("Output this tone")
            chk.setToolTip(f"Include tone {ch} in the analog output signal")
            chk.toggled.connect(lambda _on: self._apply_channel_mask())
            self.tx_chk.append(chk)
            v.addWidget(chk)

            fspin = self._dspin(0, 8_000_000, RASTER, ch * 0 + 500000, " Hz")
            fspin.setToolTip(
                "Tone frequency. Snaps to the 12.5 kHz grid; keep it above "
                "400 kHz (the analog high-pass filter blocks lower "
                "frequencies).")
            actual = QtWidgets.QLabel("")
            actual.setProperty("dim", True)
            actual.setToolTip("The actual frequency after snapping to the "
                              "12.5 kHz grid")
            fspin.editingFinished.connect(
                lambda ch=ch: self._set_freq(ch))
            self.freq_spin.append(fspin)
            self.freq_actual.append(actual)
            v.addWidget(labeled_row("Frequency", fspin, actual,
                                    stretch_label=70))

            aspin = self._dspin(0, 100, 1.0, 100.0, " %", dec=1)
            aspin.setToolTip(
                "Tone amplitude as a percentage of the DAC's full-scale "
                "output. The sum of all enabled tones must stay ≤ 100 % "
                "(watch the headroom bar).")
            aspin.editingFinished.connect(lambda ch=ch: self._set_amp(ch))
            self.amp_spin.append(aspin)
            v.addWidget(labeled_row("Amplitude", aspin, stretch_label=70))

            # No per-tone phase offset: it isn't implemented in hardware (the
            # DDS has no phase-offset input in this design), and those spare
            # registers now drive the trigger's second output.

            sec.add(box)

        # headroom
        self.headroom = QtWidgets.QProgressBar()
        self.headroom.setRange(0, 150)     # % of full scale (100 = unity)
        # %v = the raw value (the level %); NOT %p, which is the percentage of
        # the 0..150 range (that showed 67 % at a true 100 % level).
        self.headroom.setFormat("total output level %v%")
        self.headroom.setToolTip(
            "Combined level of all enabled tones as a percentage of the "
            "DAC's full-scale output. Above 100 % the output clips and "
            "the signal is distorted.")
        sec.add(labeled_row("Output level", self.headroom, stretch_label=70))

        # quick channels
        self.cmb_quick = QtWidgets.QComboBox()
        self.cmb_quick.addItems(["1 tone", "2 tones", "3 tones", "4 tones"])
        btn = QtWidgets.QPushButton("Apply balanced setup")
        btn.setToolTip(
            "One-click setup: enable this many tones and set EACH to the "
            "maximum equal amplitude that won't clip (100 % ÷ number of tones — "
            "so 1 tone = 100 %, 2 = 50 %, 4 = 25 %), and match the measurement "
            "channels + packet size to suit. The Amplitude boxes update to show "
            "what was applied.")
        btn.clicked.connect(self._quick_channels)
        sec.add(labeled_row("Quick setup", self.cmb_quick, btn,
                            stretch_label=70))
        return sec

    def current_freqs(self):
        """Actual (grid-snapped) excitation frequency per channel, in Hz."""
        return {ch: self._snap(self.freq_spin[ch].value())[1]
                for ch in range(4)}

    def _snap(self, hz):
        fcw = round(hz / RASTER)
        fcw = max(0, min(FCW_MAX - 1, fcw))
        return fcw, fcw * RASTER

    def _set_freq(self, ch):
        hz = self.freq_spin[ch].value()
        fcw, actual = self._snap(hz)
        self.freq_actual[ch].setText(f"→ {actual/1e3:.1f} kHz")
        self._submit(f"freq{ch}", lambda c: c.set_freq(ch, hz))

    def _set_amp(self, ch):
        pct = self.amp_spin[ch].value()
        code = max(0, min(0xFFFF, round(pct / 100.0 * UNITY)))
        self._submit(f"amp{ch}", lambda c: c.set_amp(ch, code))
        self._refresh_headroom()

    def _quick_channels(self):
        n = [1, 2, 3, 4][self.cmb_quick.currentIndex()]
        mask = (1 << n) - 1
        self._submit("channels", lambda c: c.set_channels(mask))
        # reflect enables + the applied even-max per-tone amplitude locally so
        # the checkboxes and Amplitude boxes match what the board now has
        per_pct = 100.0 / n
        for ch in range(4):
            on = bool(mask & (1 << ch))
            for w in (self.tx_chk[ch], self.rx_chk[ch]):
                w.blockSignals(True)
                w.setChecked(on)
                w.blockSignals(False)
            if on:
                self.amp_spin[ch].blockSignals(True)
                self.amp_spin[ch].setValue(per_pct)
                self.amp_spin[ch].blockSignals(False)
        self._refresh_headroom()

    def _refresh_headroom(self):
        self._submit("__headroom__",
                     lambda c: int(round(c.dac_headroom() * 100)))

    # =====================================================================
    # Signal Input / Demod
    # =====================================================================
    def _build_input(self):
        sec = CollapsibleSection("Signal Input — measurement")
        self.rx_chk = []
        row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Measure tones:")
        lbl.setToolTip("Which tones' responses are measured (each enabled "
                       "tone gets its own magnitude + phase readout)")
        row.addWidget(lbl)
        for ch in range(4):
            chk = QtWidgets.QCheckBox(str(ch))
            chk.setToolTip(f"Measure the response at tone {ch}'s frequency")
            chk.toggled.connect(lambda _on: self._apply_channel_mask())
            self.rx_chk.append(chk)
            row.addWidget(chk)
        row.addStretch(1)
        rw = QtWidgets.QWidget()
        rw.setLayout(row)
        sec.add(rw)

        self.chk_adc = QtWidgets.QCheckBox("Also stream raw input samples (ADC)")
        self.chk_adc.setToolTip(
            "Send the unprocessed samples from the input converter alongside "
            "the measurements — shows up in the Raw input and Spectrum plots. "
            "Uses extra network bandwidth.")
        self.chk_adc.toggled.connect(lambda _on: self._apply_channel_mask())
        sec.add(self.chk_adc)

        self.pga_spin = QtWidgets.QSpinBox()
        self.pga_spin.setRange(6, 26)
        self.pga_spin.setSingleStep(2)
        self.pga_spin.setValue(6)      # minimum gain by default (matches board)
        self.pga_spin.setSuffix(" dB")
        self.pga_spin.setToolTip(
            "Gain of the input amplifier in front of the ADC (6–26 dB in "
            "2 dB steps). Raise it for weak signals; lower it if the input "
            "over-range light comes on.")
        self.pga_spin.editingFinished.connect(
            lambda: self._submit("pga", lambda c: c.set_pga(self.pga_spin.value())))
        sec.add(labeled_row("Input gain", self.pga_spin))
        return sec

    def _tx_mask(self):
        return sum(1 << ch for ch in range(4) if self.tx_chk[ch].isChecked())

    def _rx_mask(self):
        return sum(1 << ch for ch in range(4) if self.rx_chk[ch].isChecked())

    def set_rx_enabled(self, ch, on):
        """Programmatic demod-channel enable (e.g. from the scope's show-
        channel checkboxes).  Sends the channel-mask command if it changes."""
        if self.rx_chk[ch].isChecked() == on:
            return
        self.rx_chk[ch].setChecked(on)      # toggled -> _apply_channel_mask

    def _apply_channel_mask(self):
        tx = self._tx_mask()
        rx = self._rx_mask()
        adc = self.chk_adc.isChecked()
        self._submit("channel_mask",
                     lambda c: c.set_channel_mask(tx, rx, adc))
        # if auto-packet is on, resize records/packet to the new stride
        if self.chk_auto_pkt.isChecked():
            self._apply_auto_pkt(rx, adc)
        self._refresh_headroom()

    # =====================================================================
    # FIR filter (reloadable coefficients)
    # =====================================================================
    def _build_fir(self):
        """Shortcut into the Filter tab, which owns filter design.

        This used to design here with bare fir_design defaults. It can't any
        more: the designer now derives the tap count and the DC gain from the
        design rather than using fixed constants, so a call with no arguments
        would silently produce a filter of the wrong length and gain for the
        loader. The Filter tab clamps both to the hardware profile.
        """
        sec = CollapsibleSection("FIR filter — demod low-pass", expanded=False)

        lbl = QtWidgets.QLabel(
            "Filter design lives in the Filter tab: cutoff, CIC rate, taps, "
            "response and group delay, then load.")
        lbl.setWordWrap(True)
        lbl.setProperty("dim", True)
        sec.add(lbl)

        btn = QtWidgets.QPushButton("Open Filter tab")
        btn.setToolTip("Switch to the Filter tab to design and load the demod "
                       "low-pass.")
        btn.clicked.connect(self._open_filter_tab)
        sec.add(labeled_row("Design", btn))

        btn_up = QtWidgets.QPushButton("Upload .coe…")
        btn_up.clicked.connect(self._fir_upload)
        btn_up.setToolTip("Load coefficients from an existing Xilinx .coe file "
                          "and stream them to the FPGA.")
        sec.add(labeled_row("From file", btn_up))
        return sec

    def _open_filter_tab(self):
        """Find the main window's tab bar and switch to Filter."""
        w = self.window()
        tabs = w.findChild(QtWidgets.QTabWidget) if w else None
        if tabs is None:
            return
        for i in range(tabs.count()):
            if tabs.tabText(i) == "Filter":
                tabs.setCurrentIndex(i)
                return

    def _fir_upload(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a FIR coefficient file", "",
            "Coefficient files (*.coe);;All files (*)")
        if not path:
            return
        try:
            import fir_design as fd
            taps, _w = fd.read_coe(path)
            # Always the full frame: the PL loader streams exactly NCOEF values
            # and saturates past the end, so a short push loads a wrong filter
            # with no error reported.
            payload = fd.loader_payload(taps)
        except Exception as e:
            self.client.log.emit("err", f"FIR .coe load failed: {e}")
            return
        import os
        self._submit(f"fir {os.path.basename(path)} ({len(payload)} coeffs)",
                     lambda c: c.fir_load(payload))

    # =====================================================================
    # Packetizer
    # =====================================================================
    def _build_packetizer(self):
        sec = CollapsibleSection("Network Packets", expanded=False)
        self.chk_auto_pkt = QtWidgets.QCheckBox(
            "Automatically size packets (recommended)")
        self.chk_auto_pkt.setChecked(True)
        self.chk_auto_pkt.setToolTip(
            "Pack as many measurement records into each network packet as "
            "fits in a standard Ethernet frame. Turn off only if you need a "
            "specific packet size.")
        self.chk_auto_pkt.toggled.connect(self._on_auto_pkt)
        sec.add(self.chk_auto_pkt)

        self.rpp_spin = QtWidgets.QSpinBox()
        self.rpp_spin.setRange(1, 255)
        self.rpp_spin.setValue(90)
        self.rpp_spin.setEnabled(False)
        self.rpp_spin.setToolTip(
            "How many measurement records the board packs into each UDP "
            "packet it sends to the PC")
        self.rpp_spin.editingFinished.connect(
            lambda: self._submit("pkt",
                                 lambda c: c.set_pkt_cfg(self.rpp_spin.value())))
        sec.add(labeled_row("Records per packet", self.rpp_spin,
                            stretch_label=110))

        self.stride_lbl = QtWidgets.QLabel("stride —")
        self.stride_lbl.setProperty("dim", True)
        self.stride_lbl.setToolTip(
            "Size of one measurement record (depends on how many channels "
            "are enabled) and the resulting records per packet")
        sec.add(self.stride_lbl)
        return sec

    def _on_auto_pkt(self, on):
        self.rpp_spin.setEnabled(not on)
        if on:
            self._apply_auto_pkt(self._rx_mask(), self.chk_adc.isChecked())

    def _apply_auto_pkt(self, rx, adc):
        sw = iza_ctrl.IzaCtrl.stride_words(rx, adc)
        rpp = max(1, min(255, iza_ctrl.MTU_PAYLOAD // (sw * 4)))
        self.rpp_spin.blockSignals(True)
        self.rpp_spin.setValue(rpp)
        self.rpp_spin.blockSignals(False)
        self.stride_lbl.setText(f"stride {sw} words ({sw*4} B), {rpp} rec/pkt")
        self._submit("pkt", lambda c: c.set_pkt_cfg(rpp))

    # =====================================================================
    # Advanced — DAC/ADC init + raw reg/SPI
    # =====================================================================
    def _build_advanced(self):
        sec = CollapsibleSection("Advanced — converter chips & raw access",
                                 expanded=False)

        # DAC init
        self.cmb_interp = QtWidgets.QComboBox()
        self.cmb_interp.addItems(["1x", "2x (default)", "4x", "8x"])
        self.cmb_interp.setCurrentIndex(1)          # 2x is the correct default
        self.cmb_interp.setToolTip(
            "Interpolation factor for the DAC's internal digital filters. "
            "2× is the default/correct setting for this board.")
        btn_dac = QtWidgets.QPushButton("Initialize DAC")
        btn_dac.setToolTip(
            "Run the full power-up sequence for the AD9122 output converter "
            "chip (data format, clocks, FIFO alignment). Use after power-up "
            "or if the output looks wrong.")
        btn_dac.clicked.connect(self._dac_init)
        sec.add(labeled_row("Output chip", self.cmb_interp, btn_dac,
                            stretch_label=70))

        # ADC init
        self.cmb_pat = QtWidgets.QComboBox()
        self.cmb_pat.addItems(list(iza_ctrl.ADC_PATTERNS.keys()))
        self.cmb_pat.setToolTip(
            "Built-in ADC test pattern: “off” = normal operation; the other "
            "settings replace the real samples with a known pattern for "
            "checking the digital link")
        btn_adc = QtWidgets.QPushButton("Initialize ADC")
        btn_adc.setToolTip(
            "Run the power-up sequence for the AD9467 input converter chip "
            "(data format + optional test pattern)")
        btn_adc.clicked.connect(self._adc_init)
        sec.add(labeled_row("Input chip", self.cmb_pat, btn_adc,
                            stretch_label=70))

        self.chip_status = QtWidgets.QLabel("")
        self.chip_status.setWordWrap(True)
        self.chip_status.setProperty("dim", True)
        sec.add(self.chip_status)

        # raw register
        self.reg_idx = QtWidgets.QSpinBox()
        self.reg_idx.setRange(0, 15)
        self.reg_idx.setToolTip("FPGA register index (0–15). See the "
                                "Registers tab for what each one does.")
        self.reg_val = QtWidgets.QLineEdit("0x0")
        self.reg_val.setToolTip("Value to write (0x… hex or decimal)")
        btn_rd = QtWidgets.QPushButton("Read")
        btn_rd.setToolTip("Read this FPGA register from the board")
        btn_wr = QtWidgets.QPushButton("Write")
        btn_wr.setToolTip("Write the value to this FPGA register")
        btn_rd.clicked.connect(self._reg_read)
        btn_wr.clicked.connect(self._reg_write)
        sec.add(labeled_row("FPGA reg", self.reg_idx, self.reg_val,
                            btn_rd, btn_wr, stretch_label=70))

        # raw SPI
        self.cmb_bus = QtWidgets.QComboBox()
        self.cmb_bus.addItems(["DAC", "ADC"])
        self.cmb_bus.setToolTip("Which converter chip to talk to")
        self.spi_bytes = QtWidgets.QLineEdit("0x80 0x00")
        self.spi_bytes.setToolTip(
            "Raw SPI bytes to send to the chip, space-separated "
            "(expert use — see the chip datasheet)")
        btn_spi = QtWidgets.QPushButton("Send")
        btn_spi.setToolTip("Send the raw SPI bytes and show the reply")
        btn_spi.clicked.connect(self._spi_xfer)
        sec.add(labeled_row("Raw SPI", self.cmb_bus, self.spi_bytes, btn_spi,
                            stretch_label=70))

        self.raw_status = QtWidgets.QLabel("")
        self.raw_status.setProperty("dim", True)
        sec.add(self.raw_status)
        return sec

    def _init_converters(self):
        """One-click startup init: DAC (2× interp) then ADC — the sequence the
        board needs after every power-up."""
        self._submit("dac-init", lambda c: c.dac_init(2))
        self._submit("adc-init", lambda c: c.adc_init("off"))

    def _dac_init(self):
        interp = [1, 2, 4, 8][self.cmb_interp.currentIndex()]
        self._submit("dac-init", lambda c: c.dac_init(interp))

    def _adc_init(self):
        pat = self.cmb_pat.currentText()
        self._submit("adc-init", lambda c: c.adc_init(pat))

    def _reg_read(self):
        idx = self.reg_idx.value()
        self._submit(f"regread{idx}", lambda c: c.reg_read(idx))

    def _reg_write(self):
        try:
            val = int(self.reg_val.text(), 0)
        except ValueError:
            self.raw_status.setText("bad value (use 0x… or decimal)")
            return
        idx = self.reg_idx.value()
        self._submit(f"regwrite{idx}", lambda c: c.reg_write(idx, val))

    def _spi_xfer(self):
        try:
            data = [int(x, 0) & 0xFF for x in self.spi_bytes.text().split()]
        except ValueError:
            self.raw_status.setText("bad SPI bytes")
            return
        if self.cmb_bus.currentIndex() == 0:
            bus, label = iza_ctrl.SPI_DAC, "spi-dac"
        else:
            bus, label = iza_ctrl.SPI_ADC, "spi-adc"
        self._submit(label, lambda c: c.spi(bus, data))

    # =====================================================================
    # client result / error routing
    # =====================================================================
    def _on_result(self, label, value):
        if label == "__headroom__" and value is not None:
            self.headroom.setValue(int(value))
        elif label.startswith("regread"):
            self.reg_val.setText(hex(value))
            self.raw_status.setText(f"reg{label[7:]} = {hex(value)}")
        elif label in ("dac-init", "adc-init"):
            self.chip_status.setText(str(value))
        elif label in ("spi-dac", "spi-adc"):
            self.raw_status.setText("SPI rx: "
                                    + " ".join(f"0x{b:02x}" for b in bytes(value)))
        elif label == "channels":
            # value = (rpp, per_tone_amp)
            self._refresh_headroom()

    def _on_error(self, label, msg):
        if label.startswith(("regread", "regwrite", "spi-")):
            self.raw_status.setText(f"{label} error: {msg}")
        elif label in ("dac-init", "adc-init"):
            self.chip_status.setText(f"{label} error: {msg}")

    # =====================================================================
    # status sync (from ControlClient poll)
    # =====================================================================
    def apply_status(self, regs):
        """Update the run indicator and, once per connection, sync widget values
        to the board so the panel reflects the actual state."""
        if not regs:
            self.run_led.set_color(theme.TEXT_DIM)
            self.run_state.setText("no link")
            return
        run = bool(regs.get(0, 0) & (1 << iza_ctrl.B_RUN))
        self.run_led.set_color(theme.GOOD if run else theme.WARN)
        self.run_state.setText("RUNNING" if run else "held")
        if not self._synced:
            self._sync_widgets(regs)
            self._synced = True

    def reset_sync(self):
        self._synced = False

    def _sync_widgets(self, regs):
        blk = [self.cmb_demin, self.cmb_dacout, self.chk_adc,
               self.pga_spin] + self.tx_chk + self.rx_chk + self.freq_spin \
              + self.amp_spin
        for w in blk:
            w.blockSignals(True)
        try:
            r0 = regs.get(0, 0)
            self.cmb_demin.setCurrentIndex(1 if r0 & (1 << iza_ctrl.B_ADC_SEL) else 0)
            self.cmb_dacout.setCurrentIndex(1 if r0 & (1 << iza_ctrl.B_DAC_TESTSIG) else 0)

            code = regs.get(1, 0) & 0xF
            self.pga_spin.setValue(max(6, min(26, 26 - 2 * code)))

            r2 = regs.get(2, 0)
            for ch in range(4):
                self.tx_chk[ch].setChecked(bool(r2 & (1 << ch)))
                self.rx_chk[ch].setChecked(bool(r2 & (1 << (ch + 4))))
            self.chk_adc.setChecked(bool(r2 & (1 << 8)))

            for ch in range(4):
                fa = regs.get(5 + ch, 0)
                fcw = fa & 0x3FFF
                amp = (fa >> 16) & 0xFFFF
                self.freq_spin[ch].setValue(fcw * RASTER)
                self.freq_actual[ch].setText(f"→ {fcw*RASTER/1e3:.1f} kHz")
                self.amp_spin[ch].setValue(amp / UNITY * 100.0)
        finally:
            for w in blk:
                w.blockSignals(False)
        self._refresh_headroom()
        self._apply_auto_pkt(self._rx_mask(), self.chk_adc.isChecked())
