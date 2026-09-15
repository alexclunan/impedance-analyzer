module am_modulator #(
    parameter MOD_INDEX_256 = 128  // modulation index m = 128/256 = 0.5
)(
    input  wire        clk,

    // Message signal from sample_hold (signed 16-bit)
    input  wire signed [15:0] message,

    // Carrier from the rasterized DDS Compiler (Amplitude_Mode = Full_Range):
    // fix16_15 signed, i.e. unity = +/-32767 — NOT the old CORDIC fix16_14.
    // TDATA: IMAG[31:16]=sine, REAL[15:0]=cosine
    input  wire [15:0] cos_in,

    // AM output (signed 16-bit)
    output reg  signed [15:0] am_out
);
    // -------------------------------------------------------------------------
    // 3-stage pipeline (was fully combinational -> failed timing at 200 MHz):
    //   S1  envelope = 1 + m*x(t)      (const-mult is shifts + one add)
    //   S2  envelope * carrier          (isolated so it packs into a DSP48 with
    //                                    input+output pipeline registers)
    //   S3  round half-up + take Q1.14  (32-bit add + slice)
    // cos_carrier is delayed to line up with the envelope. Latency is now 3
    // cycles; a constant excitation-path delay is a fixed phase offset the
    // demod calibration absorbs. No reset (self-flushing; matches the BD port).
    // -------------------------------------------------------------------------

    wire signed [15:0] cos_carrier = cos_in[15:0];

    // ---- stage 1: envelope = 1 + m*x(t), Q1.14 -----------------------------
    // message * constant -> the tool implements this as shift/adds, not a DSP.
    wire signed [23:0] mod_product = message * $signed(MOD_INDEX_256);
    // A part-select is ALWAYS unsigned in Verilog, so a bare
    // "mod_product[23:8] >>> 1" degrades to a LOGICAL shift and clears the
    // sign bit for negative messages (envelope then wraps negative and the
    // demod sees 180° phase flips every message half-cycle).  $signed()
    // restores the arithmetic shift.  Same trap as dac_multitone_mixer.
    wire signed [15:0] mod_q14     = $signed(mod_product[23:8]) >>> 1;  // Q1.15 -> Q1.14

    reg signed [15:0] envelope_r = 16'sd0;
    reg signed [15:0] cos_r      = 16'sd0;
    always @(posedge clk) begin
        envelope_r <= $signed(16'sd16384) + mod_q14;   // 1.0 in Q1.14 = 16384
        cos_r      <= cos_carrier;                      // align with envelope
    end

    // ---- stage 2: envelope * carrier (DSP48, registered in and out) --------
    // envelope fix16_14 * carrier fix16_15 = fix32_29.
    reg signed [31:0] am_product_r = 32'sd0;
    always @(posedge clk)
        am_product_r <= envelope_r * cos_r;

    // ---- stage 3: round half-up, take [30:15] for Q1.14 --------------------
    // The slice divides by 2^15 because the DDS carrier is FULL-RANGE fix16_15
    // (unity = 32767).  The old [29:14] slice assumed a fix16_14 carrier: with
    // the full-range DDS it put unit envelope EXACTLY at the int16 boundary,
    // so any envelope > 1.0 wrapped the waveform's sign at the carrier peaks —
    // the demod then faithfully reported the fundamental of that wrapped
    // waveform (mag collapsing + 180-degree phase flips above env = 1.0).
    // Output is fix16_14: env 1.0 -> +/-16384, headroom to env < 2.0.
    // Round (add 2^14) instead of truncating: plain truncation biases every
    // sample by -1 LSB, a constant DC offset that re-modulates onto the carrier
    // and appears as a spur at the carrier frequency in the demod output.
    wire signed [31:0] am_rounded = am_product_r + 32'sd16384;
    always @(posedge clk)
        am_out <= am_rounded[30:15];

endmodule
