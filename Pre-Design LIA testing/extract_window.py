"""
Extract 1-second window from ziBin data for testbench use.

Window selection reasoning:
- Full dataset: 639,709 samples at ~14,391 Hz, 44.45 seconds
- Rolling window analysis (1-second non-overlapping, local mean subtraction):
  Window 17 (start=244647, t=11260.7166s):
    local_ptp = 227.66 µV  <- HIGHEST of all 44 windows
    local_std = 3.30 µV
    events above 4*local_std = 32
    Contains global max (+114.71 µV local / +103.18 µV global-AC) at index 250157
    Contains global min (-112.95 µV local / -124.48 µV global-AC) at index 250164
  These two extremes are 7 samples apart — a classic bipolar Gaussian cell event.
  Window 29 has more events (66) but lower ptp (194.67 µV).
  Window 17 is chosen: highest dynamic range, contains the global max/min pair.
"""

import numpy as np
import pathlib

# ── Load ziBin ──────────────────────────────────────────────────────────────
DATA_PATH = pathlib.Path(
    "sample_data/20251106_1MHz_3V_14ksps_500Hz_1kohm_T6_S1/D1/Freq1.ziBin"
)
raw = np.fromfile(DATA_PATH, dtype=">f8")
n_records = len(raw) // 7
data = raw[: n_records * 7].reshape(n_records, 7)
# columns: t, x, y, freq, dio, auxin0, auxin1
t_col = data[:, 0]
x_col = data[:, 1]

print(f"Total records  : {n_records:,}")
print(f"Sample rate    : {n_records / (t_col[-1] - t_col[0]):.2f} Hz")
print(f"Duration       : {t_col[-1] - t_col[0]:.3f} s")

# ── Estimated sample rate ────────────────────────────────────────────────────
fs_est = n_records / (t_col[-1] - t_col[0])  # ~14391 Hz
window_samples = round(fs_est)                # 1 second worth

# ── Identify window 17 ───────────────────────────────────────────────────────
WIN_START = 244647
WIN_END   = min(WIN_START + window_samples, n_records)
x_win     = x_col[WIN_START:WIN_END]
t_win     = t_col[WIN_START:WIN_END]
n_win     = len(x_win)

print(f"\nWindow 17:")
print(f"  Start index   : {WIN_START:,}")
print(f"  End index     : {WIN_END:,}")
print(f"  Samples       : {n_win:,}")
print(f"  t_start       : {t_win[0]:.4f} s")
print(f"  t_end         : {t_win[-1]:.4f} s")

# ── Local mean subtraction ───────────────────────────────────────────────────
x_ac = x_win - np.mean(x_win)

print(f"\nAC statistics (after local mean removal):")
print(f"  Mean (should be ~0): {np.mean(x_ac)*1e6:.4f} µV")
print(f"  Std              : {np.std(x_ac)*1e6:.4f} µV")
print(f"  Peak-to-peak     : {(np.max(x_ac) - np.min(x_ac))*1e6:.4f} µV")
print(f"  Max              : {np.max(x_ac)*1e6:.4f} µV")
print(f"  Min              : {np.min(x_ac)*1e6:.4f} µV")

# ── Scale to Q1.15 ───────────────────────────────────────────────────────────
# Q1.15: DC baseline = 16384 (0.5 full-scale), depth = ±14746
# Map peak AC deviation -> ±14746 counts
ENVELOPE_DC_Q15    = 16384
ENVELOPE_DEPTH_Q15 = 14746

peak_ac = np.max(np.abs(x_ac))
scale   = ENVELOPE_DEPTH_Q15 / peak_ac

print(f"\nQ1.15 scaling:")
print(f"  Peak AC        : {peak_ac*1e6:.4f} µV")
print(f"  Scale factor   : {scale:.2f} counts/V")
print(f"  = {scale/1e3:.2f} counts/mV")

envelope_float = ENVELOPE_DC_Q15 + x_ac * scale
envelope_int   = np.round(envelope_float).astype(np.int16)

print(f"\nQ1.15 envelope statistics:")
print(f"  Min            : {envelope_int.min()}")
print(f"  Max            : {envelope_int.max()}")
print(f"  Mean           : {envelope_int.mean():.1f}")
print(f"  Range          : {envelope_int.max() - envelope_int.min()} counts")

# Verify no clipping
if envelope_int.min() < -32768 or envelope_int.max() > 32767:
    print("  WARNING: Clipping detected!")
else:
    print("  No clipping (fits in signed 16-bit)")

# ── Select exactly 14,000 samples ───────────────────────────────────────────
# We have ~14,391 samples; pick the center 14,000 to capture the bipolar event
# Global max/min are at relative indices (250157-244647)=5510 and (250164-244647)=5517
MAX_REL = 250157 - WIN_START  # ~5510
MIN_REL = 250164 - WIN_START  # ~5517

N_TARGET = 14000
center   = (MAX_REL + MIN_REL) // 2           # ~5513
half     = N_TARGET // 2                       # 7000
s_start  = max(0, center - half)
s_end    = s_start + N_TARGET
if s_end > n_win:
    s_end   = n_win
    s_start = s_end - N_TARGET

envelope_14k = envelope_int[s_start:s_end]

print(f"\n14,000-sample selection:")
print(f"  Bipolar event center (relative): {center}")
print(f"  Slice                          : [{s_start}, {s_end})")
print(f"  Global max at relative index   : {MAX_REL - s_start} within slice")
print(f"  Global min at relative index   : {MIN_REL - s_start} within slice")
print(f"  Final length                   : {len(envelope_14k)}")
print(f"  Min Q1.15                      : {envelope_14k.min()}")
print(f"  Max Q1.15                      : {envelope_14k.max()}")

# ── Write .mem file ──────────────────────────────────────────────────────────
MEM_PATH = pathlib.Path("FPGA/testbenches/sample_data_envelope.mem")
MEM_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(MEM_PATH, "w") as f:
    for val in envelope_14k:
        # Two's complement unsigned 16-bit hex, 4 digits, no prefix
        unsigned = int(val) & 0xFFFF
        f.write(f"{unsigned:04X}\n")

print(f"\nWrote {len(envelope_14k)} entries to {MEM_PATH}")

# ── Show a snippet around the bipolar event ──────────────────────────────────
ev_center = MAX_REL - s_start
print(f"\nQ1.15 values around bipolar event (index {ev_center-5} to {ev_center+10}):")
for i in range(max(0, ev_center-5), min(len(envelope_14k), ev_center+11)):
    flag = " <-- max" if (i == ev_center) else (" <-- min" if (i == ev_center + (MIN_REL - MAX_REL)) else "")
    print(f"  [{i:5d}] {envelope_14k[i]:6d}  (0x{int(envelope_14k[i]) & 0xFFFF:04X}){flag}")
