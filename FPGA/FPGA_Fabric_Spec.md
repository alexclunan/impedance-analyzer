# FPGA Fabric Specification -- Impedance Analyzer

Author: Alex Clunan

## 1. Overview

### 1.1 Target Device

| Parameter | Value |
|---|---|
| Device | Xilinx Zynq XC7Z020CLG484-2 |
| SoM | Trenz TE0720 |
| PL LUTs | 53,200 |
| PL Flip-Flops | 106,400 |
| Block RAM (36 Kb) | 140 |
| DSP48E1 Slices | 220 |
| Speed Grade | -2 |

### 1.2 Application

Digital lock-in amplifier (DLIA) for impedance spectroscopy. The FPGA fabric implements the real-time signal generation, acquisition, demodulation, filtering, and magnitude/phase extraction pipeline. The ARM Cortex-A9 processing system manages configuration, sequencing, and data readout.

### 1.3 External Converters

| Converter | Part | Resolution | Sample Rate | Interface |
|---|---|---|---|---|
| DAC | AD9122 (single channel used) | 16-bit | Up to 1.23 GSPS (with interpolation) | LVDS, 2's complement, word-load mode |
| ADC | AD9467 | 16-bit | 200 MSPS | LVDS DDR, configurable output format |

### 1.4 External Clock

200 MHz low-jitter oscillator. Directly drives the DAC clock domain in the FPGA and the AD9467 sample clock input. The AD9467 produces a Data Clock Output (DCO) that drives the ADC clock domain.

---

## 2. Clock Domains

### 2.1 DAC Clock Domain -- 200 MHz

**Source:** External 200 MHz low-jitter oscillator (direct).

**Contains:**
- Phase Accumulator (custom RTL)
- CORDIC Sine/Cosine Generator (Xilinx IP)
- DAC Output Interface / SelectIO (Xilinx IP + custom wrapper)

**I/O Bank:** Bank 35 (LVDS output to AD9122)

### 2.2 ADC Clock Domain -- 200 MHz

**Source:** AD9467 DCO (Data Clock Output), nominally 200 MHz. Asynchronous to the DAC clock.

**Contains:**
- ADC Data Realignment (custom RTL)
- Phase Synchronizer (custom RTL, CDC from DAC domain)
- Phase Accumulator (custom RTL)
- CORDIC Sine/Cosine Generator (Xilinx IP)
- Analog Path Delay FIFO (Xilinx IP)
- Mixer (custom RTL)
- Timestamp Counter (custom RTL)

**I/O Bank:** Bank 13 (LVDS input from AD9467)

### 2.3 Decimated Processing Domain -- Clock Enable

**Source:** Clock enable strobe derived from the ADC clock, asserted once every R cycles (R = CIC decimation ratio). Not a separate clock -- all logic runs on the ADC clock with a CE qualifier.

**Contains:**
- CIC Decimator (Xilinx CIC Compiler IP)
- FIR Filter (Xilinx FIR Compiler IP)
- Magnitude and Phase Calculator (custom RTL wrapper + Xilinx CORDIC IP)
- Phase Adjuster (custom RTL)

### 2.4 Triggering / Readout Domain

**Contains:**
- Triggering Logic (custom RTL)
- CPU Stream / BRAM (AXI BRAM Controller)
- Detection Logic (custom RTL)
- GPIO Output

---

## 3. Signal Path

### 3.1 Excitation Path (DAC Side)

```
FCW [48] --> Phase Accumulator --> phase [16] --> CORDIC Sin/Cos --> sin [16] --> DAC (Bank 35)
                                                                --> cos [16]    (used on ADC side only)
```

The DAC-side CORDIC sine output drives the AD9122 through the SelectIO serializer. The cosine output is unused on this side (the ADC-side generates its own sin/cos from a synchronized phase accumulator).

### 3.2 Measurement Path (ADC Side)

