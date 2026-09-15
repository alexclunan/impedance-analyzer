module sample_hold #(
    parameter CLK_FREQ_HZ    = 200_000_000,
    parameter SAMPLE_RATE_HZ = 625_000
)(
    input  wire        clk,
    input  wire        rst_n,

    // AXI4-Stream input (from FIFO)
    input  wire [15:0] s_axis_tdata,
    input  wire        s_axis_tvalid,
    input  wire        s_axis_tlast,
    output reg         s_axis_tready,

    // Status flags from FIFO
    input  wire        fifo_almost_empty,
    input  wire        fifo_prog_empty,

    // ADC-like output to PL module
    output reg  [15:0] adc_data,
    output reg         adc_valid,

    // Flow control to PS
    output wire        request_refill
);

    // 200MHz / 625kHz = 320 clocks per sample
    localparam CLKS_PER_SAMPLE = CLK_FREQ_HZ / SAMPLE_RATE_HZ;

    reg [$clog2(CLKS_PER_SAMPLE)-1:0] sample_counter;
    reg                                sample_tick;

    // Sample tick generator
    always @(posedge clk) begin
        if (!rst_n) begin
            sample_counter <= 0;
            sample_tick    <= 1'b0;
        end else begin
            if (sample_counter == CLKS_PER_SAMPLE - 1) begin
                sample_counter <= 0;
                sample_tick    <= 1'b1;
            end else begin
                sample_counter <= sample_counter + 1;
                sample_tick    <= 1'b0;
            end
        end
    end

    // Sample-hold logic
    always @(posedge clk) begin
        if (!rst_n) begin
            adc_data       <= 16'h0000;
            adc_valid      <= 1'b0;
            s_axis_tready  <= 1'b0;
        end else begin
            // Defaults
            s_axis_tready <= 1'b0;
            adc_valid     <= 1'b0;

            if (sample_tick) begin
                adc_valid <= 1'b1;  // always output on tick, even if stale

                if (s_axis_tvalid) begin
                    adc_data      <= s_axis_tdata;
                    s_axis_tready <= 1'b1;  // consume one word from FIFO
                end
                // else: FIFO empty, hold last value in adc_data
            end
        end
    end

    // Refill request direct from FIFO flag
    assign request_refill = fifo_prog_empty;

endmodule