"""
Extract a short window around the bipolar cell-transit event for fast simulation.
Event peak at slice index 5510 (positive) / 5517 (negative).
Window: 200 samples pre-event, 100 samples post-event = 300 samples total.
At SAMPLE_HOLD_CYCLES = 14286: 300 * 14286 = 4.3 M cycles = 21 ms sim time.
"""
import numpy as np, pathlib

DATA_PATH = pathlib.Path(
    "sample_data/20251106_1MHz_3V_14ksps_500Hz_1kohm_T6_S1/D1/Freq1.ziBin"
)
raw  = np.fromfile(DATA_PATH, dtype=">f8")
n    = len(raw) // 7
data = raw[: n * 7].reshape(n, 7)
x    = data[:, 1]

WIN_START = 244647
fs_est    = n / (data[-1, 0] - data[0, 0])
WIN_END   = min(WIN_START + round(fs_est), n)
x_win     = x[WIN_START:WIN_END]

x_ac  = x_win - np.mean(x_win)
peak  = np.max(np.abs(x_ac))
SCALE = 14746.0 / peak

ENVELOPE_DC = 16384

# Event center (between peak +114 µV at 5510 and trough -113 µV at 5517)
EVENT_CENTER = 5513
PRE  = 200   # samples before event
POST = 100   # samples after event

s_start = EVENT_CENTER - PRE
s_end   = EVENT_CENTER + POST
assert s_start >= 0 and s_end <= len(x_ac), "Window out of range"

x_slice     = x_ac[s_start:s_end]
env_float   = ENVELOPE_DC + x_slice * SCALE
env_int     = np.round(env_float).astype(np.int16)

print(f"Window  : [{s_start}, {s_end})  ({len(env_int)} samples)")
print(f"Event peak at index {EVENT_CENTER - s_start} within window")
print(f"Q1.15 range: {env_int.min()} to {env_int.max()}")
print(f"Sim cycles : {len(env_int)} x 14286 = {len(env_int)*14286:,}  ({len(env_int)*14286*5e-9*1e3:.1f} ms)")

MEM = pathlib.Path("FPGA/testbenches/sample_data_event_only.mem")
with open(MEM, "w") as f:
    for v in env_int:
        f.write(f"{int(v) & 0xFFFF:04X}\n")
print(f"Wrote {len(env_int)} entries -> {MEM}")

# Also print what SAMPLE_DATA_LEN to set in the testbench
print(f"\nIn testbench set:")
print(f"  localparam integer SAMPLE_DATA_LEN    = {len(env_int)};")
print(f"  $readmemh(\"sample_data_event_only.mem\", sample_data);")
