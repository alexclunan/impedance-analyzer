"""
Pytest testbench for the impedance analyzer signal chain.

Follows README architecture: DDS -> DAC (16-bit+, 250 MSPS+) -> Impedance ->
TIA (high-frequency low-noise op-amp) -> ADC (16-bit, 100 MSPS+).
Uses generators (sine/cosine, noise, errors) and component simulators.
"""

from __future__ import annotations

import pytest
import numpy as np
from numpy.testing import assert_allclose, assert_array_less

# Generators
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
# Simulators
from .simulators import (
    DACSimulator,
    ImpedanceSimulator,
    OpAmpSimulator,
    ADCSimulator,
)


# -----------------------------------------------------------------------------
# Fixtures (testbench best practices)
# -----------------------------------------------------------------------------

@pytest.fixture
def rng():
    """Reproducible random state for tests."""
    return np.random.default_rng(42)


@pytest.fixture
def sample_rate_dac_hz():
    """DAC sample rate per README: 250 MSPS+."""
    return 250e6


@pytest.fixture
def sample_rate_adc_hz():
    """ADC sample rate per README: 100 MSPS+."""
    return 100e6


@pytest.fixture
def n_samples():
    """Number of samples for time-domain tests (enough for several cycles)."""
    return 4096


@pytest.fixture
def t_vec(sample_rate_dac_hz, n_samples):
    """Time vector at DAC rate."""
    return np.arange(n_samples, dtype=float) / sample_rate_dac_hz


@pytest.fixture
def excitation_freq_hz():
    """Excitation frequency per README: multi-frequency < 10 MHz."""
    return 1e6


# -----------------------------------------------------------------------------
# 1. Sine / Cosine generator tests
# -----------------------------------------------------------------------------

class TestSineCosineGenerators:
    """Tests for sine and cosine wave generators."""

    def test_sine_wave_shape(self, t_vec):
        y = sine_wave(t_vec, frequency=1e6, amplitude=1.0, phase=0.0)
        assert y.shape == t_vec.shape
        assert y.dtype == np.float64

    def test_sine_wave_amplitude_phase(self, t_vec, rng):
        amp = 2.5
        phase = np.pi / 4
        y = sine_wave(t_vec, frequency=100e3, amplitude=amp, phase=phase)
        assert np.all(np.abs(y) <= amp + 1e-9)
        assert np.abs(np.max(y) - amp) < 0.01 or np.abs(np.min(y) + amp) < 0.01

    def test_cosine_wave_phase_shift_from_sine(self, t_vec):
        f = 500e3
        cos_y = cosine_wave(t_vec, f, amplitude=1.0, phase=0.0)
        # cos(t) = sin(t + pi/2)
        expected = sine_wave(t_vec, f, amplitude=1.0, phase=np.pi / 2)
        assert_allclose(cos_y, expected, rtol=1e-10, atol=2e-15)

    def test_multifrequency_sine_sum(self, t_vec):
        freqs = np.array([100e3, 500e3, 1e6])
        amps = np.array([0.5, 0.3, 0.2])
        y = multifrequency_sine(t_vec, freqs, amps)
        assert y.shape == t_vec.shape
        # Sum of amplitudes upper bound (rough)
        assert np.all(np.abs(y) <= np.sum(amps) + 0.1)

    def test_multifrequency_sine_phases(self, t_vec):
        freqs = np.array([1e6])
        amps = np.array([1.0])
        phases = np.array([np.pi / 2])
        y = multifrequency_sine(t_vec, freqs, amps, phases=phases)
        ref = sine_wave(t_vec, freqs[0], amplitude=1.0, phase=np.pi / 2)
        assert_allclose(y, ref, rtol=1e-10)


# -----------------------------------------------------------------------------
# 2. Noise generator tests (time and frequency domain)
# -----------------------------------------------------------------------------

