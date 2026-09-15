// demod_frame_combiner.v
// -----------------------------------------------------------------------------
// 200 MHz front-end for the reconfigurable packetizer (Plan 05 Stage B).
//
// Takes the four modulator_chain instances' r_phase_out AXIS buses DIRECTLY and
// packs them, the raw-ADC monitor, and the OR flags into one coherent wide frame
// per demod-output instant, for the CDC FIFO (axis_data_fifo, 200->100).
//
// modulator_chain r_phase_out_tdata[63:0] is the CORDIC polar output:
//   [31:0]  = magnitude (fix32_30, signed)
//   [63:32] = phase     (fix32_29, signed)
// which is exactly one packetizer channel slot {phase, sig}, so each 64-bit bus
// maps 1:1 into the frame -- no slicing/concat needed in the block design.
//
// Frame layout (ch0 in the LSBs), byte-aligned for the AXIS FIFO,
// FRAME_W = NCH*64 + 32 = 288 b (36 B):
//   { status[31:0], r_phase_out_3, r_phase_out_2, r_phase_out_1, r_phase_out_0 }
//   status = { OR[1:0], 14'b0, adc[15:0] }
//
// Unused channel inputs (fewer chains instantiated) tie to 0 and are dropped
// downstream by the packetizer's channel_mask. `valid` is the common demod-
// output strobe (wire any enabled chain's r_phase_out_tvalid -- they coincide);
// if the chains ever diverge in latency, latch each on its own valid here.
//
// Rate ~200 kHz into a depth-16 FIFO, so it never backs up; a dropped frame
// (FIFO full) raises `overflow` for telemetry rather than stalling the datapath.
// ------------------------------------------------------------------------------

`timescale 1ns / 1ps

module demod_frame_combiner #(
    parameter integer ADCW    = 16,
    parameter integer FRAME_W = 4*64 + 32       // 288 b = 36 B
)(
    input  wire                 clk,       // 200 MHz (clk_out1)
    input  wire                 rst_n,     // pipe_srst_n_200

    // modulator_chain r_phase_out buses (each {phase[63:32], mag[31:0]})
    input  wire [63:0]          r_phase_out_0,
    input  wire [63:0]          r_phase_out_1,
    input  wire [63:0]          r_phase_out_2,
    input  wire [63:0]          r_phase_out_3,
    input  wire                 valid,     // common r_phase_out_tvalid strobe

    // raw-ADC monitor + over-range flags, sampled with the frame
    input  wire [ADCW-1:0]      adc,
    input  wire [1:0]           or_flags,

    // AXIS frame out to the CDC FIFO
    output reg  [FRAME_W-1:0]   frame_tdata,
    output reg                  frame_tvalid,
    input  wire                 frame_tready,

    output reg                  overflow   // frame dropped because FIFO was full
);
    // 32-bit status word: { OR[1:0], 14'b0, adc[15:0] }  (ADCW is 16 here)
    wire [31:0] status_word = { or_flags, 14'b0, adc };

    // pack the four 64-bit polar buses + the status word
    wire [FRAME_W-1:0] frame_next = { status_word,
                                      r_phase_out_3, r_phase_out_2,
                                      r_phase_out_1, r_phase_out_0 };

    // Capture ONE frame per demod output on the RISING EDGE of valid. The
    // r_phase_out_tvalid strobe stays high for several cycles per sample; using
    // it as a level pushed a frame every cycle (the real sample followed by
    // zeros/duplicates -> ~6x record rate, 91% zero, bimodal timestamps).
    reg valid_d;
    wire valid_rise = valid & ~valid_d;

    always @(posedge clk) begin
        if (!rst_n) begin
            frame_tdata  <= {FRAME_W{1'b0}};
            frame_tvalid <= 1'b0;
            overflow     <= 1'b0;
            valid_d      <= 1'b0;
        end else begin
            valid_d <= valid;

            if (frame_tvalid && frame_tready)
                frame_tvalid <= 1'b0;      // FIFO took the frame

            if (valid_rise) begin
                if (frame_tvalid && !frame_tready) begin
                    overflow <= 1'b1;      // previous frame not yet taken -> drop
                end else begin
                    frame_tdata  <= frame_next;
                    frame_tvalid <= 1'b1;
                end
            end
        end
    end

endmodule
