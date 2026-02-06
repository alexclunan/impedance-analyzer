"""
DLIA Signal Chain Simulator

Simulates the Digital Lock-In Amplifier signal chain for impedance cytometry:
  1. DDS generates sin(ω_ref·t) as DAC input
  2. DAC converts digital to analog (with errors: INL, DNL, gain, offset, glitch)
  3. Impedance sensor: TRUE AM modulation: ADC_in = DAC_out × (1 + m × envelope)
     This models how impedance changes modulate the carrier amplitude (I = V/Z)
  4. ADC digitizes (with errors: INL, DNL, gain, offset, jitter)
  5. Demodulation: X = signal × sin(ω_ref·t), Y = signal × cos(ω_ref·t), 
     4th order Butterworth LPF (ENBW=10 kHz), R = √(X² + Y²)

Test_Signal.txt contains already-demodulated voltage (time-domain envelope at 14 kHz).
We isolate the largest pulse (baseline → rise → fall → baseline) for efficiency.

Graphs (4 rows × 2 cols: time-domain | FFT):
  Row 1: Original envelope (from Test_Signal.txt)
  Row 2: DAC percent error (normalized to amplitude)
  Row 3: ADC percent error (normalized to amplitude)
  Row 4: Original envelope vs demodulated ADC output

Run:  python testing/dlia_signal_chain_gui.py  (from repo root)
"""

from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, TextBox
from matplotlib.gridspec import GridSpec
from scipy.signal import butter, sosfiltfilt

from generators import sine_wave
from simulators import DACSimulator, ADCSimulator


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
SEED = 42
DAC_SAMPLE_RATE_HZ = 10e6          # 10 MSPS (per user spec; real DAC is 250 MSPS+)
ADC_SAMPLE_RATE_HZ = 10e6          # Match DAC for this sim (real ADC is 100 MSPS+)
CARRIER_FREQ_HZ = 500e3            # 500 kHz reference
TEST_SIGNAL_SAMPLE_RATE_HZ = 14e3  # Test_Signal.txt sample rate
TEST_SIGNAL_FILENAME = "Test_Signal.txt"
MAX_LOAD_FOR_ENVELOPE = 800_000    # Max samples to scan when finding envelope

# 4th order LPF parameters
# ENBW for 4th order Butterworth ≈ 1.026 × f_cutoff, so f_cutoff = ENBW / 1.026
LPF_ENBW_HZ = 10e3                 # 10 kHz ENBW
LPF_ORDER = 4
LPF_CUTOFF_HZ = LPF_ENBW_HZ / 1.026  # ~9746 Hz for ENBW = 10 kHz


# ──────────────────────────────────────────────────────────────────────────────
# Envelope extraction from Test_Signal.txt
# ──────────────────────────────────────────────────────────────────────────────
def load_full_signal(filepath: str, max_samples: int) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Load one float per line. Returns (signal, t) or (None, None)."""
    try:
        data = np.loadtxt(filepath, dtype=float, ndmin=1, max_rows=int(max_samples))
        signal = np.asarray(data, dtype=float)
        t = np.arange(len(signal), dtype=float) / TEST_SIGNAL_SAMPLE_RATE_HZ
        return signal, t
    except Exception:
        return None, None


def find_largest_envelope(
    signal: np.ndarray,
    t: np.ndarray,
    baseline_frac: float = 0.1,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """
    Find the largest envelope: nothing → large increase → large decrease → nothing.
    Returns (signal_slice, t_slice, start_idx, end_idx).
    """
    baseline = np.median(signal)
    span = np.percentile(signal, 95) - np.percentile(signal, 5)
    if span < 1e-30:
        return signal.copy(), t.copy(), 0, len(signal) - 1
    margin = baseline_frac * span
    # Largest deviation from baseline (peak or trough)
    peak_idx = int(np.argmax(np.abs(signal - baseline)))
    # Expand left until we're at baseline (within margin)
    left = peak_idx
    while left > 0 and abs(signal[left] - baseline) > margin:
        left -= 1
    # Expand right until we're at baseline
    right = peak_idx
    while right < len(signal) - 1 and abs(signal[right] - baseline) > margin:
        right += 1
    # Extend to include flat baseline at ends
    extend_samples = int(0.002 * TEST_SIGNAL_SAMPLE_RATE_HZ)  # ~2 ms padding
    left = max(0, left - extend_samples)
    right = min(len(signal) - 1, right + extend_samples)
    return signal[left : right + 1].copy(), t[left : right + 1].copy(), left, right


def load_and_isolate_envelope(filepath: str) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Load file, find largest envelope, return (signal_segment, t_segment) or (None, None)."""
    sig, t = load_full_signal(filepath, MAX_LOAD_FOR_ENVELOPE)
    if sig is None or len(sig) < 10:
        return None, None
    seg, t_seg, _, _ = find_largest_envelope(sig, t)
    # Re-zero time
    t_seg = t_seg - t_seg[0]
    return seg, t_seg


# ──────────────────────────────────────────────────────────────────────────────
# Signal chain functions
# ──────────────────────────────────────────────────────────────────────────────
def interpolate_to_rate(signal: np.ndarray, t_signal: np.ndarray, t_target: np.ndarray) -> np.ndarray:
    """Interpolate signal from its time base to target time base."""
    return np.interp(t_target, t_signal, signal)


def butterworth_lpf_4th_order(signal: np.ndarray, fs_hz: float, enbw_hz: float) -> np.ndarray:
    """
    Apply a 4th order Butterworth lowpass filter with specified ENBW.
    ENBW for 4th order Butterworth ≈ 1.026 × f_cutoff.
    """
    f_cutoff = enbw_hz / 1.026
    # Normalized frequency (0 to 1, where 1 = Nyquist = fs/2)
    nyquist = fs_hz / 2.0
    wn = f_cutoff / nyquist
    # Clamp to valid range
    wn = max(1e-6, min(wn, 0.9999))
    # Design filter as second-order sections for numerical stability
    sos = butter(LPF_ORDER, wn, btype='low', output='sos')
    # Apply filter forward-backward for zero phase delay
    return sosfiltfilt(sos, signal)