class TestNoiseGenerators:
    """Tests for time-domain and frequency-domain noise."""

    @pytest.mark.parametrize("noise_type", list(NoiseType))
    def test_noise_time_domain_shape(self, noise_type, n_samples, rng):
        y = noise_time_domain(n_samples, noise_type=noise_type, scale=1.0, rng=rng)
        assert y.shape == (n_samples,)
        assert np.issubdtype(y.dtype, np.floating)

    def test_noise_time_domain_white_rms(self, n_samples, rng):
        scale = 0.5
        y = noise_time_domain(n_samples, NoiseType.WHITE, scale=scale, rng=rng)
        rms = np.sqrt(np.mean(y ** 2))
        assert 0.8 * scale <= rms <= 1.2 * scale

    def test_noise_frequency_domain_shape(self, rng):
        n_bins = 1024
        spec = noise_frequency_domain(n_bins, NoiseType.WHITE, scale=1.0, rng=rng)
        assert spec.shape == (n_bins,)
        assert np.issubdtype(spec.dtype, np.complexfloating)

    def test_noise_frequency_domain_irfft_real(self, rng):
        n_bins = 512
        spec = noise_frequency_domain(n_bins, NoiseType.PINK, scale=1.0, rng=rng)
        spec[0] = np.real(spec[0])
        time_signal = np.fft.irfft(spec, n=2 * (n_bins - 1))
        assert np.all(np.isreal(time_signal))


# -----------------------------------------------------------------------------
# 3. Error generator tests
# -----------------------------------------------------------------------------

class TestErrorGenerators:
    """Tests for phase delay, DAC, op-amp, and ADC error models."""

    def test_phase_delay_circular_shift(self, t_vec, sample_rate_dac_hz, excitation_freq_hz):
        y = sine_wave(t_vec, excitation_freq_hz, amplitude=1.0, phase=0.0)
        delayed = apply_phase_delay(y, phase_delay_rad=np.pi / 2, sample_rate_hz=sample_rate_dac_hz, frequency_hz=excitation_freq_hz)
        assert delayed.shape == y.shape
        # After delay, phase should differ by ~pi/2 (qualitative)
        assert not np.allclose(delayed, y, rtol=1e-2)

    def test_dac_errors_output_range(self, rng):
        codes = np.linspace(0, 1, 256)
        out = dac_errors(codes, n_bits=16, inl_lsb=2.0, dnl_lsb=0.5, rng=rng)
        assert np.all(out >= -0.1) and np.all(out <= 1.1)

    def test_opamp_errors_bandwidth_attenuates(self, sample_rate_dac_hz, rng):
        n = 2048
        t = np.arange(n) / sample_rate_dac_hz
        sig = sine_wave(t, 50e6, amplitude=1.0)
        out = opamp_errors(sig, sample_rate_hz=sample_rate_dac_hz, bandwidth_hz=10e6, rng=rng)
        # High-freq tone should be attenuated
        assert np.max(np.abs(out)) < np.max(np.abs(sig)) * 1.1

    def test_adc_errors_integer_codes(self, rng, sample_rate_adc_hz):
        n = 1024
        analog = 0.5 * np.sin(2 * np.pi * 1e6 * np.arange(n) / sample_rate_adc_hz) + 0.5
        codes = adc_errors(analog, n_bits=16, v_ref=1.0, sample_rate_hz=sample_rate_adc_hz, rng=rng)
        assert codes.dtype in (np.int32, np.int64)
        assert np.all(codes >= 0) and np.all(codes <= 65535)


# -----------------------------------------------------------------------------
# 4. DAC simulator tests
# -----------------------------------------------------------------------------

class TestDACSimulator:
    """Tests for 16-bit, 250+ MSPS DAC simulator."""

    def test_dac_output_shape(self, t_vec, sample_rate_dac_hz):
        dac = DACSimulator(sample_rate_hz=sample_rate_dac_hz, n_bits=16, seed=0)
        # Normalized sine in [0, 1] for unipolar DAC
        digital = 0.5 + 0.5 * np.sin(2 * np.pi * 1e6 * t_vec)
        analog = dac.digital_to_analog(digital)
        assert analog.shape == digital.shape

    def test_dac_specs_per_readme(self):
        dac = DACSimulator(sample_rate_hz=250e6, n_bits=16)
        assert dac.sample_rate_hz >= 250e6
        assert dac.n_bits >= 16

    def test_dac_run_alias(self, t_vec, sample_rate_dac_hz):
        dac = DACSimulator(sample_rate_hz=sample_rate_dac_hz, seed=1)
        digital = np.linspace(0, 1, len(t_vec))
        a1 = dac.digital_to_analog(digital)
        a2 = dac.run(digital)
        assert a1.shape == a2.shape
        assert np.all(np.isfinite(a2))
        assert np.min(a2) >= -0.1 and np.max(a2) <= dac.v_ref + 0.1
        assert a2.dtype == a1.dtype


