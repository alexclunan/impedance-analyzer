"""
Component simulators for impedance analyzer testbench.

Simulates high-speed DAC (16-bit, 250+ MSPS), impedance (real + imaginary),
transimpedance amplifier (op-amp), and ADC (16-bit, 100+ MSPS) with
time- and frequency-domain behavior based on real product specifications.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Tuple, Callable

try:
    from .generators import (
        dac_errors,
        opamp_errors,
        adc_errors,
        apply_phase_delay,
        sine_wave,
        cosine_wave,
    )
except ImportError:
    from generators import (
        dac_errors,
        opamp_errors,
        adc_errors,
        apply_phase_delay,
        sine_wave,
        cosine_wave,
    )


# -----------------------------------------------------------------------------
# DAC Simulator (16-bit+, 250+ MSPS)
# -----------------------------------------------------------------------------
# Based on AD9142A (16-bit 1600 MSPS), AD9122 (16-bit 1230 MSPS) class.
# README: DAC 16-bit+, 250 MSPS+; generates composite waveform (sum of sinusoids).

class DACSimulator:
    """
    High-speed DAC simulator: 16-bit, 250+ MSPS.

    Models time-domain: settling, full-scale output; frequency-domain: SFDR,
    INL/DNL, gain/offset. Output is analog voltage normalized to [0, 1] or
    configurable Vref.
    """

    def __init__(
        self,
        sample_rate_hz: float = 250e6,
        n_bits: int = 16,
        v_ref: float = 1.0,
        inl_lsb: float = 4.0,
        dnl_lsb: float = 0.5,
        gain_error: float = 0.0,
        offset_error: float = 0.0,
        glitch_energy_frac: float = 0.0,
        settling_time_sec: Optional[float] = None,
        seed: Optional[int] = None,
    ):
        self.sample_rate_hz = sample_rate_hz
        self.n_bits = n_bits
        self.v_ref = v_ref
        self.inl_lsb = inl_lsb
        self.dnl_lsb = dnl_lsb
        self.gain_error = gain_error
        self.offset_error = offset_error
        self.glitch_energy_frac = glitch_energy_frac
        self.settling_time_sec = settling_time_sec or (1.0 / sample_rate_hz)
        self._rng = np.random.default_rng(seed)
        self._max_code = (1 << n_bits) - 1

    def digital_to_analog(self, digital_codes: np.ndarray) -> np.ndarray:
        """
        Convert digital codes to analog voltage with DAC nonidealities.

        digital_codes: integer [0, 2^n_bits - 1] or float [0, 1] normalized.
        Returns: analog voltage (same length).
        """
        codes = np.asarray(digital_codes, dtype=float)
        if codes.max() <= 1.0 and codes.min() >= 0.0:
            codes = codes * self._max_code
        codes = np.clip(codes, 0, self._max_code)

        analog = dac_errors(
            codes,
            n_bits=self.n_bits,
            inl_lsb=self.inl_lsb,
            dnl_lsb=self.dnl_lsb,
            gain_error=self.gain_error,
            offset_error=self.offset_error,
            glitch_energy_frac=self.glitch_energy_frac,
            rng=self._rng,
        )
        return analog * self.v_ref

    def run(self, digital_codes: np.ndarray) -> np.ndarray:
        """Alias for digital_to_analog."""
        return self.digital_to_analog(digital_codes)


# -----------------------------------------------------------------------------
# Impedance Simulator (real + imaginary)
# -----------------------------------------------------------------------------
# Models Z(f) = R(f) + j*X(f) for impedance cytometry (e.g. cell in channel).

class ImpedanceSimulator:
    """
    Impedance (real and imaginary) simulator.

    Z(f) = R(f) + j*X(f). Supports parallel R||C, series R-C, or custom
    frequency-dependent R, X. Used to simulate sensor/electrode response.
    """

    def __init__(
        self,
        resistance: float = 1e3,
        capacitance: float = 1e-12,
        inductance: float = 0.0,
        model: str = "parallel_rc",
    ):
        """
        Args:
            resistance: R in ohms.
            capacitance: C in farads.
            inductance: L in henries (optional).
            model: "parallel_rc" (R||C), "series_rc", or "series_rlc".
        """
        self.R = resistance
        self.C = capacitance
        self.L = inductance
        self.model = model

    def z_complex(self, f_hz: np.ndarray) -> np.ndarray:
        """
        Complex impedance Z(f) = R(f) + j*X(f).

        Returns array of shape (f_hz.size,) complex.
        """
        f = np.asarray(f_hz, dtype=float)
        w = 2.0 * np.pi * np.where(np.abs(f) < 1e-30, 1e-30, f)
        if self.model == "parallel_rc":
            # Z = R || (1/(j*w*C)) = R / (1 + j*w*R*C)
            z = self.R / (1.0 + 1j * w * self.R * self.C)
        elif self.model == "series_rc":
            # Z = R + 1/(j*w*C); at DC (f=0) C is open -> R only
            z = np.where(np.abs(f) < 1e-30, self.R + 0j, self.R + 1.0 / (1j * w * self.C))
        elif self.model == "series_rlc":
            # Z = R + j*w*L + 1/(j*w*C); at DC C open, L short
            z = np.where(np.abs(f) < 1e-30, self.R + 0j, self.R + 1j * w * self.L + 1.0 / (1j * w * self.C))
        else:
            z = np.full_like(f, self.R, dtype=complex)
        return z

    def resistance_real(self, f_hz: np.ndarray) -> np.ndarray:
        """Real part of Z(f)."""
        return np.real(self.z_complex(f_hz))

    def reactance_imaginary(self, f_hz: np.ndarray) -> np.ndarray:
        """Imaginary part of Z(f)."""
        return np.imag(self.z_complex(f_hz))

    def magnitude(self, f_hz: np.ndarray) -> np.ndarray:
        """|Z(f)|."""
        return np.abs(self.z_complex(f_hz))

    def phase_rad(self, f_hz: np.ndarray) -> np.ndarray:
        """Phase of Z(f) in radians."""
        return np.angle(self.z_complex(f_hz))

    def current_from_voltage(
        self,
        voltage: np.ndarray,
        t: np.ndarray,
        f_excitation_hz: float,
    ) -> np.ndarray:
        """
        Current through impedance for given voltage waveform (single-tone approx).

        I = V / Z. For multifrequency, use superposition or FFT; here we use
        single-tone Z at f_excitation_hz for simplicity.
        """
        z = self.z_complex(np.array([f_excitation_hz]))[0]
        if np.abs(z) < 1e-18:
            return np.zeros_like(voltage)
        return np.real(voltage / z)


# -----------------------------------------------------------------------------
# Op-amp / Transimpedance Amplifier Simulator
# -----------------------------------------------------------------------------
# README: High Frequency, Low Noise Transimpedance amplifier; TIA converts
# modulated cell current into voltage. Based on high-speed TIAs (e.g. LTC6268,
# ADA4356) with bandwidth 10–50 MHz and low input-referred current noise.

class OpAmpSimulator:
    """
    Transimpedance amplifier (op-amp) simulator.

    Vout = -Iin * Rf (ideal). Models bandwidth (single-pole), gain error,
    offset, and input-referred voltage/current noise. Time- and frequency-domain.
    """

    def __init__(
        self,
        transimpedance_ohms: float = 10e3,
        sample_rate_hz: float = 250e6,
        bandwidth_hz: float = 50e6,
        gain_error: float = 0.0,
        offset_voltage: float = 0.0,
        noise_rms_voltage: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.Rf = transimpedance_ohms
        self.sample_rate_hz = sample_rate_hz
        self.bandwidth_hz = bandwidth_hz
        self.gain_error = gain_error
        self.offset_voltage = offset_voltage
        self.noise_rms_voltage = noise_rms_voltage
        self._rng = np.random.default_rng(seed)

    def run(self, current_in: np.ndarray) -> np.ndarray:
        """
        Convert current to voltage with TIA nonidealities.

        current_in: input current (A). Returns voltage (V).
        """
        ideal_v = -current_in * self.Rf
        return opamp_errors(
            ideal_v,
            sample_rate_hz=self.sample_rate_hz,
            gain_error=self.gain_error,
            offset_voltage=self.offset_voltage,
            bandwidth_hz=self.bandwidth_hz,
            noise_rms=self.noise_rms_voltage,
            rng=self._rng,
        )


# -----------------------------------------------------------------------------
# ADC Simulator (16-bit, 100+ MSPS)
# -----------------------------------------------------------------------------
# README: ADC 16-bit 100 MSPS+; LVDS to PL. Based on 16-bit 100+ MSPS class
# (e.g. AD9680-style specs scaled to 16-bit: INL ±2 LSB, aperture jitter).

class ADCSimulator:
    """
    High-speed ADC simulator: 16-bit, 100+ MSPS.

    Models quantization, INL, DNL, gain/offset, aperture jitter. Output is
    integer codes in [0, 2^n_bits - 1].
    """

    def __init__(
        self,
        sample_rate_hz: float = 100e6,
        n_bits: int = 16,
        v_ref: float = 1.0,
        gain_error: float = 0.0,
        offset_error: float = 0.0,
        inl_lsb: float = 2.0,
        dnl_lsb: float = 0.5,
        aperture_jitter_sec: float = 0.1e-12,
        seed: Optional[int] = None,
    ):
        self.sample_rate_hz = sample_rate_hz
        self.n_bits = n_bits
        self.v_ref = v_ref
        self.gain_error = gain_error
        self.offset_error = offset_error
        self.inl_lsb = inl_lsb
        self.dnl_lsb = dnl_lsb
        self.aperture_jitter_sec = aperture_jitter_sec
        self._rng = np.random.default_rng(seed)

    def analog_to_digital(self, analog_voltage: np.ndarray) -> np.ndarray:
        """
        Convert analog voltage to digital codes with ADC nonidealities.

        analog_voltage: voltage (V). Returns integer codes [0, 2^n_bits - 1].
        """
        return adc_errors(
            analog_voltage,
            n_bits=self.n_bits,
            v_ref=self.v_ref,
            gain_error=self.gain_error,
            offset_error=self.offset_error,
            inl_lsb=self.inl_lsb,
            dnl_lsb=self.dnl_lsb,
            aperture_jitter_sec=self.aperture_jitter_sec,
            sample_rate_hz=self.sample_rate_hz,
            rng=self._rng,
        )

    def run(self, analog_voltage: np.ndarray) -> np.ndarray:
        """Alias for analog_to_digital."""
        return self.analog_to_digital(analog_voltage)
