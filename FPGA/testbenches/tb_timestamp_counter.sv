// Testbench for timestamp_counter
// Verifies: reset, per-cycle increment, correct value after N cycles
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_timestamp_counter;

    localparam COUNT_WIDTH = 64;
    localparam CLK_PERIOD  = 5.0; // 200 MHz

    logic                       clock;
    logic                       reset_n;
    logic [COUNT_WIDTH-1:0]     timestamp;

    timestamp_counter #(
        .COUNT_WIDTH(COUNT_WIDTH)
    ) uut (
        .clock     (clock),
        .reset_n   (reset_n),
        .timestamp (timestamp)
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
        $display("=== Timestamp Counter Testbench ===");
        $display("Counter width: %0d", COUNT_WIDTH);

        // -------------------------------------------------------
        // Test 1: Reset clears counter
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (4) @(posedge clock);

        check("Reset: timestamp is zero", timestamp === '0);

        // -------------------------------------------------------
        // Test 2: Increments every clock cycle
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Increment: timestamp == 1 after first cycle",
              timestamp === 64'd1);

        @(posedge clock);
        @(negedge clock);
        check("Increment: timestamp == 2 after second cycle",
              timestamp === 64'd2);

        @(posedge clock);
        @(negedge clock);
        check("Increment: timestamp == 3 after third cycle",
              timestamp === 64'd3);

        // -------------------------------------------------------
        // Test 3: Correct value after N cycles
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        repeat (1000) @(posedge clock);
        @(negedge clock);
        check("Count: timestamp == 1000 after 1000 cycles",
              timestamp === 64'd1000);

        // -------------------------------------------------------
        // Test 4: Continues counting from current value (no glitch)
        // -------------------------------------------------------
        repeat (500) @(posedge clock);
        @(negedge clock);
        check("Continue: timestamp == 1500 after 500 more cycles",
              timestamp === 64'd1500);

        // -------------------------------------------------------
        // Test 5: Reset mid-count returns to zero
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Mid-count reset: timestamp is zero",
              timestamp === '0);

        // release and verify counting resumes from zero
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        repeat (10) @(posedge clock);
        @(negedge clock);
        check("Resume: timestamp == 10 after reset and 10 cycles",
              timestamp === 64'd10);

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
