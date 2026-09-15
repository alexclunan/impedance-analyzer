//=============================================================================
// adc_fifo_read - Processing domain (clk_fpga_0). Reads the FIFO Generator core
// (configured First_Word_Fall_Through), holds last value when starved, and
// unpacks the ADC data + OR bits.
//=============================================================================
// FWFT timing: whenever fifo_empty is LOW, fifo_dout already holds a valid word
// THIS cycle, and asserting rd_en pops it (dout advances to the next word). So
// we must latch fifo_dout on the SAME cycle as ~empty. The previous version
// delayed the latch by one cycle (for standard, non-FWFT mode) -- in FWFT that
// latched dout AFTER the word had been popped (stale/invalid), dropping every
// real sample. That was the "ADC data not getting through the FIFO" bug.
//=============================================================================
module adc_fifo_read (
    input  wire        rd_clk,         // processing domain clock (clk_fpga_0)

    // FIFO Generator core ports (rd side), FWFT mode
    output wire        fifo_rd_en,
    input  wire [17:0] fifo_dout,
    input  wire        fifo_empty,

    output reg  [15:0] adc_data_out,   // held/latched ADC data
    output reg  [1:0]  adc_or_out      // held/latched OR bits
);

    // FWFT: pop whenever data is available.
    assign fifo_rd_en = ~fifo_empty;

    always @(posedge rd_clk) begin
        if (~fifo_empty) begin
            // FWFT: fifo_dout is the valid head word THIS cycle - latch it as
            // it is popped.
            adc_data_out <= fifo_dout[15:0];
            adc_or_out   <= fifo_dout[17:16];
        end
        // else: FIFO starved - hold the previous value (implicit).
    end

endmodule
