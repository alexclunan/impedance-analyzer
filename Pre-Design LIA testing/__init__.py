"""
Impedance analyzer testbench.

Provides signal/noise/error generators and component simulators (DAC,
impedance, op-amp, ADC) for testing the FPGA-based multi-frequency
impedance analyzer per README specifications.
"""

from .generators import (
    sine_wave,
    cosine_wave,
    multifrequency_sine,
    noise_time_domain,
    noise_frequency_domain,
    NoiseType,
    apply_phase_delay,
    dac_errors,
    opamp_errors,
    adc_errors,
)
from .simulators import (
    DACSimulator,
    ImpedanceSimulator,
    OpAmpSimulator,
    ADCSimulator,
)

__all__ = [
    "sine_wave",
    "cosine_wave",
    "multifrequency_sine",
    "noise_time_domain",
    "noise_frequency_domain",
    "NoiseType",
    "apply_phase_delay",
    "dac_errors",
    "opamp_errors",
    "adc_errors",
    "DACSimulator",
    "ImpedanceSimulator",
    "OpAmpSimulator",
    "ADCSimulator",
]