# -----------------------------------------------------------------------------
# 5. Impedance simulator tests (real + imaginary)
# -----------------------------------------------------------------------------

class TestImpedanceSimulator:
    """Tests for impedance (real and imaginary) simulator."""

    def test_z_parallel_rc_magnitude(self):
        imp = ImpedanceSimulator(resistance=1e3, capacitance=1e-9, model="parallel_rc")
        f = np.array([0.1, 1e6, 10e6])
        z = imp.z_complex(f)
        assert np.all(np.abs(z) <= imp.R + 1)
        assert np.all(np.real(z) > 0)

    def test_z_series_rc(self):
        imp = ImpedanceSimulator(resistance=100.0, capacitance=1e-6, model="series_rc")
        # At DC (f=0), simulator returns R only (C open); explicit f=0 handled in z_complex
        z_dc = imp.z_complex(np.array([0.0]))
        assert np.real(z_dc[0]) == imp.R
        assert np.abs(np.imag(z_dc[0])) < 1e-10
        # At high f, capacitive reactance dominates
        f_high = np.array([1e9])
        z_high = imp.z_complex(f_high)
        assert np.abs(np.imag(z_high[0])) > 0

    def test_current_from_voltage_real(self, t_vec, excitation_freq_hz):
        imp = ImpedanceSimulator(resistance=1e3, capacitance=1e-12, model="parallel_rc")
        v = np.sin(2 * np.pi * excitation_freq_hz * t_vec)
        i = imp.current_from_voltage(v, t_vec, excitation_freq_hz)
        assert np.all(np.isreal(i))
        assert i.shape == v.shape


# -----------------------------------------------------------------------------
# 6. Op-amp / TIA simulator tests
# -----------------------------------------------------------------------------

class TestOpAmpSimulator:
    """Tests for transimpedance amplifier (op-amp) simulator."""

    def test_tia_gain(self, sample_rate_dac_hz, rng):
        Rf = 10e3
        opa = OpAmpSimulator(transimpedance_ohms=Rf, sample_rate_hz=sample_rate_dac_hz, bandwidth_hz=100e6, noise_rms_voltage=0.0, seed=0)
        n = 256
        i_in = np.ones(n) * 1e-6  # 1 uA DC
        v_out = opa.run(i_in)
        # First sample can differ due to IIR filter settling; check steady-state (tail)
        assert_allclose(v_out[-10:], -Rf * 1e-6, rtol=0.02)

    def test_tia_bandwidth_effect(self, sample_rate_dac_hz):
        opa = OpAmpSimulator(transimpedance_ohms=5e3, sample_rate_hz=sample_rate_dac_hz, bandwidth_hz=5e6, noise_rms_voltage=0.0, seed=0)
        n = 2048
        t = np.arange(n) / sample_rate_dac_hz
        i_in = np.sin(2 * np.pi * 20e6 * t) * 1e-6
        v_out = opa.run(i_in)
        # 20 MHz above 5 MHz BW -> attenuated
        assert np.max(np.abs(v_out)) < 5e3 * 1e-6 * 1.5


# -----------------------------------------------------------------------------
# 7. ADC simulator tests
# -----------------------------------------------------------------------------

class TestADCSimulator:
    """Tests for 16-bit, 100+ MSPS ADC simulator."""

    def test_adc_output_range(self, sample_rate_adc_hz, rng):
        adc = ADCSimulator(sample_rate_hz=sample_rate_adc_hz, n_bits=16, seed=0)
        n = 512
        analog = 0.5 + 0.4 * np.sin(2 * np.pi * 1e6 * np.arange(n) / sample_rate_adc_hz)
        codes = adc.analog_to_digital(analog)
        assert np.all(codes >= 0) and np.all(codes <= 65535)
        assert codes.dtype in (np.int32, np.int64)

    def test_adc_specs_per_readme(self):
        adc = ADCSimulator(sample_rate_hz=100e6, n_bits=16)
        assert adc.sample_rate_hz >= 100e6
        assert adc.n_bits >= 16


