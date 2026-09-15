// phase accumulator for DDS (Direct Digital Synthesis)
// Author: Alex Clunan
//
// phase_out is scaled for the Xilinx CORDIC (dac_sin_cos) running in
// SCALED RADIANS mode. That CORDIC's phase input is fix16_13 (3 integer bits)
// and is only valid over [-1,+1) == [-pi,+pi). A raw accumulator ramp uses the
// full 16-bit scale for one turn -- a fix16_15 quantity in [-1,1) -- which the
// CORDIC would read as +/-4 and drive out of its +/-1 valid range for most of
// the turn (the "skipped"/mid-sine glitch). Converting fix16_15 -> fix16_13 is
// an arithmetic right shift by 2 (the 2 surplus integer bits): sign-extend the
// top (PHASE_WIDTH-2) phase bits by 2. One full turn then maps to [-1,+1), wraps
// cleanly at +/-pi, and never leaves the valid range.
// NOTE: the ADC-side mixer CORDIC (fed by phase_accumulator_slave) needs the
// same scaling if it is also configured for scaled radians.
module phase_accumulator
    // accumulator parameters
    #(parameter ACCUM_WIDTH = 48,
      parameter PHASE_WIDTH = 16)   // must match the CORDIC phase width (fix16_13)
(
    input                       clock,
    input                       reset_n,
    // frequency control
    input   [ACCUM_WIDTH-1:0]   fcw,
    // phase outputs
    output  [PHASE_WIDTH-1:0]   phase_out,   // scaled radians, ready for the CORDIC
    output                      phase_msb,
    output                      data_valid);

// accumulator register
reg [ACCUM_WIDTH-1:0] accumulated_phase;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        accumulated_phase <= {ACCUM_WIDTH{1'b0}};

    // accumulate phase
    end else begin
        accumulated_phase <= accumulated_phase + fcw;
    end
end

// Scaled-radians phase for the CORDIC: take the top (PHASE_WIDTH-2) phase bits
// and sign-extend by 2 (fix16_15 -> fix16_13). This is equivalent to
// $signed(accumulated_phase[MSB -: PHASE_WIDTH]) >>> 2, i.e. a divide-by-4 that
// keeps one full turn inside [-1,+1) with a clean 2's-complement wrap at +/-pi.
assign phase_out = { {2{accumulated_phase[ACCUM_WIDTH-1]}},
                     accumulated_phase[ACCUM_WIDTH-1 -: (PHASE_WIDTH-2)] };

assign phase_msb  = accumulated_phase[ACCUM_WIDTH-1];
assign data_valid = reset_n;

endmodule
