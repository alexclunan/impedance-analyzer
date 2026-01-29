# impedance-analyzer
Impedance Analyzer Capstone Project for the Swami Lab @ UVA

FPGA-BASED MULTI-FREQUENCY DIGITAL LOCK-IN AMPLIFIER 

# ABSTRACT

This repository will contain the PCB design, HDL source code, and embedded software for a high-speed Digital Lock-In Amplifier (DLIA) and triggering system implemented on a Xilinx Zynq-7000 SoC.

Designed for impedance cytometry applications, this system synthesizes multi-frequency (< 10 MHz) excitation signals and performs parallel demodulation of sensor responses in the digital domain. This measurement device will be used to trigger a sorting mechanism at low latency to sort cells and other biological materials in a microfluidic channel. 

# SYSTEM SPECIFICATIONS

Platform: Xilinx Zynq XC7Z020 SoC on the Trenz TE0720 SoM, custom carrier board PCB

ADC: 16-bit 100 MSPS+

DAC: 16-bit+, 250 MSPS+

Analog: High Frequency, Low Noise Transimpedance amplifier


# ARCHITECTURE OVERVIEW

The system utilizes a mixed-signal architecture where the FPGA handles both signal generation and analysis.

## Analog Signal Chain

1. A high-speed DAC (16-bit+, 250 MSPS+) generates a composite waveform (summation of N sinusoids) to drive the sensor electrodes.

2. A Transimpedance Amplifier (TIA) converts the modulated cell current into a voltage signal.

3. ADC: 16-bit 100 MSPS+. Connected to the FPGA fabric using LVDS traces that are delay matched.

## Digital Signal Processing (DSP) Chain

1. Direct Digital Synthesis (DDS) Core(s): Utilizes the CORDIC to generate reference Sine/Cosine waves in the FPGA programmable logic (PL) fabric.

2. Digital Mixer: Adds multiple DDS outputs together to generate a multifrequency wave. Only on when multifrequency mode is enabled.

3. DAC: Outputs 16-bit+, 250 MSPS+ Sine/Cosine wave from mixer.

4. ADC: Takes in analog signal and sends it to the PL fabric

5. FPGA ADC interface: Takes LVDS signals and converts them to usable data.

6. Digital Mixer: Performs accurate multiplication of the incoming ADC stream with local references ($X = x_{signal}[n] * sin(\omega_{ref} t)$ (real output), $Y = x_{signal}[n] * sin(\omega_{ref} t+ 90\textdegree)$ (imaginary output)). 

7. Low pass filtering: Removes unwanted high frequency noise.

8. Decimator: Downsamples the incoming waveform since target is low frequency (< 100 kHz) and needs to fit timing/resource requirements

9. Magnitude and Phase Calculator: Calculates magnitude and phase from real and imagninary components: $R = \sqrt{X^2+Y^2}$, $\phi = tan^{-1}(Y/X)$.

10. Triggering Logic: Triggers a switch that determines the path of a cell in the microfluidic channel based off a threshold calculation

# Architectural Diagram:

![alt text](https://github.com/alexclunan/impedance-analyzer/blob/main/Top-Level-Architecture/v0/Top-Level-Architecture-v0.png)
