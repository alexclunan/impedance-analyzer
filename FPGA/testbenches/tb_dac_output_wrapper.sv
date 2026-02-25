// Testbench for dac_output_wrapper
// Verifies: MUX selection, data passthrough, reset behavior
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_dac_output_wrapper;

    localparam WIDTH      = 16;
    localparam CLK_PERIOD = 5.0; // 200 MHz

    logic                   clock;
    logic                   reset_n;
    logic [WIDTH-1:0]       dds_data;
    logic [WIDTH-1:0]       test_pulse_data;
    logic                   test_mode;
    logic [WIDTH-1:0]       dac_data;
    logic                   dac_data_valid;

    dac_output_wrapper #(
        .WIDTH(WIDTH)
    ) uut (
        .clock           (clock),
        .reset_n         (reset_n),
        .dds_data        (dds_data),
        .test_pulse_data (test_pulse_data),
        .test_mode       (test_mode),
        .dac_data        (dac_data),
        .dac_data_valid  (dac_data_valid)
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
        $display("=== DAC Output Wrapper Testbench ===");

        // -------------------------------------------------------
        // Test 1: Reset clears output and deasserts valid
        // -------------------------------------------------------
        reset_n         = 1'b0;
        dds_data        = 16'hAAAA;
        test_pulse_data = 16'h5555;
        test_mode       = 1'b0;
        repeat (4) @(posedge clock);

        check("Reset: dac_data is zero",     dac_data === '0);
        check("Reset: dac_data_valid is low", dac_data_valid === 1'b0);

        // -------------------------------------------------------
        // Test 2: Normal mode passes DDS data
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        dds_data        = 16'h1234;
        test_pulse_data = 16'hABCD;
        test_mode       = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Normal mode: dac_data == dds_data (0x1234)",
              dac_data === 16'h1234);
        check("Normal mode: dac_data_valid asserted",
              dac_data_valid === 1'b1);

        // -------------------------------------------------------
        // Test 3: Test mode passes test pulse data
        // -------------------------------------------------------
        test_mode = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Test mode: dac_data == test_pulse_data (0xABCD)",
              dac_data === 16'hABCD);

        // -------------------------------------------------------
        // Test 4: MUX switches cleanly between modes
        // -------------------------------------------------------
        dds_data        = 16'h7FFF;
        test_pulse_data = 16'h8000;

        test_mode = 1'b0;
        @(posedge clock);
        @(negedge clock);
        check("Switch to normal: dac_data == 0x7FFF",
              dac_data === 16'h7FFF);

        test_mode = 1'b1;
        @(posedge clock);
        @(negedge clock);
        check("Switch to test: dac_data == 0x8000",
              dac_data === 16'h8000);

        test_mode = 1'b0;
        @(posedge clock);
        @(negedge clock);
        check("Switch back to normal: dac_data == 0x7FFF",
              dac_data === 16'h7FFF);

        // -------------------------------------------------------
        // Test 5: Data changes propagate in normal mode
        // -------------------------------------------------------
        test_mode = 1'b0;

        dds_data = 16'h0001;
        @(posedge clock);
        @(negedge clock);
        check("Data update 1: dac_data == 0x0001", dac_data === 16'h0001);

        dds_data = 16'hFFFE;
        @(posedge clock);
        @(negedge clock);
        check("Data update 2: dac_data == 0xFFFE", dac_data === 16'hFFFE);

        // -------------------------------------------------------
        // Test 6: Data changes propagate in test mode
        // -------------------------------------------------------
        test_mode = 1'b1;

        test_pulse_data = 16'h0000;
        @(posedge clock);
        @(negedge clock);
        check("Test update 1: dac_data == 0x0000", dac_data === 16'h0000);

        test_pulse_data = 16'hFFFF;
        @(posedge clock);
        @(negedge clock);
        check("Test update 2: dac_data == 0xFFFF", dac_data === 16'hFFFF);

        // -------------------------------------------------------
        // Test 7: Valid deasserts on reset, reasserts on release
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Re-reset: dac_data_valid deasserted", dac_data_valid === 1'b0);

        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Re-release: dac_data_valid reasserted", dac_data_valid === 1'b1);

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