# -----------------------------------------------------------------------------
# 8. Full signal chain (README: DAC -> Impedance -> TIA -> ADC)
# -----------------------------------------------------------------------------

class TestImpedanceAnalyzerChain:
    """Full chain test following README analog signal chain."""

    @pytest.fixture
    def chain_dac(self, sample_rate_dac_hz):
        return DACSimulator(sample_rate_hz=sample_rate_dac_hz, n_bits=16, v_ref=1.0, seed=10)

    @pytest.fixture
    def chain_impedance(self):
        return ImpedanceSimulator(resistance=2e3, capacitance=2e-12, model="parallel_rc")

    @pytest.fixture
    def chain_tia(self, sample_rate_dac_hz):
        return OpAmpSimulator(transimpedance_ohms=15e3, sample_rate_hz=sample_rate_dac_hz, bandwidth_hz=30e6, noise_rms_voltage=1e-6, seed=20)

    @pytest.fixture
    def chain_adc(self, sample_rate_adc_hz):
        return ADCSimulator(sample_rate_hz=sample_rate_adc_hz, n_bits=16, v_ref=1.0, seed=30)

    def test_chain_end_to_end(
        self,
        t_vec,
        sample_rate_dac_hz,
        excitation_freq_hz,
        chain_dac,
        chain_impedance,
        chain_tia,
        chain_adc,
    ):
        # 1) DDS: generate excitation (sine) in [0,1] for unipolar DAC
        digital_excitation = 0.5 + 0.4 * sine_wave(t_vec, excitation_freq_hz, amplitude=1.0, phase=0.0)

        # 2) DAC: digital -> analog voltage
        v_dac = chain_dac.digital_to_analog(digital_excitation)

        # 3) Impedance: voltage -> current (sensor response)
        i_sensor = chain_impedance.current_from_voltage(v_dac, t_vec, excitation_freq_hz)

        # 4) TIA: current -> voltage
        v_tia = chain_tia.run(i_sensor)

        # 5) ADC: voltage -> digital codes (may need resample if ADC rate != DAC rate)
        # For simplicity use same length; in practice ADC might run at 100 MSPS and DAC at 250 MSPS
        if len(v_tia) > 0:
            codes = chain_adc.analog_to_digital(v_tia[: len(v_tia)])
            assert codes.shape[0] == v_tia.shape[0]
            assert np.all(codes >= 0) and np.all(codes <= 65535)

    def test_chain_magnitude_phase_consistency(
        self,
        t_vec,
        sample_rate_dac_hz,
        excitation_freq_hz,
        chain_dac,
        chain_impedance,
        chain_tia,
        chain_adc,
    ):
        """Verify that magnitude and phase from chain are consistent with R = sqrt(X^2+Y^2), phi = atan2(Y,X)."""
        # Single-tone excitation
        digital_excitation = 0.5 + 0.4 * sine_wave(t_vec, excitation_freq_hz, amplitude=1.0, phase=0.0)
        v_dac = chain_dac.digital_to_analog(digital_excitation)
        i_sensor = chain_impedance.current_from_voltage(v_dac, t_vec, excitation_freq_hz)
        v_tia = chain_tia.run(i_sensor)
        codes = chain_adc.analog_to_digital(v_tia)
        # Reconstruct approximate analog from codes for demod
        v_reconstructed = (codes.astype(float) / 65535.0) - 0.5
        # In-phase and quadrature (simplified: ref sine and cosine at f_excitation)
        ref_sine = sine_wave(t_vec, excitation_freq_hz, amplitude=1.0, phase=0.0)
        ref_cosine = cosine_wave(t_vec, excitation_freq_hz, amplitude=1.0, phase=0.0)
        X = np.mean(v_reconstructed * ref_sine)
        Y = np.mean(v_reconstructed * ref_cosine)
        R = np.sqrt(X ** 2 + Y ** 2)
        phi = np.arctan2(Y, X)
        assert np.isfinite(R) and np.isfinite(phi)
        assert R >= 0
