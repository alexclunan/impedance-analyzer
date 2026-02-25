// phase accumulator for DDS (Direct Digital Synthesis)
// Author: Alex Clunan
module phase_accumulator
    // accumulator parameters
    #(parameter ACCUM_WIDTH = 48,
      parameter PHASE_WIDTH = 16)
(
    input                       clock,
    input                       reset_n,
    // frequency control
    input   [ACCUM_WIDTH-1:0]   fcw,
    // phase outputs
    output  [PHASE_WIDTH-1:0]   phase_out,
    output                      phase_msb);

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

assign phase_out = accumulated_phase[ACCUM_WIDTH-1 -: PHASE_WIDTH];
assign phase_msb = accumulated_phase[ACCUM_WIDTH-1];

endmodule