```
AD9467 LVDS DDR (Bank 13) --> SelectIO IDDR --> raw [32]
  --> ADC Data Realignment --> adc_sample [16]

Phase Synchronizer (CDC: DAC --> ADC domain, carries FCW + Phase MSB)
  --> Phase Accumulator --> phase [16]
    --> CORDIC Sin/Cos --> {cos [16], sin [16]}
      --> Analog Path Delay FIFO [32] --> {cos_delayed [16], sin_delayed [16]}

Mixer: adc_sample [16] x cos_delayed [16] --> I [32]
       adc_sample [16] x sin_delayed [16] --> Q [32]

Timestamp Counter [64] --> appended to I/Q samples

CIC Decimator: I [32] --> I_dec [32]    (clock enable output)
               Q [32] --> Q_dec [32]

FIR Filter:    I_dec [32] --> I_filt [32]
               Q_dec [32] --> Q_filt [32]

Magnitude/Phase Calculator (CORDIC vectoring):
  I_filt [32], Q_filt [32] --> magnitude [32], phase [32]

Phase Adjuster: phase [32] - base_offset [32] --> corrected_phase [32]
```

---

## 4. Block-by-Block Specification

### 4.1 Phase Accumulator (DAC Domain)

**Implementation:** Custom RTL

**Function:** Direct Digital Synthesis phase accumulator. Accumulates a 48-bit frequency control word every clock cycle. Outputs the upper 16 bits as the phase value for the CORDIC.

**Parameters:**

| Parameter | Value |
|---|---|
| Accumulator Width | 48 bits |
| FCW Width | 48 bits |
| Phase Output Width | 16 bits (accumulator bits [47:32]) |
| Frequency Resolution | 200 MHz / 2^48 = 0.71 uHz |
| Clock | 200 MHz (external) |

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | 200 MHz DAC clock |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `fcw` | input | 48 | Frequency control word |
| `phase_out` | output | 16 | Phase output (MSBs of accumulator) |

**Existing HDL:** `FPGA/Custom Hardware Source Files/phase_accumulator.v` (needs update from 64-bit to 48-bit accumulator)

---

### 4.2 CORDIC Sine/Cosine Generator (DAC Domain)

**Implementation:** Xilinx CORDIC v6.0

**Function:** Generates 16-bit sine and cosine waveforms from a 16-bit phase input using the CORDIC algorithm.

**IP Configuration:**

| Parameter | Value |
|---|---|
| Functional Selection | Sin and Cos |
| Architectural Configuration | Parallel |
| Pipelining Mode | Maximum |
| Phase Format | Radians |
| Input Width | 16 bits |
| Output Width | 16 bits |
| Data Format | Signed Fraction |
| Round Mode | Round Pos/Neg Inf |
| Flow Control | NonBlocking |
| Compensation Scaling | No Scale Compensation |

**Ports (AXI-Stream):**

| Port | Direction | Width | Description |
|---|---|---|---|
| `aclk` | input | 1 | 200 MHz DAC clock |
| `s_axis_phase_tvalid` | input | 1 | Phase input valid |
| `s_axis_phase_tdata` | input | 16 | Phase input |
| `m_axis_dout_tvalid` | output | 1 | Output valid |
| `m_axis_dout_tdata` | output | 32 | `{cos[31:16], sin[15:0]}` |

---

### 4.3 DAC Output Interface

**Implementation:** Xilinx SelectIO Wizard v5.1 + Custom RTL wrapper

**Function:** Serializes 16-bit DAC data into LVDS differential output for the AD9122. Forwards a synchronous clock to the DAC.

**SelectIO Configuration:**

| Parameter | Value |
|---|---|
| Bus Direction | Outputs |
| Bus IO Standard | DIFF_SSTL18_I |
| System Data Width | 8 bits |
| Serialization Factor | 4:1 |
| Active Edge | DDR |
| Clock Forwarding | Enabled |
| I/O Bank | Bank 35 |

