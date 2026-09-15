// DAC output wrapper with test mode MUX
// selects between DDS sine output and calibration test pulse
// Author: Alex Clunan
//
// Pipelined (was fully combinational into dac_out_reg -> failed timing at
// 200 MHz because the tool absorbed the mux + PCB-inversion into the upstream
// multitone-mixer DSP48, creating a long DSP path).  Three stages now:
//   S1  register the inputs (isolates the mixer DSP from the mux)
//   S2  registered mux (hold last value while input_data_valid is low)
//   S3  registered PCB PN inversion (clean register -> SelectIO ODDR)
// Latency is +2 cycles: a fixed DAC-path delay, absorbed by calibration. Port
// list is unchanged, so the module-ref boundary does not move.
module dac_output_wrapper
    #(parameter WIDTH = 16)
(
    input                   clock,
    // normal DDS data
    input   [WIDTH-1:0]     dds_cos,
    input                   input_data_valid,
    // calibration test pulse
    input   [WIDTH-1:0]     test_pulse_data,
    // mode select: 0 = normal, 1 = test pulse
    input                   test_mode,
    // output to SelectIO IP (active after reset)
    output  [WIDTH-1:0]     dac_out,
    output                  dac_data_valid);

// ---- stage 1: register inputs (breaks the mixer-DSP -> mux absorption) ----
reg [WIDTH-1:0] dds_cos_r      = {WIDTH{1'b0}};
reg [WIDTH-1:0] test_pulse_r   = {WIDTH{1'b0}};
reg             test_mode_r    = 1'b0;
reg             valid_r        = 1'b0;
always @(posedge clock) begin
    dds_cos_r    <= dds_cos;
    test_pulse_r <= test_pulse_data;
    test_mode_r  <= test_mode;
    valid_r      <= input_data_valid;
end

// ---- stage 2: registered MUX (hold last value when not valid) ----
reg [WIDTH-1:0] dac_out_reg    = {WIDTH{1'b0}};
reg             dac_dv_reg     = 1'b0;
always @(posedge clock) begin
    if (valid_r != 1'b1) begin
        dac_out_reg <= dac_out_reg;
        dac_dv_reg  <= 1'b0;
    end else begin
        dac_out_reg <= test_mode_r ? test_pulse_r : dds_cos_r;
        dac_dv_reg  <= 1'b1;
    end
end

// ---- stage 3: registered PCB PN inversion (clean reg -> SelectIO) ----
// invert some bits to match the PCB differential-pair swaps
reg [WIDTH-1:0] dac_out_xor    = {WIDTH{1'b0}};
reg             dac_dv_r2      = 1'b0;
always @(posedge clock) begin
    dac_out_xor <= dac_out_reg ^ 16'h7D7D;
    dac_dv_r2   <= dac_dv_reg;
end

assign dac_out        = dac_out_xor;
assign dac_data_valid = dac_dv_r2;

endmodule