def demodulate_iq(signal: np.ndarray, t: np.ndarray, f_ref_hz: float, fs_hz: float, 
                  lpf_enbw_hz: float = LPF_ENBW_HZ) -> np.ndarray:
    """
    Demodulation per README:
      X = signal × sin(ω_ref·t)   (in-phase)
      Y = signal × cos(ω_ref·t)   (quadrature, 90° shifted)
      4th order Butterworth LPF
      R = √(X² + Y²)
    """
    omega = 2.0 * np.pi * f_ref_hz
    ref_sin = np.sin(omega * t)
    ref_cos = np.cos(omega * t)
    X_raw = signal * ref_sin
    Y_raw = signal * ref_cos
    # 4th order Butterworth LPF with configurable ENBW
    X_lpf = butterworth_lpf_4th_order(X_raw, fs_hz, lpf_enbw_hz)
    Y_lpf = butterworth_lpf_4th_order(Y_raw, fs_hz, lpf_enbw_hz)
    R = np.sqrt(X_lpf**2 + Y_lpf**2)
    return R


def run_signal_chain(
    t: np.ndarray,
    envelope: np.ndarray,
    t_envelope: np.ndarray,
    carrier_vpp: float,
    dac_params: dict,
    adc_params: dict,
    opamp_params: dict,
    lpf_enbw_hz: float = LPF_ENBW_HZ,
) -> dict:
    """
    Run the full DLIA signal chain:
      1. DDS: Vpp sine wave as reference (DAC input)
      2. DAC: digital → analog with errors
      3. AM modulation: carrier × (1 + envelope_voltage)
         - envelope_voltage is actual voltage from Test_Signal.txt
         - For ~11mV peak signal, this gives ~1% modulation depth
      4. Op-amp (unity gain buffer): buffers signal with bandwidth/noise
      5. ADC: analog → digital with errors
      6. Demodulate ADC output

    Returns dict with all intermediate signals for plotting.
    """
    omega = 2.0 * np.pi * CARRIER_FREQ_HZ
    dac_v_ref = dac_params.get("v_ref", 1.0)

    # ── Step 1: DDS generates reference sine (DAC input) ──
    # Carrier: centered at Vpp/2 with amplitude Vpp/2, ranging from 0 to Vpp
    # carrier_vpp is the peak-to-peak voltage (e.g., 1V means 0 to 1V)
    # Normalize to [0, 1] for DAC input, then scale by v_ref
    
    # First, check envelope peak to leave headroom for AM modulation
    # The modulated signal = carrier × (1 + envelope), so max = carrier_peak × (1 + env_max)
    # To prevent clipping: carrier_peak × (1 + env_max) <= v_ref
    # So: carrier_peak <= v_ref / (1 + env_max)
    envelope_interp_preview = interpolate_to_rate(envelope, t_envelope, t)
    env_max = np.max(envelope_interp_preview)
    env_min = np.min(envelope_interp_preview)
    
    # Calculate max allowable carrier peak (leave 1% extra headroom)
    headroom_factor = 1.01
    max_carrier_peak = dac_v_ref / (headroom_factor * (1 + max(env_max, 0)))
    
    # Also ensure carrier doesn't go negative: carrier_min × (1 + env_min) >= 0
    # For unipolar carrier (0 to Vpp), minimum is 0, so this is always satisfied
    
    carrier_center = carrier_vpp / 2.0 / dac_v_ref  # Normalized center
    carrier_amp = carrier_vpp / 2.0 / dac_v_ref     # Normalized amplitude
    carrier_peak_volts = (carrier_center + carrier_amp) * dac_v_ref
    
    # Scale down if needed to prevent clipping
    if carrier_peak_volts > max_carrier_peak:
        scale = max_carrier_peak / carrier_peak_volts
        carrier_center *= scale
        carrier_amp *= scale
        print(f"Carrier scaled by {scale:.4f} to prevent clipping (env_max={env_max*1e3:.2f}mV)")
    
    dac_input_digital = carrier_center + carrier_amp * np.sin(omega * t)
    dac_input_digital = np.clip(dac_input_digital, 0.0, 1.0)

    # ── Step 2: DAC with errors ──
    dac_n_bits = int(dac_params.get("n_bits", 16))
    dac = DACSimulator(
        sample_rate_hz=DAC_SAMPLE_RATE_HZ,
        n_bits=dac_n_bits,
        v_ref=dac_v_ref,
        inl_lsb=dac_params["inl_lsb"],
        dnl_lsb=dac_params["dnl_lsb"],
        gain_error=dac_params["gain_error"],
        offset_error=dac_params["offset_error"],
        glitch_energy_frac=dac_params.get("glitch_energy_frac", 0.0),
        seed=SEED,
    )
    dac_output = dac.digital_to_analog(dac_input_digital)

    # Ideal DAC output (no errors) for comparison
    dac_output_ideal = dac_input_digital * dac_v_ref

    # ── Step 3: AM modulation with actual envelope voltage ──
    # Test_Signal.txt contains actual voltages (in volts)
    # Interpolate to DAC sample rate
    envelope_interp = interpolate_to_rate(envelope, t_envelope, t)
    
    # Use envelope values directly as voltages (NO normalization)
    # Modulation: carrier × (1 + envelope_voltage)
    # For ~11mV peak envelope and 0.5V carrier center, this is ~2% modulation
    modulated = dac_output * (1.0 + envelope_interp)
    
    # Store envelope info for comparison
    envelope_peak = np.max(np.abs(envelope_interp))
    carrier_amplitude_volts = carrier_amp * dac_v_ref
    modulation_depth_pct = (envelope_peak / 1.0) * 100  # As percentage of unity

    # ── Step 4: Op-amp in unity gain configuration (voltage follower) ──
    # Buffers the signal with bandwidth limitation and adds noise
    opamp_bandwidth = opamp_params.get("bandwidth_hz", 50e6)
    opamp_noise = opamp_params.get("noise_rms", 0.0)
    opamp_offset = opamp_params.get("offset_voltage", 0.0)
    opamp_gain_error = opamp_params.get("gain_error", 0.0)
    
    # Unity gain: V_out = V_in × (1 + gain_error) + offset
    opamp_output = modulated * (1.0 + opamp_gain_error) + opamp_offset
    
    # Add noise
    if opamp_noise > 0:
        rng = np.random.default_rng(SEED + 1)
        opamp_output = opamp_output + rng.normal(0, opamp_noise, len(opamp_output))
    
    # Apply bandwidth limitation (simple 1st order LPF if bandwidth < Nyquist/2)
    if opamp_bandwidth < DAC_SAMPLE_RATE_HZ / 4:
        from scipy.signal import butter, sosfilt
        nyq = DAC_SAMPLE_RATE_HZ / 2
        wn = min(opamp_bandwidth / nyq, 0.99)
        sos = butter(1, wn, btype='low', output='sos')
        opamp_output = sosfilt(sos, opamp_output)

    # ── Step 5: ADC with errors ──
    adc_v_ref = adc_params.get("v_ref", 1.0)
    adc_n_bits = int(adc_params.get("n_bits", 16))
    adc_input = np.clip(opamp_output, 0.0, adc_v_ref)
    
    adc = ADCSimulator(
        sample_rate_hz=ADC_SAMPLE_RATE_HZ,
        n_bits=adc_n_bits,
        v_ref=adc_v_ref,
        gain_error=adc_params["gain_error"],
        offset_error=adc_params["offset_error"],
        inl_lsb=adc_params["inl_lsb"],
        dnl_lsb=adc_params["dnl_lsb"],
        aperture_jitter_sec=adc_params["aperture_jitter_sec"],
        seed=SEED,
    )
    adc_codes = adc.analog_to_digital(adc_input)
    # Reconstruct voltage from ADC codes (use actual bit depth)
    max_code = (1 << adc_n_bits) - 1
    adc_output = (adc_codes.astype(float) / max_code) * adc_v_ref

    # ── Step 6: Demodulate ADC output to recover envelope ──
    R_demod = demodulate_iq(adc_output, t, CARRIER_FREQ_HZ, DAC_SAMPLE_RATE_HZ, lpf_enbw_hz)

    # Also demodulate DAC output (before adding envelope) to see DAC error effect
    R_dac = demodulate_iq(dac_output, t, CARRIER_FREQ_HZ, DAC_SAMPLE_RATE_HZ, lpf_enbw_hz)
    R_dac_ideal = demodulate_iq(dac_output_ideal, t, CARRIER_FREQ_HZ, DAC_SAMPLE_RATE_HZ, lpf_enbw_hz)

    return {
        "t": t,
        "envelope_voltage": envelope_interp,       # Actual voltage from Test_Signal.txt
        "envelope_peak": envelope_peak,            # Peak envelope voltage
        "modulation_depth_pct": modulation_depth_pct,
        "carrier_amp": carrier_amp,                # Carrier amplitude (normalized 0-1)
        "carrier_amp_volts": carrier_amplitude_volts,
        "dac_input": dac_input_digital,
        "dac_output": dac_output,
        "dac_output_ideal": dac_output_ideal,
        "dac_demod": R_dac,
        "dac_demod_ideal": R_dac_ideal,
        "opamp_output": opamp_output,              # Output after op-amp buffer
        "adc_input": adc_input,
        "adc_output": adc_output,
        "adc_demod": R_demod,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GUI
# ──────────────────────────────────────────────────────────────────────────────
def main():
    test_signal_path = os.path.join(_THIS_DIR, TEST_SIGNAL_FILENAME)

    # Load and isolate the largest envelope from Test_Signal.txt
    envelope_seg, t_envelope_seg = load_and_isolate_envelope(test_signal_path)
    if envelope_seg is None:
        print(f"ERROR: Could not load {test_signal_path}")
        print("Place Test_Signal.txt in the testing/ folder.")
        return

    print(f"Loaded envelope: {len(envelope_seg)} samples, "
          f"duration = {t_envelope_seg[-1]*1e3:.2f} ms")

    # Default parameters
    p = {
        "carrier_vpp": 1.0,          # Carrier peak-to-peak voltage
        "lpf_enbw_khz": 10.0,        # Demodulation LPF ENBW in kHz
        "graph_scale": 1.0,          # Manual scale factor for recovered signal
        "dc_bias_uv": 0.0,           # DC bias adjustment in µV
        "dac_bits": 16,
        "dac_v_ref": 1.0,
        "dac_inl_lsb": 0.0,
        "dac_dnl_lsb": 0.0,
        "dac_gain_pct_fs": 0.0,      # DAC gain error in %FS
        "dac_offset_pct_fs": 0.0,    # DAC offset error in %FS
        "opamp_bw_mhz": 50.0,        # Op-amp bandwidth in MHz
        "opamp_noise_uv": 0.0,       # Op-amp noise in µV RMS
        "opamp_offset_mv": 0.0,      # Op-amp offset in mV
        "adc_bits": 16,
        "adc_v_ref": 1.0,
        "adc_inl_lsb": 0.0,
        "adc_dnl_lsb": 0.0,
        "adc_gain_pct_fs": 0.0,      # ADC gain error in %FS
        "adc_offset_pct_fs": 0.0,    # ADC offset error in %FS
        "adc_jitter_sec": 0.0,
    }

    # ── Figure setup ──
    fig = plt.figure(figsize=(18, 12))
    fig.canvas.manager.set_window_title("DLIA Signal Chain: DAC → AM Modulation → OpAmp → ADC → Demod")
    
    # Main plot grid: 5 rows × 3 columns (time, FFT, stats)
    gs = GridSpec(5, 3, figure=fig, left=0.05, right=0.98, top=0.97, bottom=0.32,
                  hspace=0.40, wspace=0.20, width_ratios=[1, 1, 0.7])

    ax_env_t = fig.add_subplot(gs[0, 0])
    ax_env_f = fig.add_subplot(gs[0, 1])
    ax_dac_t = fig.add_subplot(gs[1, 0])
    ax_dac_f = fig.add_subplot(gs[1, 1])
    ax_adc_t = fig.add_subplot(gs[2, 0])
    ax_adc_f = fig.add_subplot(gs[2, 1])
    ax_cmp_t = fig.add_subplot(gs[3, 0])
    ax_cmp_f = fig.add_subplot(gs[3, 1])
    ax_err_t = fig.add_subplot(gs[4, 0])
    ax_err_f = fig.add_subplot(gs[4, 1])
    # Stats panel spans rows 2-4 on the right
    ax_err_stats = fig.add_subplot(gs[2:5, 2])

    # ── Slider specifications (organized by category) ──
    slider_specs_col1 = [  # Signal & Display
        {"label": "Carrier V", "key": "carrier_vpp", "vmin": 0.1, "vmax": 2.0},
        {"label": "LPF kHz", "key": "lpf_enbw_khz", "vmin": 1.0, "vmax": 100.0},
        {"label": "Scale", "key": "graph_scale", "vmin": 0.1, "vmax": 10.0},
        {"label": "DC µV", "key": "dc_bias_uv", "vmin": -100000.0, "vmax": 100000.0},
        {"label": "OA BW", "key": "opamp_bw_mhz", "vmin": 1.0, "vmax": 100.0},
        {"label": "OA noise", "key": "opamp_noise_uv", "vmin": 0, "vmax": 10},
        {"label": "OA offset", "key": "opamp_offset_mv", "vmin": -10, "vmax": 10},
    ]
    slider_specs_col2 = [  # DAC
        {"label": "bits", "key": "dac_bits", "vmin": 4, "vmax": 24},
        {"label": "Vref", "key": "dac_v_ref", "vmin": 0.5, "vmax": 2.0},
        {"label": "INL", "key": "dac_inl_lsb", "vmin": 0, "vmax": 16},
        {"label": "DNL", "key": "dac_dnl_lsb", "vmin": 0, "vmax": 6},
        {"label": "gain%", "key": "dac_gain_pct_fs", "vmin": -10.0, "vmax": 10.0},
        {"label": "offset%", "key": "dac_offset_pct_fs", "vmin": -10.0, "vmax": 10.0},
    ]
    slider_specs_col3 = [  # ADC
        {"label": "bits", "key": "adc_bits", "vmin": 4, "vmax": 24},
        {"label": "Vref", "key": "adc_v_ref", "vmin": 0.5, "vmax": 2.0},
        {"label": "INL", "key": "adc_inl_lsb", "vmin": 0, "vmax": 16},
        {"label": "DNL", "key": "adc_dnl_lsb", "vmin": 0, "vmax": 6},
        {"label": "gain%", "key": "adc_gain_pct_fs", "vmin": -10.0, "vmax": 10.0},
        {"label": "offset%", "key": "adc_offset_pct_fs", "vmin": -10.0, "vmax": 10.0},
        {"label": "jitter", "key": "adc_jitter_sec", "vmin": 0, "vmax": 5e-12},
    ]

    # Slider layout: 3 columns at bottom (below plots which end at bottom=0.32)
    row_height = 0.018
    row_step = 0.021
    col_width = 0.31
    col_starts = [0.02, 0.35, 0.68]
    slider_bottom = 0.27

    # Storage for slider widgets and state
    slider_widgets = []
    _updating = [False]
    _optimal_values = {"dc_bias_uv": 0.0, "scale": 1.0}  # Store optimal values for auto-adjust

    def format_val(v):
        """Format value for display."""
        if abs(v) < 1e-6 and v != 0:
            return f"{v:.2e}"
        elif abs(v) >= 1000:
            return f"{v:.2e}"
        elif v == int(v):
            return f"{int(v)}"
        else:
            return f"{v:.4g}"

    def create_slider_column(specs, col_idx):
        """Create a column of sliders."""
        x_start = col_starts[col_idx]
        label_width = 0.055  # Fixed width for labels
        for idx, spec in enumerate(specs):
            y = slider_bottom - idx * row_step
            vmin, vmax = spec["vmin"], spec["vmax"]
            valinit = np.clip(float(p.get(spec["key"], vmin)), vmin, vmax)
            
            # Label (separate text, not using slider's built-in label)
            fig.text(x_start, y + row_height/2, spec["label"], fontsize=7, 
                    va='center', ha='left', color='#333')
            
            # Slider without label
            slider_x = x_start + label_width
            slider_w = col_width - label_width - 0.04
            ax_slider = fig.add_axes([slider_x, y, slider_w, row_height])
            slider = Slider(ax_slider, "", vmin, vmax, valinit=valinit)
            slider.valtext.set_visible(False)
            
            # Value display
            ax_val = fig.add_axes([slider_x + slider_w + 0.005, y, 0.03, row_height])
            ax_val.set_axis_off()
            val_text = ax_val.text(0.5, 0.5, format_val(valinit), ha='center', va='center', 
                                   fontsize=7, transform=ax_val.transAxes)
            
            slider_widgets.append({
                "slider": slider,
                "key": spec["key"],
                "spec": spec,
                "val_text": val_text,
                "val_ax": ax_val,
            })

    # Create all slider columns with headers
    header_y = slider_bottom + 0.018
    fig.text(col_starts[0] + col_width/2, header_y, "Signal & OpAmp", ha='center', fontsize=9, fontweight='bold', color='#333')
    fig.text(col_starts[1] + col_width/2, header_y, "DAC Parameters", ha='center', fontsize=9, fontweight='bold', color='#333')
    fig.text(col_starts[2] + col_width/2, header_y, "ADC Parameters", ha='center', fontsize=9, fontweight='bold', color='#333')
    
    create_slider_column(slider_specs_col1, 0)
    create_slider_column(slider_specs_col2, 1)
    create_slider_column(slider_specs_col3, 2)

    def on_slider_change(idx):
        """Update value display when slider changes."""
        def handler(val):
            if _updating[0]:
                return
            widget = slider_widgets[idx]
            widget["val_text"].set_text(format_val(val))
            widget["val_ax"].figure.canvas.draw_idle()
        return handler

    # Connect slider callbacks
    for idx, widget in enumerate(slider_widgets):
        widget["slider"].on_changed(on_slider_change(idx))

    def get_params():
        return {w["key"]: w["slider"].val for w in slider_widgets}

    def update(_=None):
        par = get_params()

        # Compute DAC time array based on envelope duration
        duration = t_envelope_seg[-1]
        n_samples = int(duration * DAC_SAMPLE_RATE_HZ)
        if n_samples < 100:
            return
        t_dac = np.arange(n_samples, dtype=float) / DAC_SAMPLE_RATE_HZ

        dac_params = {
            "n_bits": int(par["dac_bits"]),
            "v_ref": par["dac_v_ref"],
            "inl_lsb": par["dac_inl_lsb"],
            "dnl_lsb": par["dac_dnl_lsb"],
            "gain_error": par["dac_gain_pct_fs"] / 100.0,      # Convert %FS to fractional
            "offset_error": par["dac_offset_pct_fs"] / 100.0,  # Convert %FS to fractional
            "glitch_energy_frac": 0.0,
        }
        adc_params = {
            "n_bits": int(par["adc_bits"]),
            "v_ref": par["adc_v_ref"],
            "inl_lsb": par["adc_inl_lsb"],
            "dnl_lsb": par["adc_dnl_lsb"],
            "gain_error": par["adc_gain_pct_fs"] / 100.0,      # Convert %FS to fractional
            "offset_error": par["adc_offset_pct_fs"] / 100.0,  # Convert %FS to fractional
            "aperture_jitter_sec": par["adc_jitter_sec"],
        }
        opamp_params = {
            "bandwidth_hz": par["opamp_bw_mhz"] * 1e6,
            "noise_rms": par["opamp_noise_uv"] * 1e-6,
            "offset_voltage": par["opamp_offset_mv"] * 1e-3,
            "gain_error": 0.0,  # Unity gain
        }

        try:
            lpf_enbw_hz = par["lpf_enbw_khz"] * 1e3  # Convert kHz to Hz
            result = run_signal_chain(
                t_dac, envelope_seg, t_envelope_seg,
                par["carrier_vpp"], dac_params, adc_params, opamp_params,
                lpf_enbw_hz=lpf_enbw_hz
            )
        except Exception as e:
            print(f"Error in signal chain: {e}")
            return

        t = result["t"]
        n = len(t)
        t_ms = t * 1e3  # Full time array in ms (ALL samples)

        # FFT setup
        n_fft = min(16384, n)
        freqs_hz = np.fft.rfftfreq(n_fft, 1.0 / DAC_SAMPLE_RATE_HZ)
        freqs_khz = freqs_hz / 1e3

        def plot_fft(ax, sig, color, label=None):
            spec = np.fft.rfft(sig[:n_fft] - np.mean(sig[:n_fft]))
            ax.semilogy(freqs_khz, np.maximum(np.abs(spec), 1e-20), color=color, label=label, alpha=0.8)

        # ── Row 1: Original envelope (full duration, ALL samples) ──
        ax_env_t.clear()
        env_voltage = result["envelope_voltage"]  # Actual voltage from Test_Signal.txt
        env_peak = result["envelope_peak"]
        mod_depth = result["modulation_depth_pct"]
        ax_env_t.plot(t_ms, env_voltage * 1e3, color="C0", linewidth=0.5)  # Show in mV
        ax_env_t.set_ylabel("Voltage (mV)")
        ax_env_t.set_title(f"Original Envelope (peak={env_peak*1e3:.2f} mV, mod={mod_depth:.2f}%)", fontsize=9)
        ax_env_t.grid(True, alpha=0.3)

        ax_env_f.clear()
        plot_fft(ax_env_f, env_voltage, "C0")
        ax_env_f.set_ylabel("|FFT|")
        ax_env_f.set_title("FFT: Original Envelope", fontsize=9)
        ax_env_f.grid(True, alpha=0.3)

        # ── Row 2: DAC percent error ──
        ax_dac_t.clear()
        dac_in = result["dac_input"] * par["dac_v_ref"]
        dac_out = result["dac_output"]
        dac_amplitude = (np.max(dac_in) - np.min(dac_in)) / 2.0
        dac_error_pct = (dac_out - dac_in) / dac_amplitude * 100.0
        dac_rms_err = np.sqrt(np.mean(dac_error_pct**2))
        dac_max_err = np.max(np.abs(dac_error_pct))
        ax_dac_t.plot(t_ms, dac_error_pct, color="C1", linewidth=0.5)
        ax_dac_t.set_ylabel("Error (%)")
        ax_dac_t.set_title(f"DAC Error (RMS={dac_rms_err:.2e}%, Max={dac_max_err:.2e}%)", fontsize=9)
        ax_dac_t.grid(True, alpha=0.3)
        ax_dac_t.axhline(0, color="gray", linestyle="--", alpha=0.5)

        ax_dac_f.clear()
        plot_fft(ax_dac_f, dac_out - dac_in, "C1", "Error")
        ax_dac_f.set_ylabel("|FFT|")
        ax_dac_f.set_title("FFT: DAC Error", fontsize=9)
        ax_dac_f.grid(True, alpha=0.3)
        ax_dac_f.axvline(CARRIER_FREQ_HZ/1e3, color="gray", linestyle="--", alpha=0.5)

        # ── Row 3: ADC percent error ──
        ax_adc_t.clear()
        adc_in = result["adc_input"]
        adc_out = result["adc_output"]
        adc_amplitude = (np.max(adc_in) - np.min(adc_in)) / 2.0
        if adc_amplitude < 1e-10:
            adc_amplitude = 1.0
        adc_error_pct = (adc_out - adc_in) / adc_amplitude * 100.0
        adc_rms_err = np.sqrt(np.mean(adc_error_pct**2))
        adc_max_err = np.max(np.abs(adc_error_pct))
        ax_adc_t.plot(t_ms, adc_error_pct, color="C2", linewidth=0.5)
        ax_adc_t.set_ylabel("Error (%)")
        ax_adc_t.set_title(f"ADC Error (RMS={adc_rms_err:.2e}%, Max={adc_max_err:.2e}%)", fontsize=9)
        ax_adc_t.grid(True, alpha=0.3)
        ax_adc_t.axhline(0, color="gray", linestyle="--", alpha=0.5)

        ax_adc_f.clear()
        plot_fft(ax_adc_f, adc_out - adc_in, "C2", "Error")
        ax_adc_f.set_ylabel("|FFT|")
        ax_adc_f.set_title("FFT: ADC Error", fontsize=9)
        ax_adc_f.grid(True, alpha=0.3)
        ax_adc_f.axvline(CARRIER_FREQ_HZ/1e3, color="gray", linestyle="--", alpha=0.5)

        # ── Row 4: Original vs Demodulated vs Error ──
        ax_cmp_t.clear()
        adc_demod = result["adc_demod"]
        carrier_amp = result["carrier_amp"]  # Normalized carrier amplitude (0-1)
        carrier_amp_volts = result["carrier_amp_volts"]
        
        # Skip first 10% of samples (filter transient)
        skip_samples = max(1, n // 10)
        
        # AM modulation: signal = carrier × (1 + envelope_voltage)
        # After IQ demod: R ≈ (carrier_amp_volts/2) × (1 + envelope_voltage)
        # True baseline = carrier_amp_volts / 2
        dac_vref = par["dac_v_ref"]
        theoretical_baseline = carrier_amp * dac_vref / 2.0
        
        median_baseline = np.median(adc_demod[skip_samples:])
        if theoretical_baseline > 1e-10 and 0.5 < median_baseline / theoretical_baseline < 2.0:
            baseline = theoretical_baseline
        else:
            baseline = median_baseline if median_baseline > 1e-10 else 1.0
        
        # Recover the modulation: (R - baseline) / baseline ≈ envelope_voltage
        demod_recovered = (adc_demod - baseline) / baseline
        
        # The ACTUAL modulation applied was the envelope voltage directly
        original_modulation = env_voltage  # Actual voltage from Test_Signal.txt
        
        # Calculate what scale factor SHOULD be (for diagnostics)
        # If envelope peak is X mV, and recovered peak is Y, scale = X/Y
        orig_peak = np.max(np.abs(original_modulation[skip_samples:]))
        demod_peak = np.max(np.abs(demod_recovered[skip_samples:]))
        suggested_scale = orig_peak / demod_peak if demod_peak > 1e-15 else 1.0
        
        # Use manual graph scale factor and DC bias
        graph_scale = par["graph_scale"]
        dc_bias_v = par["dc_bias_uv"] * 1e-6  # Convert µV to V
        demod_scaled = demod_recovered * graph_scale + dc_bias_v
        
        # Calculate optimal DC bias (the value that minimizes mean squared error)
        # Optimal bias = mean(original) - mean(scaled_recovered_without_bias)
        demod_scaled_no_bias = demod_recovered[skip_samples:] * graph_scale
        orig_region_for_bias = original_modulation[skip_samples:]
        optimal_dc_bias_v = np.mean(orig_region_for_bias) - np.mean(demod_scaled_no_bias)
        optimal_dc_bias_uv = optimal_dc_bias_v * 1e6
        
        # Store optimal values for auto-adjust buttons
        _optimal_values["dc_bias_uv"] = optimal_dc_bias_uv
        _optimal_values["scale"] = suggested_scale
        
        # Print diagnostic info
        print(f"\n=== DIAGNOSTICS ===")
        print(f"Carrier: Vpp={par['carrier_vpp']:.6f}V, amp_normalized={carrier_amp:.6f}, amp_volts={carrier_amp*dac_vref:.6f}V")
        print(f"Baseline: theoretical={theoretical_baseline:.6f}V, median={median_baseline:.6f}V, used={baseline:.6f}V")
        print(f"Demod R: min={np.min(adc_demod[skip_samples:]):.6f}, max={np.max(adc_demod[skip_samples:]):.6f}, mean={np.mean(adc_demod[skip_samples:]):.6f}")
        print(f"Expected R range: {baseline*(1+np.min(env_voltage[skip_samples:])):.6f} to {baseline*(1+np.max(env_voltage[skip_samples:])):.6f}")
        print(f"Envelope: min={np.min(env_voltage)*1e3:.6f}mV, max={np.max(env_voltage)*1e3:.6f}mV")
        print(f"Recovered: min={np.min(demod_recovered[skip_samples:])*1e3:.6f}mV, max={np.max(demod_recovered[skip_samples:])*1e3:.6f}mV")
        print(f"Peaks: original={orig_peak*1e3:.6f}mV, demod_raw={demod_peak*1e3:.6f}mV")
        print(f"Suggested scale={suggested_scale:.6f} (should be ~1.0 with no errors)")
        print(f"DC bias: current={par['dc_bias_uv']:.6f}µV, optimal={optimal_dc_bias_uv:.6f}µV")
        
        # Error = scaled recovered with DC bias - original
        error = demod_scaled - original_modulation
        error_region = error[skip_samples:]
        rms_error = np.sqrt(np.mean(error_region**2))
        max_error = np.max(np.abs(error_region))
        
        # Trim data to exclude transient for plotting (show in mV)
        t_ms_trim = t_ms[skip_samples:]
        orig_trim = original_modulation[skip_samples:] * 1e3  # Convert to mV
        demod_trim = demod_scaled[skip_samples:] * 1e3
        error_trim = error[skip_samples:] * 1e3
        
        # Plot original and recovered (without transient, in mV)
        ax_cmp_t.plot(t_ms_trim, orig_trim, color="C0", alpha=0.8, linewidth=0.6, label="Original")
        bias_label = f"Recovered ×{graph_scale:.2f}" + (f" +{par['dc_bias_uv']:.1f}µV" if par['dc_bias_uv'] != 0 else "")
        ax_cmp_t.plot(t_ms_trim, demod_trim, color="C4", alpha=0.7, linewidth=0.5, label=bias_label)
        ax_cmp_t.set_ylabel("Voltage (mV)")
        ax_cmp_t.set_xlabel("Time (ms)")
        lpf_enbw_khz = par["lpf_enbw_khz"]
        ax_cmp_t.set_title(f"Envelope Recovery (LPF={lpf_enbw_khz:.0f}kHz, opt. bias={optimal_dc_bias_uv:.2f}µV)", fontsize=9)
        ax_cmp_t.legend(loc="upper right", fontsize=6)
        ax_cmp_t.grid(True, alpha=0.3)
        ax_cmp_t.axhline(0, color="gray", linestyle="--", alpha=0.3)

        ax_cmp_f.clear()
        plot_fft(ax_cmp_f, orig_trim, "C0", "Original")
        plot_fft(ax_cmp_f, demod_trim, "C4", "Recovered")
        ax_cmp_f.set_ylabel("|FFT|")
        ax_cmp_f.set_xlabel("Frequency (kHz)")
        ax_cmp_f.set_title("FFT: Original vs Recovered", fontsize=9)
        ax_cmp_f.legend(loc="upper right", fontsize=6)
        ax_cmp_f.grid(True, alpha=0.3)

        # ── Row 5: Dedicated Error Plot and Statistics ──
        ax_err_t.clear()
        
        # Calculate comprehensive error statistics (6 decimal precision)
        orig_region = original_modulation[skip_samples:]
        demod_region = demod_scaled[skip_samples:]
        error_region_v = error[skip_samples:]  # Error in volts
        
        # Basic statistics
        n_pts = len(error_region_v)
        mean_error = np.mean(error_region_v)
        std_error = np.std(error_region_v)
        rms_error = np.sqrt(np.mean(error_region_v**2))
        max_error = np.max(error_region_v)
        min_error = np.min(error_region_v)
        max_abs_error = np.max(np.abs(error_region_v))
        
        # Peak values
        orig_max = np.max(orig_region)
        orig_min = np.min(orig_region)
        orig_peak_to_peak = orig_max - orig_min
        demod_max = np.max(demod_region)
        demod_min = np.min(demod_region)
        
        # Relative errors (as percentage of original peak-to-peak)
        if orig_peak_to_peak > 1e-15:
            rms_pct = (rms_error / orig_peak_to_peak) * 100
            max_abs_pct = (max_abs_error / orig_peak_to_peak) * 100
        else:
            rms_pct = 0.0
            max_abs_pct = 0.0
        
        # Correlation coefficient
        if np.std(orig_region) > 1e-15 and np.std(demod_region) > 1e-15:
            correlation = np.corrcoef(orig_region, demod_region)[0, 1]
        else:
            correlation = 0.0
        
        # Plot error (in µV for better scale)
        error_uv = error_trim * 1e3  # mV to µV
        ax_err_t.plot(t_ms_trim, error_uv, color="C3", linewidth=0.6)
        ax_err_t.set_ylabel("Error (µV)")
        ax_err_t.set_xlabel("Time (ms)")
        ax_err_t.set_title(f"Recovery Error (RMS={rms_error*1e6:.2f} µV, Max={max_abs_error*1e6:.2f} µV)", fontsize=9)
        ax_err_t.grid(True, alpha=0.3)
        ax_err_t.axhline(0, color="gray", linestyle="--", alpha=0.5)
        
        # FFT of error
        ax_err_f.clear()
        plot_fft(ax_err_f, error_uv, "C3", "Error")
        ax_err_f.set_ylabel("|FFT| (µV)")
        ax_err_f.set_xlabel("Frequency (kHz)")
        ax_err_f.set_title("FFT of Recovery Error", fontsize=9)
        ax_err_f.grid(True, alpha=0.3)
        
        # Statistics panel
        ax_err_stats.clear()
        ax_err_stats.set_axis_off()
        
        stats_text = (
            f"╔══════════════════════════════════════╗\n"
            f"║   ENVELOPE RECOVERY STATISTICS       ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ ORIGINAL ENVELOPE:                   ║\n"
            f"║   Peak (max):    {orig_max*1e3:+.6f} mV      ║\n"
            f"║   Peak (min):    {orig_min*1e3:+.6f} mV      ║\n"
            f"║   Peak-to-Peak:  {orig_peak_to_peak*1e3:.6f} mV       ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ RECOVERED (×{graph_scale:.2f}):                    ║\n"
            f"║   Peak (max):    {demod_max*1e3:+.6f} mV      ║\n"
            f"║   Peak (min):    {demod_min*1e3:+.6f} mV      ║\n"
            f"║   Sugg. scale:   {suggested_scale:.6f}          ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ DC BIAS (µV):                        ║\n"
            f"║   Current:       {par['dc_bias_uv']:+.6f}         ║\n"
            f"║   Optimal:       {optimal_dc_bias_uv:+.6f}         ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ ERROR (µV):                          ║\n"
            f"║   Mean:          {mean_error*1e6:+.6f}         ║\n"
            f"║   Std Dev:       {std_error*1e6:.6f}          ║\n"
            f"║   RMS:           {rms_error*1e6:.6f}          ║\n"
            f"║   Max |Error|:   {max_abs_error*1e6:.6f}          ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ RELATIVE (% of P-P):                 ║\n"
            f"║   RMS:           {rms_pct:.6f} %          ║\n"
            f"║   Max |Error|:   {max_abs_pct:.6f} %          ║\n"
            f"╠══════════════════════════════════════╣\n"
            f"║ CORRELATION:  r={correlation:.6f}          ║\n"
            f"║ Samples: {n_pts:,} (excl. {skip_samples:,})    ║\n"
            f"╚══════════════════════════════════════╝"
        )
        
        ax_err_stats.text(0.02, 0.98, stats_text, transform=ax_err_stats.transAxes,
                         fontsize=8, fontfamily='monospace', verticalalignment='top',
                         bbox=dict(boxstyle='round', facecolor='#f5f5dc', alpha=0.9, edgecolor='#8b8b00'))

        fig.canvas.draw_idle()

    # ── Buttons ──
    update_ax = fig.add_axes([0.03, 0.02, 0.08, 0.035])
    btn_update = Button(update_ax, "UPDATE", color='lightgreen', hovercolor='green')
    btn_update.on_clicked(lambda _: update())

    reset_ax = fig.add_axes([0.115, 0.02, 0.06, 0.035])
    btn_reset = Button(reset_ax, "Reset", color='lightgray', hovercolor='darkgray')

    auto_ax = fig.add_axes([0.18, 0.02, 0.08, 0.035])
    btn_auto = Button(auto_ax, "Auto Bias", color='lightyellow', hovercolor='gold')

    def reset(_=None):
        _updating[0] = True
        for widget in slider_widgets:
            key = widget["key"]
            if key in p:
                default_val = np.clip(p[key], widget["spec"]["vmin"], widget["spec"]["vmax"])
                widget["slider"].set_val(default_val)
                widget["val_text"].set_text(format_val(default_val))
        _updating[0] = False
        update()

    def auto_fit(_=None):
        """Automatically set DC bias to optimal value."""
        _updating[0] = True
        for widget in slider_widgets:
            if widget["key"] == "dc_bias_uv":
                opt_bias = np.clip(_optimal_values["dc_bias_uv"], widget["spec"]["vmin"], widget["spec"]["vmax"])
                widget["slider"].set_val(opt_bias)
                widget["val_text"].set_text(format_val(opt_bias))
                break
        _updating[0] = False
        update()

    btn_reset.on_clicked(reset)
    btn_auto.on_clicked(auto_fit)

    # ── Command input ──
    ax_cmd = fig.add_axes([0.28, 0.02, 0.22, 0.035])
    cmd_box = TextBox(ax_cmd, "Set: ", initial="")
    cmd_box.drawon = False
    
    ax_status = fig.add_axes([0.51, 0.02, 0.28, 0.035])
    ax_status.set_axis_off()
    status_text = ax_status.text(0, 0.5, "Format: param_name value (e.g., dc_bias_uv 5.0)", 
                                  fontsize=8, va='center', transform=ax_status.transAxes, color='gray')
    
    def on_cmd_submit(text):
        """Parse command and set parameter value."""
        parts = text.strip().split()
        if len(parts) != 2:
            status_text.set_text("Format: param_name value")
            status_text.set_color('red')
            fig.canvas.draw_idle()
            return
        param_name, val_str = parts
        try:
            new_val = float(val_str)
        except ValueError:
            status_text.set_text(f"Invalid number: {val_str}")
            status_text.set_color('red')
            fig.canvas.draw_idle()
            return
        for widget in slider_widgets:
            if widget["key"] == param_name:
                spec = widget["spec"]
                new_val = np.clip(new_val, spec["vmin"], spec["vmax"])
                _updating[0] = True
                widget["slider"].set_val(new_val)
                widget["val_text"].set_text(format_val(new_val))
                _updating[0] = False
                status_text.set_text(f"✓ {param_name} = {format_val(new_val)}")
                status_text.set_color('green')
                fig.canvas.draw_idle()
                return
        status_text.set_text(f"Unknown: {param_name}")
        status_text.set_color('red')
        fig.canvas.draw_idle()
    
    cmd_box.on_submit(on_cmd_submit)

    # ── Info label ──
    fig.text(0.85, 0.025, "DDS→DAC→AM→OpAmp→ADC→Demod", 
             fontsize=8, ha='center', va='center', style='italic', color='gray')

    update()
    plt.show()


if __name__ == "__main__":
    main()