**Custom Wrapper Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | 200 MHz DAC clock |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `dac_data` | input | 16 | DAC sample (2's complement) |
| `axi_config0..6` | input | 32 each | Configuration registers |
| `data_out_p` | output | 8 | LVDS positive |
| `data_out_n` | output | 8 | LVDS negative |
| `clk_out_p` | output | 1 | Forwarded clock positive |
| `clk_out_n` | output | 1 | Forwarded clock negative |

**Existing HDL:** `FPGA/Custom Hardware Source Files/DAC_driver_top.v` (stub)

---

### 4.4 ADC Data Realignment

**Implementation:** Custom RTL

**Function:** Sits between the SelectIO IDDR deserializer and the processing pipeline. Performs two functions:

1. **Byte reordering:** The AD9467 outputs DDR data with D[15:1] on the rising edge and D[14:0] on the falling edge of DCO. After IDDR deserialization into a 32-bit word, this block reconstructs the 16-bit sample.
2. **Per-lane LVDS polarity inversion:** Some LVDS differential pairs have swapped P/N traces on the PCB. A configurable 16-bit bitmask inverts individual data lanes to correct this.

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `raw_data` | input | 32 | IDDR deserialized DDR data |
| `polarity_mask` | input | 16 | Per-lane inversion bitmask (1 = invert) |
| `capture_select` | input | 1 | Byte-order swap for frequency-dependent alignment |
| `adc_sample` | output | 16 | Reconstructed ADC sample |
| `adc_valid` | output | 1 | Sample valid strobe |

---

### 4.5 Phase Synchronizer

**Implementation:** Custom RTL

**Function:** Clock domain crossing between the DAC clock (200 MHz external) and the ADC clock (AD9467 DCO, 200 MHz). These clocks are nominally the same frequency but asynchronous (the DCO has variable propagation delay through the AD9467).

The synchronizer transfers the DAC-side phase accumulator MSB edge across the clock domain boundary using a double-flop synchronizer with edge detection. The ADC-side phase accumulator uses this synchronized edge to align its phase with the DAC side.

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `dac_clock` | input | 1 | 200 MHz DAC clock |
| `adc_clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `dac_phase_msb` | input | 1 | MSB of DAC-side phase accumulator |
| `fcw` | input | 48 | Frequency control word (stable, from config registers) |
| `synced_phase_msb` | output | 1 | Synchronized MSB in ADC clock domain |
| `synced_fcw` | output | 48 | FCW registered in ADC clock domain |

**Existing HDL:** `FPGA/Custom Hardware Source Files/phase_accumulator_aligner.v` (stub, needs rewrite)

**Design Note:** The FCW is static during operation (guaranteed by the config-while-reset constraint), so it does not require true CDC -- it is simply registered into the ADC clock domain while the pipeline is held in reset.

---

### 4.6 Phase Accumulator (ADC Domain)

**Implementation:** Custom RTL

**Function:** Identical architecture to the DAC-side phase accumulator (Section 4.1). Receives the FCW and phase alignment signal from the Phase Synchronizer. Runs on the AD9467 DCO clock.

**Ports:** Same as Section 4.1, with the addition of:

| Port | Direction | Width | Description |
|---|---|---|---|
| `synced_phase_msb` | input | 1 | Phase alignment from synchronizer |

---

### 4.7 CORDIC Sine/Cosine Generator (ADC Domain)

**Implementation:** Xilinx CORDIC v6.0

**Function:** Same configuration as the DAC-side CORDIC (Section 4.2). Generates the sin/cos reference signals for the mixer. Runs on the AD9467 DCO clock.

---

### 4.8 Analog Path Delay FIFO

**Implementation:** Xilinx FIFO Generator

**Function:** Delays the sin/cos reference signals to compensate for the analog propagation delay between DAC output and ADC input (through the analog front-end: DAC -> TIA -> ADC). Both sin and cos are concatenated into a single 32-bit word to guarantee matched delay.

**IP Configuration:**

| Parameter | Value |
|---|---|
| Interface Type | Native |
| FIFO Implementation | Common Clock Block RAM |
| Data Width | 32 bits (`{cos[15:0], sin[15:0]}`) |
| Depth | 256 |
| Data Count | Enabled (8-bit) |
| Almost Full/Empty | Enabled |
| Reset | Synchronous |
| Max Delay | 256 / 200 MHz = 1.28 us |

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clk` | input | 1 | AD9467 DCO |
| `srst` | input | 1 | Synchronous reset (active high) |
| `din` | input | 32 | `{cos[15:0], sin[15:0]}` from CORDIC |
| `wr_en` | input | 1 | Write enable |
| `rd_en` | input | 1 | Read enable |
| `dout` | output | 32 | `{cos_delayed[15:0], sin_delayed[15:0]}` |
| `full` | output | 1 | Full flag |
| `empty` | output | 1 | Empty flag |
| `data_count` | output | 8 | Current fill level |

**Configuration:** The analog path delay is set by a 12-bit configuration register (REG2) that controls the read pointer offset relative to the write pointer.

---

### 4.9 Mixer

**Implementation:** Custom RTL

**Function:** Digital lock-in mixer. Multiplies the 16-bit ADC input sample with the delayed 16-bit sin and cos reference signals to produce the in-phase (I) and quadrature (Q) demodulated signals. The full 32-bit product is preserved (no truncation) to maximize dynamic range through the decimation chain.

**Parameters:**

| Parameter | Value |
|---|---|
| Input Width | 16 bits (ADC) x 16 bits (reference) |
| Output Width | 32 bits (full product, signed) |
| Multiply Implementation | DSP48E1 |

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `adc_sample` | input | 16 | ADC input from realignment block |
| `cos_ref` | input | 16 | Cosine reference from FIFO |
| `sin_ref` | input | 16 | Sine reference from FIFO |
| `fifo_data_count` | input | 8 | FIFO fill level |
| `fifo_rd_en` | output | 1 | FIFO read enable |
| `processing_enable` | input | 1 | Enable from config register |
| `i_out` | output | 32 | In-phase (real) product: ADC x cos |
| `q_out` | output | 32 | Quadrature (imaginary) product: ADC x sin |
| `valid_out` | output | 1 | Output valid strobe |

**Existing HDL:** `FPGA/Custom Hardware Source Files/lock-in_mixer.v` (needs update: 32-bit output width, split FIFO into {cos, sin})

---

### 4.10 Timestamp Counter

**Implementation:** Custom RTL

**Function:** 64-bit free-running counter clocked at the ADC sample rate. The timestamp value is captured and appended to each I/Q sample pair, providing precise timing information for impedance measurements.

| Parameter | Value |
|---|---|
| Counter Width | 64 bits |
| Clock | AD9467 DCO (200 MHz) |
| Wrap Period | 2^64 / 200 MHz = ~2,924 years |

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `timestamp` | output | 64 | Current timestamp value |

---

### 4.11 Decimator / Low-Pass Filter (I and Q Channels)

**Implementation:** Xilinx CIC Compiler IP + Xilinx FIR Compiler IP + Custom RTL wrapper

**Function:** Two-stage decimation and filtering. The CIC provides high-ratio decimation with automatic bit-growth management (Hogenauer pruning). The FIR provides a sharp cutoff and compensates for CIC passband droop. Separate I and Q instances process the two channels identically.

All logic runs on the ADC clock with a clock enable for the decimated output rate.

#### 4.11.1 CIC Decimator

**IP:** Xilinx CIC Compiler

| Parameter | Preliminary Value |
|---|---|
| Input Data Width | 32 bits |
| Output Data Width | 32 bits (pruned) |
| Number of Stages | TBD (3-5 typical) |
| Differential Delay | 1 |
| Decimation Ratio | Runtime-programmable via `S_AXIS_CONFIG` |
| Target Decimation Ratio | ~20,000:1 (for 10 kHz output from 200 MHz) |
| Sample Rate | 200 MHz input |
| Has ARESETN | Yes |

**Key AXI-Stream Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `aclk` | input | 1 | AD9467 DCO |
| `aresetn` | input | 1 | Active-low synchronous reset |
| `s_axis_data_tdata` | input | 32 | Mixer I or Q output |
| `s_axis_data_tvalid` | input | 1 | Input valid |
| `s_axis_config_tdata` | input | varies | Decimation ratio |
| `s_axis_config_tvalid` | input | 1 | Config valid |
| `m_axis_data_tdata` | output | 32 | Decimated output |
| `m_axis_data_tvalid` | output | 1 | Output valid (serves as clock enable) |

#### 4.11.2 FIR Filter

**IP:** Xilinx FIR Compiler

| Parameter | Preliminary Value |
|---|---|
| Input Data Width | 32 bits |
| Output Data Width | 32 bits |
| Coefficient Width | 16-24 bits (TBD) |
| Number of Taps | TBD (design-time parameter) |
| Coefficient Reload | Enabled (via AXI) |
| Optimization | Area or Speed (TBD based on resource budget) |
| Preliminary Cutoff | 10 kHz (at decimated sample rate) |

The FIR coefficient set is computed by the PS (ARM) and loaded via the AXI reload interface between experiments. This allows runtime-configurable cutoff frequency and filter response without regenerating the bitstream. CIC passband droop compensation is incorporated into the FIR coefficient design.

**Key AXI-Stream Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `aclk` | input | 1 | AD9467 DCO |
| `aresetn` | input | 1 | Active-low synchronous reset |
| `s_axis_data_tdata` | input | 32 | CIC output |
| `s_axis_data_tvalid` | input | 1 | Input valid (from CIC m_axis_data_tvalid) |
| `s_axis_reload_tdata` | input | varies | Coefficient reload data |
| `s_axis_reload_tvalid` | input | 1 | Reload valid |
| `s_axis_reload_tlast` | input | 1 | Last coefficient in set |
| `m_axis_data_tdata` | output | 32 | Filtered output |
| `m_axis_data_tvalid` | output | 1 | Output valid |

#### 4.11.3 Custom RTL Wrapper

The wrapper handles:
- Clock enable generation from CIC output valid
- AXI-Stream connections between CIC and FIR
- CIC decimation ratio configuration sequencing (loads `S_AXIS_CONFIG` from REG4 on state machine command)
- FIR coefficient reload sequencing (coordinates with PS writes)
- Pipeline reset/enable control from State Machine

---

### 4.12 Magnitude and Phase Calculator

**Implementation:** Custom RTL wrapper + Xilinx CORDIC v6.0

**Function:** Computes both magnitude and phase from the filtered I/Q signals using a single CORDIC instance in vectoring (translate) mode. The CORDIC vectoring algorithm simultaneously produces:

- Magnitude: sqrt(I^2 + Q^2)
- Phase: atan2(Q, I)

Using a single CORDIC instance (rather than separate SQRT and arctan blocks) halves the CORDIC resource usage and guarantees consistent latency between magnitude and phase outputs.

**CORDIC IP Configuration:**

| Parameter | Value |
|---|---|
| Functional Selection | Translate (Vectoring Mode) |
| Architectural Configuration | Parallel |
| Pipelining Mode | Maximum |
| Input Width | 32 bits |
| Output Width | 32 bits |
| Data Format | Signed Fraction |
| Flow Control | NonBlocking |

**Wrapper Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `ce` | input | 1 | Clock enable (decimated rate) |
| `i_in` | input | 32 | Filtered in-phase signal |
| `q_in` | input | 32 | Filtered quadrature signal |
| `valid_in` | input | 1 | Input valid |
| `magnitude` | output | 32 | sqrt(I^2 + Q^2) |
| `phase` | output | 32 | atan2(Q, I) in radians (signed fraction) |
| `valid_out` | output | 1 | Output valid |

---

### 4.13 Phase Adjuster

**Implementation:** Custom RTL

**Function:** Subtracts a configurable base phase offset from the measured phase to produce the corrected impedance phase. The base offset compensates for fixed phase shifts in the analog signal chain.

**Ports:**

| Port | Direction | Width | Description |
|---|---|---|---|
| `clock` | input | 1 | AD9467 DCO |
| `reset_n` | input | 1 | Active-low asynchronous reset |
| `ce` | input | 1 | Clock enable (decimated rate) |
| `measured_phase` | input | 32 | Phase from magnitude/phase calculator |
| `base_phase_offset` | input | 32 | Configurable offset (from REG6-REG7) |
| `corrected_phase` | output | 32 | Adjusted phase output |

---

### 4.14 Configuration Registers

**Implementation:** Custom AXI4-Lite Slave IP (`Configuration_Register`)

**Function:** 64 x 32-bit registers accessible from the PS via M_AXI_GP0. Register outputs are connected directly to PL logic without clock domain crossing synchronizers.

| Parameter | Value |
|---|---|
| AXI Data Width | 32 bits |
| AXI Address Width | 8 bits |
| Number of Registers | 64 |
| Address Range | 0x00 - 0xFC (4-byte aligned) |
| AXI Clock | FCLK0 (100 MHz) |

**Design Constraint:** The State Machine must hold the processing pipeline in reset whenever the PS writes new configuration values. All register values are guaranteed stable during active operation. This eliminates the need for CDC logic on the register outputs.

---

### 4.15 State Machine

**Implementation:** Custom RTL

**Function:** System-level sequencer that controls the measurement flow. Responsibilities:

1. **Config-while-reset enforcement:** Holds the processing pipeline in reset while the PS writes configuration registers and loads FIR coefficients.
2. **Startup sequencing:** Releases reset in the correct order (config registers settle -> CIC config loaded -> FIR coefficients loaded -> pipeline enabled).
3. **Measurement control:** Starts/stops measurements, coordinates data capture.
4. **Block enables:** Individual enable/disable for pipeline stages.

Controlled by the PS via configuration register commands and status readback.

---

### 4.16 Triggering Logic / Detection Logic

**Implementation:** Custom RTL

**Function:** Monitors the magnitude and/or phase output from the processing pipeline for configurable trigger conditions (threshold crossing, settling detection). Trigger parameters are set via configuration registers (REG8-REG9). Triggers can initiate data capture into BRAM or assert GPIO output pins.

---

### 4.17 CPU Stream / BRAM

**Implementation:** AXI BRAM Controller (Xilinx IP)

**Function:** Provides a shared BRAM interface between PL and PS. The PL writes measurement results (magnitude, phase, timestamps) into BRAM. The PS reads results via the AXI BRAM Controller mapped into the M_AXI_GP0 address space.

The architecture is designed so the BRAM can be replaced with an AXI-Stream interface and AXI DMA engine if higher throughput is needed in the future.

---

### 4.18 GPIO Output

**Implementation:** PL GPIO

**Function:** Output pins for external triggering and synchronization. Directly driven by the Detection Logic block.

---

## 5. External I/O Interfaces

### 5.1 Bank 35 -- DAC Output (AD9122)

| Signal | Direction | Width | Standard | Description |
|---|---|---|---|---|
| `dac_data_p/n` | output | 8 diff pairs | DIFF_SSTL18_I | DAC data (4:1 serialized) |
| `dac_clk_p/n` | output | 1 diff pair | DIFF_SSTL18_I | Forwarded clock |

The AD9122 is configured for word-load mode. Only one of the two DAC channels is used. Data format is 2's complement.

### 5.2 Bank 13 -- ADC Input (AD9467)

| Signal | Direction | Width | Standard | Description |
|---|---|---|---|---|
| `adc_data_p/n` | input | 16 diff pairs | DIFF_SSTL18_I | ADC data (DDR) |
| `adc_dco_p/n` | input | 1 diff pair | DIFF_SSTL18_I | Data clock output from AD9467 |

The AD9467 outputs interleaved DDR data: D[15:1] on the rising edge of DCO and D[14:0] on the falling edge. The ADC Data Realignment block (Section 4.4) reconstructs the 16-bit sample and handles per-lane LVDS polarity inversion for swapped N/P traces on the PCB.

### 5.3 Low-Jitter Clock Input

200 MHz external oscillator. Routed to:
- FPGA fabric (DAC clock domain, direct)
- AD9467 clock input (produces DCO for ADC clock domain)
- AD9122 reference clock (if not using AD9122's internal PLL)

### 5.4 SPI (PS Peripheral)

Main DAC/ADC/CLK Controller. The PS configures the AD9467, AD9122, and any external clock generators via the Zynq PS SPI peripheral.

### 5.5 Other Interfaces

| Interface | Function |
|---|---|
| Extra DAC Output/Controller | Secondary DAC channel (separate from AD9122 signal path) |
| USB Controller | Data output to host PC |
| Ethernet Controller | Network data interface |
| GPIO | Triggering / detection outputs |

---

## 6. PS-PL Interface

### 6.1 AXI Interconnect

| Parameter | Value |
|---|---|
| AXI Port | M_AXI_GP0 |
| AXI Protocol | AXI4-Lite |
| Address Range | 0x40000000 - 0x7FFFFFFF |
| AXI Bus Clock | FCLK0 = 100 MHz |

### 6.2 Address Map

| Peripheral | Base Address | Size | Description |
|---|---|---|---|
| Configuration Registers | TBD (Vivado auto-assign) | 256 B | 64 x 32-bit config registers |
| AXI BRAM Controller | TBD (Vivado auto-assign) | TBD | Measurement data readout |
| FIR Compiler (I) reload | TBD (Vivado auto-assign) | TBD | FIR coefficient reload AXI |
| FIR Compiler (Q) reload | TBD (Vivado auto-assign) | TBD | FIR coefficient reload AXI |

### 6.3 Data Flow

**PS to PL (configuration):**
- FCW, analog path delay, processing enable, trigger parameters, state machine commands, base phase offset, CIC decimation ratio, ADC realignment config
- FIR coefficients (via FIR Compiler AXI reload interface)

**PL to PS (measurement data):**
- Magnitude (32-bit), corrected phase (32-bit), timestamps (64-bit)
- Status/trigger flags
- Readout via AXI BRAM Controller

---

## 7. Configuration Register Map

All registers are 32-bit, 4-byte aligned. Base address assigned by Vivado.

| Register | Offset | Field | Description |
|---|---|---|---|
| REG0 | 0x00 | `fcw[31:0]` | Frequency Control Word, lower 32 bits |
| REG1 | 0x04 | `fcw[47:32]` | Frequency Control Word, upper 16 bits (bits [31:16] reserved) |
| REG2 | 0x08 | `analog_path_delay[11:0]` | FIFO read pointer offset (12-bit). Max delay = 256 samples = 1.28 us |
| REG3 | 0x0C | `processing_enable`, mixer config | Bit 0: processing enable. Remaining bits: mixer configuration |
| REG4 | 0x10 | `cic_decimation_ratio` | CIC decimation ratio (passed to CIC `S_AXIS_CONFIG` by State Machine) |
| REG5 | 0x14 | `fir_reload_status` | FIR reload trigger/status (PS signals reload complete) |
| REG6 | 0x18 | `base_phase_offset[31:0]` | Base phase offset, lower 32 bits |
| REG7 | 0x1C | `base_phase_offset` (reserved) | Reserved for extended phase offset |
| REG8 | 0x20 | `trigger_threshold` | Trigger threshold value |
| REG9 | 0x24 | `trigger_config` | Trigger mode and configuration |
| REG10 | 0x28 | `state_machine_ctrl` | State machine command / status |
| REG11 | 0x2C | `adc_realign_config` | Bits [15:0]: LVDS polarity inversion bitmask. Bit 16: capture select |
| REG12+ | 0x30+ | | Data stream, component status readback |
| REG13-63 | 0x34-0xFC | | Reserved / TBD |

**Operational constraint:** All register writes must occur while the State Machine holds the pipeline in reset. The PS must not modify registers during active measurement.

---

## 8. Resource Estimates

### 8.1 Available Resources (XC7Z020CLG484-2)

| Resource | Available |
|---|---|
| LUTs | 53,200 |
| Flip-Flops | 106,400 |
| Block RAM (36 Kb) | 140 |
| DSP48E1 | 220 |

### 8.2 Estimated Usage

| Block | LUTs | FFs | BRAM | DSP48 | Notes |
|---|---|---|---|---|---|
| Phase Accumulators (x2) | ~200 | ~200 | 0 | 0 | 48-bit adders |
| CORDIC Sin/Cos (x2) | ~400-800 | ~400-800 | 0 | 0 | Max pipeline, 200 MHz |
| CORDIC Vectoring (x1) | ~200-400 | ~200-400 | 0 | 0 | Decimated rate, relaxed timing |
| ADC Data Realignment | ~50 | ~100 | 0 | 0 | Combinational + registers |
| Phase Synchronizer | ~50 | ~150 | 0 | 0 | Double-flop + edge detect |
| Analog Path Delay FIFO | ~20 | ~50 | 1 | 0 | 256 x 32-bit BRAM |
| Mixer | ~50 | ~100 | 0 | 2 | Two DSP48E1 multiplies |
| Timestamp Counter | ~30 | ~70 | 0 | 0 | 64-bit counter |
| CIC Compiler (x2) | ~200-600 | ~200-600 | 0-2 | 0-4 | Depends on stages, decimation ratio |
| FIR Compiler (x2) | ~200-800 | ~200-800 | 1-4 | 4-40 | Depends on taps, optimization |
| Magnitude/Phase wrapper | ~50 | ~100 | 0 | 0 | Glue logic |
| Phase Adjuster | ~30 | ~40 | 0 | 0 | 32-bit subtractor |
| Config Registers | ~200 | ~2,100 | 0 | 0 | 64 x 32-bit regs + AXI |
| State Machine | ~100-300 | ~100-300 | 0 | 0 | Depends on complexity |
| Triggering Logic | ~100-200 | ~100-200 | 0 | 0 | Comparators + control |
| AXI BRAM Controller | ~100 | ~100 | 1-4 | 0 | Xilinx IP |
| SelectIO (ADC + DAC) | ~100 | ~200 | 0 | 0 | ISERDES/OSERDES primitives |
| **Estimated Total** | **~2,000-5,000** | **~4,000-6,000** | **~4-12** | **~6-46** | |
| **Utilization** | **~4-10%** | **~4-6%** | **~3-9%** | **~3-21%** | Comfortably within budget |

Resource usage is dominated by the FIR Compiler (DSP48 count scales with tap count) and CIC Compiler (register width scales with decimation ratio and stages). The XC7Z020 has ample headroom for this design.
