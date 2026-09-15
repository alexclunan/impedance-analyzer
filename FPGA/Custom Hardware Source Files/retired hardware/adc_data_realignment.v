// ADC data realignment for AD9467 DDR LVDS interface
// reconstructs 16-bit sample from 32-bit IDDR output with per-lane polarity correction
// Author: Alex Clunan
module adc_data_realignment
    // data width parameter
    #(parameter WIDTH = 16)
(
    input                       clock,
    input                       reset_n,
    // IDDR deserialized input
    input   [2*WIDTH-1:0]       raw_data,
    // configuration
    input   [WIDTH-1:0]         polarity_mask,
    input                       capture_select,
    // reconstructed output
    output  [WIDTH-1:0]         adc_sample,
    output                      adc_valid);

// per-lane polarity correction applied to both halves
wire [WIDTH-1:0] upper_corrected = raw_data[2*WIDTH-1:WIDTH] ^ polarity_mask;
wire [WIDTH-1:0] lower_corrected = raw_data[WIDTH-1:0]       ^ polarity_mask;

// byte-order selection based on capture phase
wire [WIDTH-1:0] selected_sample = capture_select ? lower_corrected : upper_corrected;

// output registers
reg [WIDTH-1:0] adc_sample_reg;
reg             adc_valid_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        adc_sample_reg <= {WIDTH{1'b0}};
        adc_valid_reg  <= 1'b0;

    // register reconstructed sample
    end else begin
        adc_sample_reg <= selected_sample;
        adc_valid_reg  <= 1'b1;
    end
end

assign adc_sample = adc_sample_reg;
assign adc_valid  = adc_valid_reg;

endmodule
