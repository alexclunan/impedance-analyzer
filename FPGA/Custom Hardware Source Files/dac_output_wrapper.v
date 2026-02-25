// DAC output wrapper with test mode MUX
// selects between DDS sine output and calibration test pulse
// Author: Alex Clunan
module dac_output_wrapper
    // data width parameter
    #(parameter WIDTH = 16)
(
    input                   clock,
    input                   reset_n,
    // normal DDS data
    input   [WIDTH-1:0]     dds_data,
    // calibration test pulse
    input   [WIDTH-1:0]     test_pulse_data,
    // mode select: 0 = normal, 1 = test pulse
    input                   test_mode,
    // output to SelectIO IP (active after reset)
    output  [WIDTH-1:0]     dac_data,
    output                  dac_data_valid);

// MUX and output register
reg [WIDTH-1:0] dac_data_reg;
reg             dac_data_valid_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        dac_data_reg       <= {WIDTH{1'b0}};
        dac_data_valid_reg <= 1'b0;

    // registered MUX output
    end else begin
        dac_data_reg       <= test_mode ? test_pulse_data : dds_data;
        dac_data_valid_reg <= 1'b1;
    end
end

assign dac_data       = dac_data_reg;
assign dac_data_valid = dac_data_valid_reg;

endmodule
