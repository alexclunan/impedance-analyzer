# Error Models Documentation

This document describes exactly how all errors are generated in the DLIA signal chain simulation (`dlia_signal_chain_gui.py`).

---

## Signal Chain Overview

```
DDS → DAC → AM Modulation → OpAmp Buffer → ADC → IQ Demodulation → LPF → Output
```

---

## 1. DAC Errors

The DAC converts digital codes to analog voltages with the following error sources:

### 1.1 Gain Error (`dac_gain_pct_fs`)

**Unit:** %FS (percent of full scale)

**Implementation:**
```python
dac_out = ideal_output * (1.0 + gain_error)
```

Where `gain_error = dac_gain_pct_fs / 100.0` (converts %FS to fractional).

**Effect:** Scales the entire output by a multiplicative factor. A +1% gain error means the output is 1% higher than ideal at all codes.

### 1.2 Offset Error (`dac_offset_pct_fs`)

**Unit:** %FS (percent of full scale)

**Implementation:**
```python
dac_out = ideal_output * (1.0 + gain_error) + offset_error
```

Where `offset_error = dac_offset_pct_fs / 100.0` (normalized to full scale).

**Effect:** Adds a constant DC offset to all output values. A +1% offset error shifts the entire output up by 1% of full scale.

### 1.3 INL - Integral Nonlinearity (`dac_inl_lsb`)

**Unit:** LSB (Least Significant Bits)

**Implementation:**
```python
# Generate a random walk profile across all codes
inl_profile = np.cumsum(rng.standard_normal(n_levels))
inl_profile = inl_profile - inl_profile.mean()  # Zero-mean
inl_profile = inl_profile / max(|inl_profile|) * (inl_lsb / max_code)

# Apply INL based on current code
inl_error = inl_profile[code]
dac_out = ideal + inl_error + ...
```

**Effect:** Creates a smooth, code-dependent deviation from the ideal transfer function. Represents cumulative errors in the DAC's internal resistor ladder. The profile is generated once per simulation run (seeded random).

### 1.4 DNL - Differential Nonlinearity (`dac_dnl_lsb`)

**Unit:** LSB (Least Significant Bits)

**Implementation:**
```python
dnl_random = rng.standard_normal(n_samples) * (dnl_lsb / max_code)
dac_out = ideal + inl_error + dnl_random
```

**Effect:** Adds random per-sample noise representing step-size variations. Each code transition has a slightly different step size.

### 1.5 Complete DAC Error Formula

```
V_out = [V_ideal + INL(code) + DNL_noise] × (1 + gain_error) + offset_error
```

Where:
- `V_ideal = (code / max_code) × V_ref`
- `max_code = 2^n_bits - 1`

---

## 2. OpAmp (Unity Gain Buffer) Errors

The OpAmp is configured as a unity-gain buffer in this simulation.

### 2.1 Gain Error (Fixed at 0)

The OpAmp gain error is set to 0 (perfect unity gain).

### 2.2 Offset Voltage (`opamp_offset_mv`)

**Unit:** mV (millivolts)

**Implementation:**
```python
opamp_output = input × (1.0 + gain_error) + offset_voltage
```

Where `offset_voltage = opamp_offset_mv × 1e-3` (converts mV to V).

**Effect:** Adds a constant DC offset to the signal.

### 2.3 Bandwidth Limitation (`opamp_bw_mhz`)

**Unit:** MHz

**Implementation:**
```python
# First-order IIR low-pass filter
alpha = 1.0 - exp(-2π × f_bandwidth / f_sample)
y[n] = alpha × x[n] + (1 - alpha) × y[n-1]
```

**Effect:** Single-pole rolloff at the specified bandwidth. Attenuates high-frequency components and introduces phase shift. The -3dB point is at `opamp_bw_mhz`.

### 2.4 Noise (`opamp_noise_uv`)

**Unit:** µV RMS (microvolts RMS)

**Implementation:**
```python
noise = rng.standard_normal(n_samples) × noise_rms
output = signal + noise
```

Where `noise_rms = opamp_noise_uv × 1e-6` (converts µV to V).

**Effect:** Adds white Gaussian noise with the specified RMS amplitude.

### 2.5 Complete OpAmp Error Formula

```
V_out = LPF[V_in × (1 + gain_error) + offset] + noise
```

Where LPF is a first-order IIR filter with cutoff at `bandwidth_hz`.

---

## 3. ADC Errors

The ADC converts analog voltages to digital codes with the following error sources:

### 3.1 Gain Error (`adc_gain_pct_fs`)

**Unit:** %FS (percent of full scale)

**Implementation:**
```python
x_normalized = (V_in / V_ref) × (1.0 + gain_error)
```

Where `gain_error = adc_gain_pct_fs / 100.0`.

**Effect:** Scales the input before quantization. A +1% gain error makes all codes 1% higher than they should be.

### 3.2 Offset Error (`adc_offset_pct_fs`)

**Unit:** %FS (percent of full scale)

**Implementation:**
```python
x_normalized = (V_in / V_ref) × (1.0 + gain_error) + offset_error / V_ref
```

Where `offset_error = adc_offset_pct_fs / 100.0`.

**Effect:** Shifts the entire transfer function. A +1% offset means a 0V input reads as 1% of full scale.

### 3.3 INL - Integral Nonlinearity (`adc_inl_lsb`)

**Unit:** LSB (Least Significant Bits)

**Implementation:**
```python
# Generate a random walk profile across all codes
inl_profile = np.cumsum(rng.standard_normal(n_levels))
inl_profile = inl_profile - inl_profile.mean()
inl_profile = inl_profile / max(|inl_profile|) × (inl_lsb / n_levels)

# Apply INL based on current code
code_float = code_float + inl_profile[code]
```

