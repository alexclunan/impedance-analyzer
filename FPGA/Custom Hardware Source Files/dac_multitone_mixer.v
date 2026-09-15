// dac_multitone_mixer.v
// -----------------------------------------------------------------------------
// Sums the four modulator_chain DDS cosine outputs into one multitone DAC
// excitation (Plan 05 Stage C). Each tone is scaled by a per-channel amplitude
// and gated by a per-tone enable, then summed and saturated to the DAC width.
//
// Takes each chain's dds_cos_out[15:0] DIRECTLY (no BD slice/concat), same style
// as demod_frame_combiner. sin outputs are NOT summed — they are the internal
// quadrature LO for demod.
//
// Amplitude (amp_i, from CH*_FA[31:16]) is unsigned Q1.15: 0x8000 = unity gain,
// so a single full-scale tone uses ~0x8000 (firmware AMP_DEFAULT 0x7FFF ~ unity).
// For N simultaneous tones keep sum(amp) well under full scale (or rely on the
// saturate below) — worst case all peaks align, so ~0x2000 each guarantees no
// clip; crest-factor phasing (per-channel POFF) lets you push higher.
//
// Pipeline: multiply -> shift+sum -> saturate (3 cycles), out_valid tracks.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module dac_multitone_mixer #(
    parameter integer W     = 16,   // DDS/DAC sample width (signed)
    parameter integer AMPW  = 16,   // amplitude width (unsigned Q1.15)
    parameter integer FRACT = 15    // amplitude fractional bits (unity = 1<<FRACT)
)(
    input  wire                 clk,        // 200 MHz (clk_out1)
    input  wire                 rst_n,      // dds_srst_n / pipe_srst_n_200

    // per-channel DDS cosine carriers (signed)
    input  wire signed [W-1:0]  cos_0, cos_1, cos_2, cos_3,
    // per-channel amplitude scale (unsigned, CH*_FA[31:16])
    input  wire [AMPW-1:0]      amp_0, amp_1, amp_2, amp_3,
    // per-tone enable (CH_EN2[3:0])
    input  wire [3:0]           tx_enable,
    input  wire                 in_valid,   // dds_valid

    output reg  signed [W-1:0]  dac_out,
    output reg                  out_valid
);
    localparam integer NCH  = 4;
    localparam integer PRODW = W + AMPW + 1;         // signed cos * unsigned amp
    localparam integer SUMW  = W + 4;                // headroom for NCH tones

    wire signed [W-1:0]    cos_in [0:NCH-1];
    wire        [AMPW-1:0] amp_in [0:NCH-1];
    assign cos_in[0] = cos_0; assign cos_in[1] = cos_1;
    assign cos_in[2] = cos_2; assign cos_in[3] = cos_3;
    assign amp_in[0] = amp_0; assign amp_in[1] = amp_1;
    assign amp_in[2] = amp_2; assign amp_in[3] = amp_3;

    // ---- stage 1: scale each enabled tone ----------------------------------
    reg signed [PRODW-1:0] prod [0:NCH-1];
    reg                    v1;
    integer i;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NCH; i = i + 1) prod[i] <= {PRODW{1'b0}};
            v1 <= 1'b0;
        end else begin
            for (i = 0; i < NCH; i = i + 1)
                // Gate the CARRIER, not the product.  The old form
                //   tx_enable ? ($signed*..$signed) : {PRODW{1'b0}}
                // put an UNSIGNED zero branch in the ternary, which makes the
                // whole conditional unsigned and forces Vivado to evaluate the
                // signed multiply in an UNSIGNED context: a negative cos (e.g.
                // 0xFFFF) is read as +65535, so the DAC railed to +full-scale on
                // the negative half.  Selecting the 16-bit carrier first (equal
                // width -> bits preserved) then $signed-casting keeps the
                // multiply a clean top-level signed*signed for negatives too.
                prod[i] <= $signed(tx_enable[i] ? cos_in[i] : {W{1'b0}})
                         * $signed({1'b0, amp_in[i]});
            v1 <= in_valid;
        end
    end

    // ---- stage 2: back to sample scale and sum -----------------------------
    reg signed [SUMW-1:0] sum;
    reg                   v2;
    always @(posedge clk) begin
        if (!rst_n) begin
            sum <= {SUMW{1'b0}};
            v2  <= 1'b0;
        end else begin
            // $signed() is REQUIRED: Vivado does not reliably carry the
            // signedness of an unpacked-array (memory) element through `>>>`,
            // so `prod[i] >>> FRACT` degrades to a LOGICAL shift.  On negative
            // samples that shifts zeros into the top bits, turning a small
            // negative into a large positive that saturates to +32767 -- the
            // "clean positive half, negative half railed to +full-scale"
            // symptom seen on both the ILA and the scope.  Forcing $signed
            // makes the shift arithmetic (sign-extending), as intended.
            sum <= ($signed(prod[0]) >>> FRACT) + ($signed(prod[1]) >>> FRACT)
                 + ($signed(prod[2]) >>> FRACT) + ($signed(prod[3]) >>> FRACT);
            v2  <= v1;
        end
    end

    // ---- stage 3: saturate to W-bit signed ---------------------------------
    localparam signed [SUMW-1:0] MAXP =  (1 <<< (W-1)) - 1;   // +32767
    localparam signed [SUMW-1:0] MINN = -(1 <<< (W-1));       // -32768
    always @(posedge clk) begin
        if (!rst_n) begin
            dac_out   <= {W{1'b0}};
            out_valid <= 1'b0;
        end else begin
            if (sum > MAXP)      dac_out <= MAXP[W-1:0];
            else if (sum < MINN) dac_out <= MINN[W-1:0];
            else                 dac_out <= sum[W-1:0];
            out_valid <= v2;
        end
    end

endmodule
