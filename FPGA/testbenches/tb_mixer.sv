// Testbench for mixer
// Verifies: signed multiplication, processing enable, FIFO control, full-scale inputs
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_mixer;

    localparam INPUT_WIDTH      = 16;
    localparam OUTPUT_WIDTH     = 32;
    localparam FIFO_COUNT_WIDTH = 8;
    localparam CLK_PERIOD       = 5.0; // 200 MHz

    logic                           clock;
    logic                           reset_n;
    logic [INPUT_WIDTH-1:0]         adc_sample;
    logic [INPUT_WIDTH-1:0]         cos_ref;
    logic [INPUT_WIDTH-1:0]         sin_ref;
    logic [FIFO_COUNT_WIDTH-1:0]    fifo_data_count;
    logic                           fifo_rd_en;
    logic                           processing_enable;
    logic [OUTPUT_WIDTH-1:0]        i_out;
    logic [OUTPUT_WIDTH-1:0]        q_out;
    logic                           valid_out;

    mixer #(
        .INPUT_WIDTH(INPUT_WIDTH),
        .OUTPUT_WIDTH(OUTPUT_WIDTH),
        .FIFO_COUNT_WIDTH(FIFO_COUNT_WIDTH)
    ) uut (
        .clock             (clock),
        .reset_n           (reset_n),
        .adc_sample        (adc_sample),
        .cos_ref           (cos_ref),
        .sin_ref           (sin_ref),
        .fifo_data_count   (fifo_data_count),
        .fifo_rd_en        (fifo_rd_en),
        .processing_enable (processing_enable),
        .i_out             (i_out),
        .q_out             (q_out),
        .valid_out         (valid_out)
    );

    // Clock generation
    initial clock = 1'b0;
    always #(CLK_PERIOD / 2.0) clock = ~clock;

    // Test sequence
    integer errors = 0;

    task automatic check(input string msg, input logic condition);
        if (!condition) begin
            $error("FAIL: %s", msg);
            errors++;
        end else begin
            $display("PASS: %s", msg);
        end
    endtask

    // expected product helper (signed 16x16 -> 32)
    function automatic [OUTPUT_WIDTH-1:0] expected_product;
        input [INPUT_WIDTH-1:0] a;
        input [INPUT_WIDTH-1:0] b;
        begin
            expected_product = $signed(a) * $signed(b);
        end
    endfunction

    initial begin
        $display("=== Mixer Testbench ===");

        // -------------------------------------------------------
        // Test 1: Reset clears outputs
        // -------------------------------------------------------
        reset_n           = 1'b0;
        adc_sample        = '0;
        cos_ref           = '0;
        sin_ref           = '0;
        fifo_data_count   = '0;
        processing_enable = 1'b0;
        repeat (4) @(posedge clock);

        check("Reset: i_out is zero",     i_out === '0);
        check("Reset: q_out is zero",     q_out === '0);
        check("Reset: valid_out is low",  valid_out === 1'b0);
        check("Reset: fifo_rd_en is low", fifo_rd_en === 1'b0);

        // -------------------------------------------------------
        // Test 2: Known positive inputs produce correct product
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        adc_sample        = 16'd100;
        cos_ref           = 16'd200;
        sin_ref           = 16'd300;
        fifo_data_count   = 8'd10;
        processing_enable = 1'b1;

        @(posedge clock);
        @(negedge clock);

        // 100 * 200 = 20000, 100 * 300 = 30000
        check("Positive: i_out == 100 * 200 = 20000",
              $signed(i_out) === 32'sd20000);
        check("Positive: q_out == 100 * 300 = 30000",
              $signed(q_out) === 32'sd30000);
        check("Positive: valid_out asserted",   valid_out === 1'b1);
        check("Positive: fifo_rd_en asserted",  fifo_rd_en === 1'b1);

        // -------------------------------------------------------
        // Test 3: Signed negative inputs
        // -------------------------------------------------------
        adc_sample = -16'sd1000;
        cos_ref    = 16'sd500;
        sin_ref    = -16'sd750;

        @(posedge clock);
        @(negedge clock);

        // -1000 * 500 = -500000, -1000 * -750 = 750000
        check("Negative: i_out == -1000 * 500 = -500000",
              $signed(i_out) === -32'sd500000);
        check("Negative: q_out == -1000 * -750 = 750000",
              $signed(q_out) === 32'sd750000);

        // -------------------------------------------------------
        // Test 4: Output is zero when processing_enable deasserted
        // -------------------------------------------------------
        processing_enable = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Disabled: i_out is zero",     i_out === '0);
        check("Disabled: q_out is zero",     q_out === '0);
        check("Disabled: valid_out is low",  valid_out === 1'b0);
        check("Disabled: fifo_rd_en is low", fifo_rd_en === 1'b0);

        // -------------------------------------------------------
        // Test 5: FIFO read enable only when FIFO has data
        // -------------------------------------------------------
        processing_enable = 1'b1;
        fifo_data_count   = 8'd0;

        @(posedge clock);
        @(negedge clock);
        check("Empty FIFO: fifo_rd_en is low",  fifo_rd_en === 1'b0);
        check("Empty FIFO: valid_out is low",   valid_out === 1'b0);

        fifo_data_count = 8'd1;

        @(posedge clock);
        @(negedge clock);
        check("FIFO has data: fifo_rd_en asserted", fifo_rd_en === 1'b1);
        check("FIFO has data: valid_out asserted",  valid_out === 1'b1);

        // -------------------------------------------------------
        // Test 6: Full-scale positive (max positive * max positive)
        // -------------------------------------------------------
        adc_sample = 16'h7FFF;  // +32767
        cos_ref    = 16'h7FFF;  // +32767
        sin_ref    = 16'h7FFF;
        fifo_data_count = 8'd50;

        @(posedge clock);
        @(negedge clock);

        // 32767 * 32767 = 1073676289 = 0x3FFF_0001
        check("Full-scale pos: i_out == 32767^2 = 0x3FFF0001",
              i_out === expected_product(16'h7FFF, 16'h7FFF));

        // -------------------------------------------------------
        // Test 7: Full-scale negative (most negative * most negative)
        // -------------------------------------------------------
        adc_sample = 16'h8000;  // -32768
        cos_ref    = 16'h8000;  // -32768
        sin_ref    = 16'h8000;

        @(posedge clock);
        @(negedge clock);

        // (-32768) * (-32768) = 1073741824 = 0x4000_0000
        check("Full-scale neg: i_out == (-32768)^2 = 0x40000000",
              i_out === expected_product(16'h8000, 16'h8000));

        // -------------------------------------------------------
        // Test 8: Max positive * max negative (cross sign)
        // -------------------------------------------------------
        adc_sample = 16'h7FFF;  // +32767
        cos_ref    = 16'h8000;  // -32768
        sin_ref    = 16'h8001;  // -32767

        @(posedge clock);
        @(negedge clock);

        // 32767 * (-32768) = -1073709056
        check("Cross sign: i_out == 32767 * (-32768)",
              i_out === expected_product(16'h7FFF, 16'h8000));
        // 32767 * (-32767) = -1073676289
        check("Cross sign: q_out == 32767 * (-32767)",
              q_out === expected_product(16'h7FFF, 16'h8001));

        // -------------------------------------------------------
        // Test 9: Zero ADC sample produces zero outputs
        // -------------------------------------------------------
        adc_sample = 16'd0;
        cos_ref    = 16'h7FFF;
        sin_ref    = 16'h8000;

        @(posedge clock);
        @(negedge clock);
        check("Zero sample: i_out == 0", i_out === '0);
        check("Zero sample: q_out == 0", q_out === '0);

        // -------------------------------------------------------
        // Summary
        // -------------------------------------------------------
        $display("=== Test Complete: %0d errors ===", errors);
        if (errors == 0)
            $display("ALL TESTS PASSED");
        else
            $display("SOME TESTS FAILED");

        $finish;
    end

endmodule
