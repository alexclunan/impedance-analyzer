// running mean subtractor for AC-coupled magnitude readout
// Author: Alex Clunan
module running_mean_subtractor
    // averaging parameters
    #(parameter DATA_WIDTH = 32,
      parameter AVG_SHIFT  = 10)
(
    input                           clock,
    input                           reset_n,
    // input magnitude stream
    input   [DATA_WIDTH-1:0]        signal_in,
    input                           valid_in,
    // averaged and AC-coupled outputs
    output  [DATA_WIDTH-1:0]        mean_out,
    output  signed [DATA_WIDTH:0]   signal_ac,
    output                          valid_out);

// signed average and AC registers
reg signed [DATA_WIDTH:0] mean_reg;
reg signed [DATA_WIDTH:0] signal_ac_reg;
reg                       valid_out_reg;

// signed calculation wires
wire signed [DATA_WIDTH:0] signal_extended = {1'b0, signal_in};
wire signed [DATA_WIDTH:0] mean_error      = signal_extended - mean_reg;
wire signed [DATA_WIDTH:0] mean_step       = mean_error >>> AVG_SHIFT;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        mean_reg       <= {(DATA_WIDTH+1){1'b0}};
        signal_ac_reg  <= {(DATA_WIDTH+1){1'b0}};
        valid_out_reg  <= 1'b0;

    // update running mean on valid samples
    end else if (valid_in == 1'b1) begin
        signal_ac_reg  <= signal_extended - mean_reg;
        mean_reg       <= mean_reg + mean_step;
        valid_out_reg  <= 1'b1;

    // hold state between valid samples
    end else begin
        mean_reg       <= mean_reg;
        signal_ac_reg  <= signal_ac_reg;
        valid_out_reg  <= 1'b0;
    end
end

assign mean_out  = mean_reg[DATA_WIDTH-1:0];
assign signal_ac = signal_ac_reg;
assign valid_out = valid_out_reg;

endmodule