**Effect:** Creates code-dependent deviation from ideal quantization. Similar to DAC INL but applied during analog-to-digital conversion.

### 3.4 DNL - Differential Nonlinearity (`adc_dnl_lsb`)

**Unit:** LSB (Least Significant Bits)

**Implementation:**
```python
code_float = code_float + rng.standard_normal(n_samples) × dnl_lsb
```

**Effect:** Random per-sample quantization variation. Some code bins are wider/narrower than ideal.

### 3.5 Aperture Jitter (`adc_jitter_sec`)

**Unit:** seconds (typically picoseconds, e.g., 5e-12)

**Implementation:**
```python
# Time uncertainty causes voltage error for changing signals
jitter = rng.standard_normal(n_samples) × aperture_jitter_sec
dV_dt = np.gradient(V_in, dt)  # Signal slope
V_in_jittered = V_in + dV_dt × jitter
```

**Effect:** For fast-changing signals, sampling time uncertainty causes voltage errors. The error is proportional to `dV/dt × Δt_jitter`. High-frequency signals are more affected.

### 3.6 Quantization

**Implementation:**
```python
codes = np.clip(np.round(code_float), 0, max_code).astype(int)
```

**Effect:** Rounds to nearest integer code, creating quantization noise with RMS = LSB/√12.

### 3.7 Complete ADC Error Flow

```
1. Aperture jitter:  V' = V_in + (dV/dt) × jitter_noise
2. Gain & offset:    V'' = (V' / V_ref) × (1 + gain_error) + offset_error
3. Scale to codes:   code_float = V'' × max_code
4. Add INL:          code_float += INL_profile[code]
5. Add DNL:          code_float += DNL_noise
6. Quantize:         code = round(code_float)
```

---

## 4. Demodulation LPF

### 4.1 Low-Pass Filter (`lpf_enbw_khz`)

**Unit:** kHz (Equivalent Noise Bandwidth)

**Implementation:**
```python
# 4th-order Butterworth filter
f_cutoff = enbw_hz / 1.026  # ENBW to -3dB conversion for 4th order
sos = scipy.signal.butter(4, f_cutoff/f_nyquist, btype='low', output='sos')
output = scipy.signal.sosfiltfilt(sos, signal)  # Zero-phase filtering
```

**Effect:** 
- Removes 2× carrier frequency components from IQ demodulation
- Zero-phase filtering (forward-backward) prevents phase distortion
- Wider ENBW preserves more envelope bandwidth but passes more noise
- Narrower ENBW smooths the output but may attenuate fast envelope changes

---

## 5. Display/Recovery Parameters

### 5.1 Graph Scale (`graph_scale`)

**Unit:** Dimensionless multiplier

**Implementation:**
```python
demod_scaled = demod_recovered × graph_scale
```

**Effect:** Manual scaling of recovered signal for visual comparison.

### 5.2 DC Bias (`dc_bias_uv`)

**Unit:** µV (microvolts)

**Implementation:**
```python
demod_final = demod_recovered × graph_scale + dc_bias_uv × 1e-6
```

**Effect:** Adds DC offset to recovered signal. The "Auto Bias" button calculates the optimal value to minimize mean error.

---

## 6. Carrier Headroom Adjustment

To prevent clipping during AM modulation, the carrier amplitude is automatically scaled:

```python
# Calculate max allowable carrier peak
max_carrier_peak = V_ref / (1.01 × (1 + max(envelope, 0)))

# Scale carrier if needed
if carrier_peak > max_carrier_peak:
    scale = max_carrier_peak / carrier_peak
    carrier_center *= scale
    carrier_amp *= scale
```

**Effect:** Ensures `carrier × (1 + envelope)` never exceeds ADC reference voltage.

---

## 7. Summary Table

| Parameter | Unit | Range (GUI) | Effect |
|-----------|------|-------------|--------|
| **DAC** |
| `dac_bits` | bits | 4-24 | Resolution: 2^n levels |
| `dac_v_ref` | V | 0.5-2.0 | Full-scale voltage |
| `dac_inl_lsb` | LSB | 0-16 | Smooth transfer function error |
| `dac_dnl_lsb` | LSB | 0-6 | Per-step random error |
| `dac_gain_pct_fs` | %FS | ±5 | Multiplicative scale error |
| `dac_offset_pct_fs` | %FS | ±10 | Additive DC error |
| **OpAmp** |
| `opamp_bw_mhz` | MHz | 1-100 | Bandwidth limit (1st order) |
| `opamp_noise_uv` | µV RMS | 0-1000 | White noise |
| `opamp_offset_mv` | mV | ±10 | DC offset |
| **ADC** |
| `adc_bits` | bits | 4-24 | Resolution: 2^n levels |
| `adc_v_ref` | V | 0.5-2.0 | Full-scale voltage |
| `adc_inl_lsb` | LSB | 0-16 | Smooth transfer function error |
| `adc_dnl_lsb` | LSB | 0-6 | Per-step random error |
| `adc_gain_pct_fs` | %FS | ±5 | Multiplicative scale error |
| `adc_offset_pct_fs` | %FS | ±10 | Additive DC error |
| `adc_jitter_sec` | ps | 0-5 | Aperture timing uncertainty |
| **Demod** |
| `lpf_enbw_khz` | kHz | 1-100 | Post-demod filter bandwidth |

---

## 8. Code References

- **DAC errors:** `generators.py::dac_errors()` (lines 303-354)
- **OpAmp errors:** `generators.py::opamp_errors()` (lines 366-394)
- **ADC errors:** `generators.py::adc_errors()` (lines 397-447)
- **Simulators:** `simulators.py` (DACSimulator, OpAmpSimulator, ADCSimulator)
- **Signal chain:** `dlia_signal_chain_gui.py::run_signal_chain()`
