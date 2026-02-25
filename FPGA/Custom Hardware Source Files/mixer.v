// digital lock-in mixer for impedance demodulation
// multiplies ADC sample with delayed sin/cos references, full 32-bit signed product
// Author: Alex Clunan
module mixer
    // data width parameters
    #(parameter INPUT_WIDTH      = 16,
      parameter OUTPUT_WIDTH     = 32,
      parameter FIFO_COUNT_WIDTH = 8)
(
    input                           clock,
    input                           reset_n,
    // ADC input
    input   [INPUT_WIDTH-1:0]       adc_sample,
    // reference inputs from delay FIFO
    input   [INPUT_WIDTH-1:0]       cos_ref,
    input   [INPUT_WIDTH-1:0]       sin_ref,
    // FIFO control
    input   [FIFO_COUNT_WIDTH-1:0]  fifo_data_count,
    output                          fifo_rd_en,
    // processing control
    input                           processing_enable,
    // demodulated outputs
    output  [OUTPUT_WIDTH-1:0]      i_out,
    output  [OUTPUT_WIDTH-1:0]      q_out,
    output                          valid_out);

// FIFO has data when count is non-zero
wire fifo_has_data = (fifo_data_count != {FIFO_COUNT_WIDTH{1'b0}});

// output registers
reg [OUTPUT_WIDTH-1:0]  i_out_reg;
reg [OUTPUT_WIDTH-1:0]  q_out_reg;
reg                     valid_out_reg;
reg                     fifo_rd_en_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        i_out_reg      <= {OUTPUT_WIDTH{1'b0}};
        q_out_reg      <= {OUTPUT_WIDTH{1'b0}};
        valid_out_reg  <= 1'b0;
        fifo_rd_en_reg <= 1'b0;

    // active mixing
    end else if (processing_enable == 1'b1 && fifo_has_data) begin
        i_out_reg      <= $signed(adc_sample) * $signed(cos_ref);
        q_out_reg      <= $signed(adc_sample) * $signed(sin_ref);
        valid_out_reg  <= 1'b1;
        fifo_rd_en_reg <= 1'b1;

    // disabled: clear outputs and stop reading FIFO
    end else begin
        i_out_reg      <= {OUTPUT_WIDTH{1'b0}};
        q_out_reg      <= {OUTPUT_WIDTH{1'b0}};
        valid_out_reg  <= 1'b0;
        fifo_rd_en_reg <= 1'b0;
    end
end

assign i_out      = i_out_reg;
assign q_out      = q_out_reg;
assign valid_out  = valid_out_reg;
assign fifo_rd_en = fifo_rd_en_reg;

endmodule
