// Testbench for phase_adjuster
// Verifies: subtraction, wrapping, clock enable gating
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_phase_adjuster;

    localparam WIDTH      = 32;
    localparam CLK_PERIOD = 5.0; // 200 MHz

    logic                   clock;
    logic                   reset_n;
    logic                   ce;
    logic [WIDTH-1:0]       measured_phase;
    logic [WIDTH-1:0]       base_phase_offset;
    logic [WIDTH-1:0]       corrected_phase;

    phase_adjuster #(
        .WIDTH(WIDTH)
    ) uut (
        .clock             (clock),
        .reset_n           (reset_n),
        .ce                (ce),
        .measured_phase    (measured_phase),
        .base_phase_offset (base_phase_offset),
        .corrected_phase   (corrected_phase)
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
        $display("=== Phase Adjuster Testbench ===");
        $display("Data width: %0d", WIDTH);

        // -------------------------------------------------------
        // Test 1: Reset clears output
        // -------------------------------------------------------
        reset_n           = 1'b0;
        ce                = 1'b0;
        measured_phase    = '0;
        base_phase_offset = '0;
        repeat (4) @(posedge clock);

        check("Reset: corrected_phase is zero", corrected_phase === '0);

        // -------------------------------------------------------
        // Test 2: Positive offset subtraction
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        measured_phase    = 32'h0000_1000;
        base_phase_offset = 32'h0000_0400;
        ce = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Positive offset: 0x1000 - 0x0400 == 0x0C00",
              corrected_phase === 32'h0000_0C00);

        // -------------------------------------------------------
        // Test 3: Output holds when ce is deasserted
        // -------------------------------------------------------
        ce = 1'b0;
        measured_phase    = 32'hDEAD_BEEF;
        base_phase_offset = 32'h0000_0000;

        repeat (5) @(posedge clock);
        @(negedge clock);
        check("CE deasserted: output holds at 0x0C00",
              corrected_phase === 32'h0000_0C00);

        // -------------------------------------------------------
        // Test 4: Negative result (wrapping)
        // -------------------------------------------------------
        // measured < offset => result wraps unsigned (correct for phase arithmetic)
        ce = 1'b1;
        measured_phase    = 32'h0000_0100;
        base_phase_offset = 32'h0000_0400;

        @(posedge clock);
        @(negedge clock);
        check("Wrap: 0x0100 - 0x0400 == 0xFFFF_FD00",
              corrected_phase === 32'hFFFF_FD00);

        // -------------------------------------------------------
        // Test 5: Large positive offset
        // -------------------------------------------------------
        measured_phase    = 32'h8000_0000;
        base_phase_offset = 32'h7FFF_FFFF;

        @(posedge clock);
        @(negedge clock);
        check("Large offset: 0x80000000 - 0x7FFFFFFF == 0x00000001",
              corrected_phase === 32'h0000_0001);

        // -------------------------------------------------------
        // Test 6: Zero offset passthrough
        // -------------------------------------------------------
        measured_phase    = 32'h1234_5678;
        base_phase_offset = 32'h0000_0000;

        @(posedge clock);
        @(negedge clock);
        check("Zero offset: passthrough 0x12345678",
              corrected_phase === 32'h1234_5678);

        // -------------------------------------------------------
        // Test 7: Equal values produce zero
        // -------------------------------------------------------
        measured_phase    = 32'hABCD_EF01;
        base_phase_offset = 32'hABCD_EF01;

        @(posedge clock);
        @(negedge clock);
        check("Equal: same input and offset == 0",
              corrected_phase === 32'h0000_0000);

        // -------------------------------------------------------
        // Test 8: Full-scale wrap-around
        // -------------------------------------------------------
        measured_phase    = 32'h0000_0000;
        base_phase_offset = 32'h0000_0001;

        @(posedge clock);
        @(negedge clock);
        check("Full wrap: 0x0 - 0x1 == 0xFFFFFFFF",
              corrected_phase === 32'hFFFF_FFFF);

        // -------------------------------------------------------
        // Test 9: CE single-pulse update
        // -------------------------------------------------------
        // pulse ce for one cycle with new data, then deassert
        ce = 1'b0;
        measured_phase    = 32'h0000_00FF;
        base_phase_offset = 32'h0000_000F;

        @(posedge clock); // ce=0, no update
        ce = 1'b1;
        @(posedge clock); // ce=1, updates
        ce = 1'b0;
        @(negedge clock);
        check("CE pulse: output updated to 0xF0",
              corrected_phase === 32'h0000_00F0);

        // output holds for several more cycles
        measured_phase    = 32'hFFFF_FFFF;
        base_phase_offset = 32'h0000_0000;
        repeat (5) @(posedge clock);
        @(negedge clock);
        check("CE pulse hold: output still 0xF0",
              corrected_phase === 32'h0000_00F0);

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
