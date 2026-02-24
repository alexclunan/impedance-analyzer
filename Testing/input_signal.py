import matplotlib.pyplot as plt
import numpy as np

# Load the voltage data from the file
# Assuming the file contains one voltage value per line
file_path = './Testing/Test_Signal.txt'
voltage = np.loadtxt(file_path)

# Signal parameters provided
sampling_rate = 14000  # 14 kHz
num_samples = len(voltage)

# Create the time axis
# Time = Index / Sampling Rate
time = np.arange(num_samples) / sampling_rate

# ══════════════════════════════════════════════════════════════════════════════
# Compute FFT with zero-padding for high frequency resolution
# ══════════════════════════════════════════════════════════════════════════════

# Zero-pad for higher frequency resolution (8x padding)
n_fft = num_samples * 8
freq_resolution = sampling_rate / n_fft

# Remove DC component for better dynamic range visualization
voltage_ac = voltage - np.mean(voltage)

# Compute FFT
fft_result = np.fft.rfft(voltage_ac, n=n_fft)
fft_magnitude = np.abs(fft_result) / num_samples  # Normalize by original length
fft_magnitude_db = 20 * np.log10(np.maximum(fft_magnitude, 1e-12))  # Convert to dB

# Frequency axis
frequencies = np.fft.rfftfreq(n_fft, d=1/sampling_rate)

# ══════════════════════════════════════════════════════════════════════════════
# Plotting
# ══════════════════════════════════════════════════════════════════════════════

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# ── Plot 1: Time domain (full) ──
ax1 = axes[0, 0]
ax1.plot(time, voltage * 1e3, label='Voltage Signal', color='b', linewidth=0.5)
ax1.set_title('Voltage vs. Time (Full Signal)')
ax1.set_xlabel('Time (seconds)')
ax1.set_ylabel('Voltage (mV)')
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.legend()

# ── Plot 2: FFT (full spectrum) ──
ax2 = axes[0, 1]
ax2.semilogy(frequencies, fft_magnitude * 1e3, color='r', linewidth=0.5)
ax2.set_title(f'FFT Magnitude (Full Spectrum, Resolution: {freq_resolution*1e3:.3f} mHz)')
ax2.set_xlabel('Frequency (Hz)')
ax2.set_ylabel('Magnitude (mV)')
ax2.set_xlim(0, sampling_rate / 2)
ax2.grid(True, linestyle='--', alpha=0.7)

# ── Plot 3: FFT zoomed to DC (0-100 Hz) ──
ax3 = axes[1, 0]
dc_zoom_max = 100  # Hz
mask_dc = frequencies <= dc_zoom_max
ax3.plot(frequencies[mask_dc], fft_magnitude[mask_dc] * 1e3, color='g', linewidth=0.8)
ax3.set_title(f'FFT Near DC (0-{dc_zoom_max} Hz)')
ax3.set_xlabel('Frequency (Hz)')
ax3.set_ylabel('Magnitude (mV)')
ax3.set_xlim(0, dc_zoom_max)
ax3.grid(True, linestyle='--', alpha=0.7)

# ── Plot 4: FFT zoomed to very low frequencies (0-10 Hz) with dB scale ──
ax4 = axes[1, 1]
dc_zoom_max_detail = 10  # Hz
mask_detail = frequencies <= dc_zoom_max_detail
ax4.plot(frequencies[mask_detail], fft_magnitude_db[mask_detail], color='purple', linewidth=0.8)
ax4.set_title(f'FFT Detail Near DC (0-{dc_zoom_max_detail} Hz, dB Scale)')
ax4.set_xlabel('Frequency (Hz)')
ax4.set_ylabel('Magnitude (dB)')
ax4.set_xlim(0, dc_zoom_max_detail)
ax4.grid(True, linestyle='--', alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════════
# Print statistics
# ══════════════════════════════════════════════════════════════════════════════

print(f"═══════════════════════════════════════════════════════════════")
print(f"                    SIGNAL ANALYSIS                            ")
print(f"═══════════════════════════════════════════════════════════════")
print(f"Signal duration:       {time[-1]:.3f} seconds")
print(f"Number of samples:     {num_samples:,}")
print(f"Sampling rate:         {sampling_rate:,} Hz")
print(f"FFT size (zero-padded):{n_fft:,}")
print(f"Frequency resolution:  {freq_resolution*1e3:.6f} mHz ({freq_resolution:.6f} Hz)")
print(f"───────────────────────────────────────────────────────────────")
print(f"Voltage DC (mean):     {np.mean(voltage)*1e3:.6f} mV")
print(f"Voltage RMS (AC):      {np.std(voltage)*1e3:.6f} mV")
print(f"Voltage peak-to-peak:  {(np.max(voltage)-np.min(voltage))*1e3:.6f} mV")
print(f"Voltage min:           {np.min(voltage)*1e3:.6f} mV")
print(f"Voltage max:           {np.max(voltage)*1e3:.6f} mV")
print(f"═══════════════════════════════════════════════════════════════")

# Find dominant frequencies near DC (excluding DC itself)
dc_exclude = 0.1  # Exclude frequencies below 0.1 Hz
mask_peaks = (frequencies > dc_exclude) & (frequencies < 100)
if np.any(mask_peaks):
    peak_idx = np.argmax(fft_magnitude[mask_peaks])
    peak_freq = frequencies[mask_peaks][peak_idx]
    peak_mag = fft_magnitude[mask_peaks][peak_idx]
    print(f"Dominant freq (0.1-100 Hz): {peak_freq:.6f} Hz, magnitude: {peak_mag*1e3:.6f} mV")
print(f"═══════════════════════════════════════════════════════════════")

# Display the plot
plt.tight_layout()
plt.show()