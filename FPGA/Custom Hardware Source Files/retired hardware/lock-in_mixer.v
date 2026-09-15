// mixer for lock-in amplifier
// assumes FIFO is written to every cycle with data from DDS block
// Author: Alex Clunan
module lock_in_mixer 
    // module width
    #(parameter WIDTH = 16
    // input FIFO size
      parameter FIFO_SIZE = 256
      parameter FIFO_COUNT = $clog2(FIFO_SIZE)
    // input configuration register size
      parameter AXI_REGISTER_SIZE = 32)
(
    input clock,
    input reset_n,
    // signal IOs
    input   [WIDTH-1:0]         dds_cos,
    input   [WIDTH-1:0]         dds_sin,
    input   [WIDTH-1:0]         device_input
    output  [WIDTH-1:0]         real_signal,
    output  [WIDTH-1:0]         imag_signal,
    // FIFO control
    //input                       fifo_data_valid,
    input   [FIFO_COUNT-1:0]    fifo_data_count,
    output                      fifo_rd_en,
    // configuration setup
    input   [AXI_REGISTER_SIZE-1:0] axi_config0);

// configuration wires
wire [FIFO_COUNT-1:0]   target_fifo_data_count = axi_config0[FIFO_COUNT-1:0];
wire                    processing_enable      = axi_config0[FIFO_COUNT];

// internal ADC input buffer 
reg [1:0] [WIDTH-1:0]        ADC_input_buffer;

// output registers
reg  [WIDTH-1:0]        real_signal_register;
reg  [WIDTH-1:0]        imag_signal_register; 

// FIFO control register
reg                     fifo_rd_en_register;

always @(posedge(clock) or negedge(reset_n)) begin
    // asynchronous low reset
    if (reset_n == 0) begin
        fifo_rd_en_register  <= 0;
        real_signal_register <= 0;
        imag_signal_register <= 0;

    // main loop
    end else if (processing_enable == 1 and fifo_data_count >= target_fifo_data_count) begin
        
        fifo_rd_en_register  <= 1;

        real_signal_register <= dds_cos * ADC_input_buffer[1];
        imag_signal_register <= dds_sin * ADC_input_buffer[1];

    // disabled processing
    end else begin
        fifo_rd_en_register  <= 0;

        real_signal_register <= real_signal_register;
        imag_signal_register <= imag_signal_register;
    end

    // buffered ADC input always represents ADC input
    ADC_input_buffer[0]  <= device_input;
    ADC_input_buffer[1]  <= ADC_input_buffer[0];

end


assign fifo_rd_en = fifo_rd_en_register;
assign real_signal = real_signal_register;
assign imag_signal = imag_signal_register;

endmodule