% 1. Define Filter System Parameters
Fs_in = 200e6;    % 200 MHz input from FPGA
Fs_out = 100e3;   % 100 kHz output after CIC
R = 2000;         % Decimation factor (200MHz / 100kHz)
M = 1;            % CIC differential delay
N = 4;            % CIC number of stages

% FIR Target Specs
Fpass = 10e3;     % 10 kHz passband edge for cell sorting pulse
Fstop = 15e3;     % 15 kHz stopband edge
Apass = 0.1;      % 0.1 dB tight passband ripple
Astop = 80;       % 80 dB stopband attenuation

% CIC bit growth info
cic_gain = (R*M)^N;
cic_gain_dB = 20*log10(cic_gain);
cic_bit_growth = N * ceil(log2(R*M));
fprintf('CIC raw DC gain: %.2e (%.1f dB)\n', cic_gain, cic_gain_dB);
fprintf('CIC bit growth:  %d bits (32-bit input -> %d-bit full precision)\n', ...
        cic_bit_growth, 32 + cic_bit_growth);

% 2. Create the CIC Decimator System Object (for fvtool only)
cic_filter = dsp.CICDecimator(R, M, N);

% 3. Design the FIR Inverse Sinc Compensator
% Surrogate R avoids floating-point underflow in ciccomp.
% Valid because passband droop = sinc(M*f/Fs_out)^N, independent of R.
R_surrogate = 64;
comp_spec = fdesign.ciccomp(R_surrogate, ...
                            cic_filter.DifferentialDelay, ...
                            cic_filter.NumSections, ...
                            Fpass, Fstop, Apass, Astop, Fs_out);

% Design as dfilt for reliable coefficient extraction
fir_dfilt = design(comp_spec, 'equiripple');
b_fir = fir_dfilt.Numerator;
fprintf('FIR compensator: %d taps\n', length(b_fir));

% Also create system object version for fvtool
fir_sysobj = design(comp_spec, 'equiripple', 'SystemObject', true);
cascaded_pipeline = cascade(cic_filter, fir_sysobj);

% =====================================================================
% 4. Compute frequency responses on a common axis (0 to Fs_out/2)
%    Both CIC droop and FIR operate in this band after decimation
% =====================================================================
Nfft = 4096;

% FIR response: freqz with scalar N gives N evenly-spaced points 0..Fs/2
[H_fir, f_axis] = freqz(b_fir, 1, Nfft, Fs_out);
H_fir_dB = 20*log10(abs(H_fir / H_fir(1)));

% CIC passband droop: analytical sinc^N formula (exact for f << Fs_in)
H_cic_droop = sinc(M * f_axis / Fs_out).^N;
H_cic_dB = 20*log10(abs(H_cic_droop));

% Cascaded: multiply (add in dB)
H_cas_dB = H_cic_dB + H_fir_dB;

% Diagnostic printout
fprintf('\nAt Fpass = %.0f kHz:\n', Fpass/1e3);
fprintf('  CIC droop:  %.3f dB\n', interp1(f_axis, H_cic_dB, Fpass));
fprintf('  FIR gain:   %.3f dB\n', interp1(f_axis, H_fir_dB, Fpass));
fprintf('  Combined:   %.3f dB\n', interp1(f_axis, H_cas_dB, Fpass));

% =====================================================================
% 5. Plot: two subplots (passband zoom + full range)
% =====================================================================
fig1 = figure('Color', 'white', 'Name', 'Filter Analysis');

% Top: passband compensation detail
ax_top = subplot(2, 1, 1, 'Parent', fig1, 'Box', 'on', 'XGrid', 'on', 'YGrid', 'on');
hold(ax_top, 'on');
h1 = plot(ax_top, f_axis/1e3, H_cic_dB, 'Color', [0 0.447 0.741], 'LineWidth', 1.5);
h2 = plot(ax_top, f_axis/1e3, H_fir_dB, 'Color', [0.635 0.078 0.184], 'LineWidth', 1.5);
h3 = plot(ax_top, f_axis/1e3, H_cas_dB, 'Color', [0.929 0.694 0.125], 'LineWidth', 2);
xline(ax_top, Fpass/1e3, '--k', 'Fpass', 'LabelVerticalAlignment', 'top', 'HandleVisibility', 'off');
hold(ax_top, 'off');
xlabel(ax_top, 'Frequency (kHz)');
ylabel(ax_top, 'Magnitude (dB)');
title(ax_top, 'Passband Compensation Detail');
legend(ax_top, [h1 h2 h3], 'CIC Droop', 'FIR Compensator', 'Cascaded (Flat)', ...
       'Location', 'southwest');
xlim(ax_top, [0 12]);
ylim(ax_top, [-0.5 0.5]);

% Bottom: full response showing stopband rejection
ax_bot = subplot(2, 1, 2, 'Parent', fig1, 'Box', 'on', 'XGrid', 'on', 'YGrid', 'on');
hold(ax_bot, 'on');
plot(ax_bot, f_axis/1e3, H_cic_dB, 'Color', [0 0.447 0.741], 'LineWidth', 1.5);
plot(ax_bot, f_axis/1e3, H_fir_dB, 'Color', [0.635 0.078 0.184], 'LineWidth', 1.5);
plot(ax_bot, f_axis/1e3, H_cas_dB, 'Color', [0.929 0.694 0.125], 'LineWidth', 1.5);
xline(ax_bot, Fpass/1e3, '--k', 'Fpass', 'HandleVisibility', 'off');
xline(ax_bot, Fstop/1e3, '--k', 'Fstop', 'HandleVisibility', 'off');
hold(ax_bot, 'off');
xlabel(ax_bot, 'Frequency (kHz)');
ylabel(ax_bot, 'Magnitude (dB)');
title(ax_bot, 'Full Response (0 - 50 kHz)');
xlim(ax_bot, [0 50]);
ylim(ax_bot, [-100 5]);

% =====================================================================
% 6. Wideband CIC response (normalized, input-rate view)
% =====================================================================
[H_cic_wide, f_wide] = freqz(cic_filter, Nfft, Fs_in);
H_cic_wide_dB = 20*log10(abs(H_cic_wide / H_cic_wide(1)));

fig2 = figure('Color', 'white', 'Name', 'Wideband CIC Response (Normalized)');
ax2 = axes(fig2, 'Color', 'white', 'Box', 'on', 'XGrid', 'on', 'YGrid', 'on');
plot(ax2, f_wide/1e6, H_cic_wide_dB, 'Color', [0 0.447 0.741], 'LineWidth', 1.5);
xlabel(ax2, 'Frequency (MHz)');
ylabel(ax2, 'Magnitude (dB)');
title(ax2, 'CIC Decimator Wideband Response (Normalized to 0 dB at DC)');
ylim(ax2, [-120 5]);

% =====================================================================
% 7. Raw fvtool for reference (shows absolute gain)
% =====================================================================
hfvt = fvtool(cic_filter, fir_sysobj, cascaded_pipeline, ...
              'Fs', [Fs_in, Fs_out, Fs_in]);
legend(hfvt, 'CIC Decimator (raw gain)', ...
             'FIR Compensator', ...
             'Cascaded (raw gain)');
hfvt.Color = 'white';

fprintf('\nNote: fvtool shows ~%.0f dB raw CIC gain = (R*M)^N = %d^%d.\n', ...
        cic_gain_dB, R*M, N);
fprintf('Xilinx CIC IP absorbs this as %d bits of internal growth.\n', cic_bit_growth);
