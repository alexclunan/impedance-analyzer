// Testbench for adc_data_realignment
// Verifies: sample reconstruction, polarity inversion, capture select, edge cases
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_adc_data_realignment;

    localparam WIDTH      = 16;
    localparam CLK_PERIOD = 5.0; // 200 MHz

    logic                   clock;
    logic                   reset_n;
    logic [2*WIDTH-1:0]     raw_data;
    logic [WIDTH-1:0]       polarity_mask;
    logic                   capture_select;
    logic [WIDTH-1:0]       adc_sample;
    logic                   adc_valid;

    adc_data_realignment #(
        .WIDTH(WIDTH)
    ) uut (
        .clock          (clock),
        .reset_n        (reset_n),
        .raw_data       (raw_data),
        .polarity_mask  (polarity_mask),
        .capture_select (capture_select),
        .adc_sample     (adc_sample),
        .adc_valid      (adc_valid)
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

    initial begin
        $display("=== ADC Data Realignment Testbench ===");
        $display("Data width: %0d", WIDTH);

        // -------------------------------------------------------
        // Test 1: Reset clears output and deasserts valid
        // -------------------------------------------------------
        reset_n        = 1'b0;
        raw_data       = '0;
        polarity_mask  = '0;
        capture_select = 1'b0;
        repeat (4) @(posedge clock);

        check("Reset: adc_sample is zero",  adc_sample === '0);
        check("Reset: adc_valid is low",    adc_valid  === 1'b0);

        // -------------------------------------------------------
        // Test 2: Upper half selected (capture_select = 0)
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        raw_data       = {16'hA5A5, 16'h5A5A};
        polarity_mask  = 16'h0000;
        capture_select = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Upper select: adc_sample == 0xA5A5 (upper half)",
              adc_sample === 16'hA5A5);
        check("Upper select: adc_valid asserted",
              adc_valid === 1'b1);

        // -------------------------------------------------------
        // Test 3: Lower half selected (capture_select = 1)
        // -------------------------------------------------------
        capture_select = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Lower select: adc_sample == 0x5A5A (lower half)",
              adc_sample === 16'h5A5A);

        // -------------------------------------------------------
        // Test 4: Single-bit polarity inversion
        // -------------------------------------------------------
        raw_data       = {16'h0000, 16'h0000};
        polarity_mask  = 16'h0001;
        capture_select = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Single-bit invert: bit 0 inverted, adc_sample == 0x0001",
              adc_sample === 16'h0001);

        // verify same inversion applies to lower half
        capture_select = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Single-bit invert lower: bit 0 inverted, adc_sample == 0x0001",
              adc_sample === 16'h0001);

        // -------------------------------------------------------
        // Test 5: Each bit of polarity_mask inverts independently
        // -------------------------------------------------------
        capture_select = 1'b0;

        // walk a 1 through each bit of polarity_mask
        begin : per_lane_test
            integer i;
            logic [WIDTH-1:0] expected;
            logic all_passed;
            all_passed = 1'b1;

            for (i = 0; i < WIDTH; i++) begin
                raw_data      = '0;
                polarity_mask = (16'd1 << i);

                @(posedge clock);
                @(negedge clock);

                expected = (16'd1 << i);
                if (adc_sample !== expected) begin
                    $error("FAIL: Per-lane invert bit %0d: expected 0x%04h, got 0x%04h",
                           i, expected, adc_sample);
                    errors++;
                    all_passed = 1'b0;
                end
            end

            if (all_passed)
                $display("PASS: Per-lane invert: all 16 bits independently verified");
        end

        // -------------------------------------------------------
        // Test 6: All-ones polarity mask (full inversion)
        // -------------------------------------------------------
        raw_data       = {16'hA5A5, 16'h0000};
        polarity_mask  = 16'hFFFF;
        capture_select = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("All-ones mask: 0xA5A5 inverted == 0x5A5A",
              adc_sample === 16'h5A5A);

        // -------------------------------------------------------
        // Test 7: All-zeros polarity mask (no inversion)
        // -------------------------------------------------------
        polarity_mask = 16'h0000;

        @(posedge clock);
        @(negedge clock);
        check("All-zeros mask: 0xA5A5 unchanged",
              adc_sample === 16'hA5A5);

        // -------------------------------------------------------
        // Test 8: Polarity + capture_select combined
        // -------------------------------------------------------
        raw_data       = {16'hFF00, 16'h00FF};
        polarity_mask  = 16'h0F0F;
        capture_select = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Combined upper: 0xFF00 ^ 0x0F0F == 0xF00F",
              adc_sample === 16'hF00F);

        capture_select = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Combined lower: 0x00FF ^ 0x0F0F == 0x0FF0",
              adc_sample === 16'h0FF0);

        // -------------------------------------------------------
        // Test 9: Realistic ADC pattern
        // -------------------------------------------------------
        // simulate a known 16-bit 2's complement sample in upper half
        raw_data       = {16'hFE0C, 16'h01F3};
        polarity_mask  = 16'h0000;
        capture_select = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Realistic pattern upper: 0xFE0C passthrough",
              adc_sample === 16'hFE0C);

        capture_select = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Realistic pattern lower: 0x01F3 passthrough",
              adc_sample === 16'h01F3);

        // -------------------------------------------------------
        // Test 10: Valid deasserts on reset, reasserts on release
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Re-reset: adc_valid deasserted", adc_valid === 1'b0);

        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Re-release: adc_valid reasserted", adc_valid === 1'b1);

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
