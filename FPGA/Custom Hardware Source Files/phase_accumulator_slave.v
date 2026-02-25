// slave phase accumulator for ADC clock domain
// tracks master via signed correction from phase synchronizer
// Author: Alex Clunan
module phase_accumulator_slave
    // accumulator parameters
    #(parameter ACCUM_WIDTH = 48,
      parameter PHASE_WIDTH = 16)
(
    input                       clock,
    input                       reset_n,
    // frequency control
    input   [ACCUM_WIDTH-1:0]   fcw,
    // correction from phase synchronizer: 2'b01 = +1, 2'b00 = 0, 2'b11 = -1
    input   [1:0]               correction,
    // phase outputs
    output  [PHASE_WIDTH-1:0]   phase_out,
    output                      phase_msb);

// accumulator register
reg [ACCUM_WIDTH-1:0] accumulated_phase;

// sign-extend 2-bit correction to accumulator width
wire [ACCUM_WIDTH-1:0] correction_ext = {{(ACCUM_WIDTH-2){correction[1]}}, correction};

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        accumulated_phase <= {ACCUM_WIDTH{1'b0}};

    // accumulate phase with correction
    end else begin
        accumulated_phase <= accumulated_phase + fcw + correction_ext;
    end
end

assign phase_out = accumulated_phase[ACCUM_WIDTH-1 -: PHASE_WIDTH];
assign phase_msb = accumulated_phase[ACCUM_WIDTH-1];

endmodule
