module adc_fifo_write (
    
    input  wire [17:0] adc_data_in,    // raw ADC sample from IDDR/deserializer

    output wire [17:0] fifo_din,
    output wire        fifo_wr_en,
    input  wire        fifo_full
);

    // Pack: {OR[1:0], ADC_DATA[15:0]} -> 18 bits total
   
    assign fifo_din = adc_data_in;

    // If full, sample is silently dropped - no stall, no backpressure to ADC side.
    assign fifo_wr_en = ~fifo_full;

endmodule