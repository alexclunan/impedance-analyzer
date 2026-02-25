// phase adjuster for impedance phase correction
// subtracts a configurable base offset from the measured phase
// Author: Alex Clunan
module phase_adjuster
    // data width parameter
    #(parameter WIDTH = 32)
(
    input                   clock,
    input                   reset_n,
    // clock enable (decimated rate)
    input                   ce,
    // phase inputs
    input   [WIDTH-1:0]     measured_phase,
    input   [WIDTH-1:0]     base_phase_offset,
    // corrected output
    output  [WIDTH-1:0]     corrected_phase);

// output register
reg [WIDTH-1:0] corrected_phase_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        corrected_phase_reg <= {WIDTH{1'b0}};

    // update on clock enable
    end else if (ce == 1'b1) begin
        corrected_phase_reg <= measured_phase - base_phase_offset;
    end
end

assign corrected_phase = corrected_phase_reg;

endmodule
