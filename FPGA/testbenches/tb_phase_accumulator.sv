// Testbench for phase_accumulator
// Verifies: reset, phase increment, MSB toggle rate, frequency resolution
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_phase_accumulator;

    localparam ACCUM_WIDTH = 48;
    localparam PHASE_WIDTH = 16;
    localparam CLK_PERIOD  = 5.0; // 200 MHz

    logic                       clock;
    logic                       reset_n;
    logic [ACCUM_WIDTH-1:0]     fcw;
    logic [PHASE_WIDTH-1:0]     phase_out;
    logic                       phase_msb;

    phase_accumulator #(
        .ACCUM_WIDTH(ACCUM_WIDTH),
        .PHASE_WIDTH(PHASE_WIDTH)
    ) uut (
        .clock     (clock),
        .reset_n   (reset_n),
        .fcw       (fcw),
        .phase_out (phase_out),
        .phase_msb (phase_msb)
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

    // Track MSB transitions
    logic prev_msb;
    integer msb_toggle_count;

    initial begin
        $display("=== Phase Accumulator Testbench ===");
        $display("Accumulator width: %0d, Phase width: %0d", ACCUM_WIDTH, PHASE_WIDTH);

        // -------------------------------------------------------
        // Test 1: Reset clears accumulator
        // -------------------------------------------------------
        reset_n = 1'b0;
        fcw     = '0;
        repeat (4) @(posedge clock);

        check("Reset: phase_out is zero", phase_out == '0);
        check("Reset: phase_msb is zero", phase_msb == 1'b0);

        // -------------------------------------------------------
        // Test 2: Phase increments correctly for a known FCW
        // -------------------------------------------------------
        // FCW = 1 in the upper 16 bits -> phase_out increments by 1 each cycle
        // That means FCW = 1 << 32 = 48'h0001_0000_0000
        fcw = 48'h0001_0000_0000;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // After 1 cycle, phase_out should be 1
        @(posedge clock);
        @(negedge clock); // sample after register update
        check("Increment: phase_out == 1 after first cycle",
              phase_out == 16'd1);

        // After 10 more cycles, phase_out should be 11
        repeat (10) @(posedge clock);
        @(negedge clock);
        check("Increment: phase_out == 11 after 11 cycles",
              phase_out == 16'd11);

        // -------------------------------------------------------
        // Test 3: MSB toggles at expected rate
        // -------------------------------------------------------
        // FCW = 48'h800000000000 sets MSB every cycle (half the accumulator range)
        // MSB should toggle every single clock cycle
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'h8000_0000_0000;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        prev_msb = 1'b0;
        msb_toggle_count = 0;

        repeat (100) begin
            @(posedge clock);
            @(negedge clock);
            if (phase_msb !== prev_msb)
                msb_toggle_count++;
            prev_msb = phase_msb;
        end

        check("MSB toggle: toggles every cycle (100 toggles in 100 cycles)",
              msb_toggle_count == 100);

        // -------------------------------------------------------
        // Test 4: Minimum FCW step produces single-LSB phase increment
        // -------------------------------------------------------
        // FCW = 1 -> accumulator increments by 1 each cycle
        // After 2^32 cycles, phase_out should increment by 1
        // We can't run 2^32 cycles, so verify accumulator LSB increments
        // and that phase_out stays at 0 for the first 2^32-1 cycles
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'd1;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // After 100 cycles with FCW=1, accumulated_phase = 100
        // phase_out = accumulated_phase[47:32] = 0 (since 100 < 2^32)
        repeat (100) @(posedge clock);
        @(negedge clock);
        check("Resolution: phase_out stays 0 with FCW=1 after 100 cycles",
              phase_out == 16'd0);

        // -------------------------------------------------------
        // Test 5: Full-scale rollover
        // -------------------------------------------------------
        // FCW chosen so accumulator wraps cleanly
        // FCW = 48'hFFFF_0000_0000 -> phase_out decrements by 1 each cycle (wrapping)
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'hFFFF_0000_0000;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Rollover: phase_out == 0xFFFF after 1 cycle with FCW=0xFFFF<<32",
              phase_out == 16'hFFFF);

        repeat (1) @(posedge clock);
        @(negedge clock);
        check("Rollover: phase_out == 0xFFFE after 2 cycles",
              phase_out == 16'hFFFE);

        // -------------------------------------------------------
        // Test 6: FCW change mid-operation
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'h0001_0000_0000;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        repeat (5) @(posedge clock);
        @(negedge clock);
        check("FCW change: phase_out == 5 after 5 cycles with FCW=1<<32",
              phase_out == 16'd5);

        // Change FCW to 2<<32
        fcw = 48'h0002_0000_0000;
        repeat (5) @(posedge clock);
        @(negedge clock);
        check("FCW change: phase_out == 15 after 5 more cycles with FCW=2<<32",
              phase_out == 16'd15);

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
