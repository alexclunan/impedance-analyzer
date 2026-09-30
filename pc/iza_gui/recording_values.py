"""Qt-free demod scaling (shared with the live stream) and recording validity flags."""

import numpy as np

MAG_SCALE = float(1 << 30)
PHASE_SCALE = float(1 << 29)

# One validity byte per recorded row; zero means valid. Flags may be combined.
INVALID_INPUT = 2   # nonfinite input or negative magnitude
OVER_RANGE = 4      # ADC over-range


def scale_mag(sig):
    return np.asarray(sig, dtype=np.float64) / MAG_SCALE


def scale_phase_rad(phase):
    return np.asarray(phase, dtype=np.float64) / PHASE_SCALE


def admittance_values(sig, phase, over_range):
    """Return relative differential admittance x/y and uint8 validity flags.

    x/y keep the original scaling (mag*cos(phi), mag*sin(phi)). Flagged rows
    are still recorded unchanged; the flags only mark them. Never clamp or
    substitute a previous sample.
    """
    mag = scale_mag(sig)
    phi = scale_phase_rad(phase)
    flags = np.zeros(mag.shape, dtype=np.uint8)
    finite = np.isfinite(mag) & np.isfinite(phi)
    flags[~finite | (mag < 0)] |= INVALID_INPUT
    flags[np.asarray(over_range) != 0] |= OVER_RANGE
    phi = np.where(np.isfinite(phi), phi, np.nan)
    mag = np.where(np.isfinite(mag), mag, np.nan)
    return mag * np.cos(phi), mag * np.sin(phi), flags
