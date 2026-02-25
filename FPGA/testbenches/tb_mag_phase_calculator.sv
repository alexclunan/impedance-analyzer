// Testbench for mag_phase_calculator
// Verifies: I/Q packing, CORDIC output unpacking, CE gating, valid pipeline
// CORDIC IP ports are exposed, so the testbench drives/monitors them directly
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_mag_phase_calculator;

    localparam DATA_WIDTH   = 32;
    localparam CORDIC_WIDTH = 64;
    localparam CLK_PERIOD   = 5.0; // 200 MHz

    logic                       clock;
    logic                       reset_n;
    logic                       ce;
    logic [DATA_WIDTH-1:0]      i_in;
    logic [DATA_WIDTH-1:0]      q_in;
    logic                       valid_in;
    logic [DATA_WIDTH-1:0]      magnitude;
    logic [DATA_WIDTH-1:0]      phase;
    logic                       valid_out;

    // CORDIC IP interface (driven/monitored by testbench)
    logic [CORDIC_WIDTH-1:0]    cordic_s_axis_cartesian_tdata;
    logic                       cordic_s_axis_cartesian_tvalid;
    logic [CORDIC_WIDTH-1:0]    cordic_m_axis_dout_tdata;
    logic                       cordic_m_axis_dout_tvalid;

    mag_phase_calculator #(
        .DATA_WIDTH   (DATA_WIDTH),
        .CORDIC_WIDTH (CORDIC_WIDTH)
    ) uut (
        .clock                          (clock),
        .reset_n                        (reset_n),
        .ce                             (ce),
        .i_in                           (i_in),
        .q_in                           (q_in),
        .valid_in                       (valid_in),
        .magnitude                      (magnitude),
        .phase                          (phase),
        .valid_out                      (valid_out),
        .cordic_s_axis_cartesian_tdata  (cordic_s_axis_cartesian_tdata),
        .cordic_s_axis_cartesian_tvalid (cordic_s_axis_cartesian_tvalid),
        .cordic_m_axis_dout_tdata       (cordic_m_axis_dout_tdata),
        .cordic_m_axis_dout_tvalid      (cordic_m_axis_dout_tvalid)
    );

    // Clock generation
    initial clock = 1'b0;
    always #(CLK_PERIOD / 2.0) clock = ~clock;

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
        $display("=== Magnitude/Phase Calculator Testbench ===");
        $display("DATA_WIDTH: %0d, CORDIC_WIDTH: %0d", DATA_WIDTH, CORDIC_WIDTH);

        // initialize
        reset_n  = 1'b0;
        ce       = 1'b0;
        i_in     = '0;
        q_in     = '0;
        valid_in = 1'b0;
        cordic_m_axis_dout_tdata  = '0;
        cordic_m_axis_dout_tvalid = 1'b0;

        repeat (4) @(posedge clock);

        // -------------------------------------------------------
        // Test 1: Reset clears all outputs
        // -------------------------------------------------------
        check("Reset: CORDIC tvalid is low",
              cordic_s_axis_cartesian_tvalid === 1'b0);
        check("Reset: CORDIC tdata is zero",
              cordic_s_axis_cartesian_tdata === '0);
        check("Reset: magnitude is zero",   magnitude === '0);
        check("Reset: phase is zero",       phase === '0);
        check("Reset: valid_out is low",    valid_out === 1'b0);

        // -------------------------------------------------------
        // Test 2: I/Q packing format (I=X in lower, Q=Y in upper)
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        i_in     = 32'hAAAA_BBBB;
        q_in     = 32'hCCCC_DDDD;
        valid_in = 1'b1;
        ce       = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Packing: lower 32 bits == I (0xAAAA_BBBB)",
              cordic_s_axis_cartesian_tdata[31:0] === 32'hAAAA_BBBB);
        check("Packing: upper 32 bits == Q (0xCCCC_DDDD)",
              cordic_s_axis_cartesian_tdata[63:32] === 32'hCCCC_DDDD);
        check("Packing: tvalid asserted",
              cordic_s_axis_cartesian_tvalid === 1'b1);

        // -------------------------------------------------------
        // Test 3: CE gating -- tvalid deasserts when ce is low
        // -------------------------------------------------------
        ce = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("CE gate: tvalid low when ce deasserted",
              cordic_s_axis_cartesian_tvalid === 1'b0);

        // data should remain latched (registered)
        check("CE gate: tdata holds previous value",
              cordic_s_axis_cartesian_tdata[31:0] === 32'hAAAA_BBBB);

        // -------------------------------------------------------
        // Test 4: valid_in gating -- tvalid follows valid_in when ce high
        // -------------------------------------------------------
        ce       = 1'b1;
        valid_in = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("valid_in gate: tvalid low when valid_in deasserted",
              cordic_s_axis_cartesian_tvalid === 1'b0);

        valid_in = 1'b1;
        @(posedge clock);
        @(negedge clock);
        check("valid_in gate: tvalid high when valid_in reasserted",
              cordic_s_axis_cartesian_tvalid === 1'b1);

        // -------------------------------------------------------
        // Test 5: CORDIC output unpacking -- magnitude and phase
        // -------------------------------------------------------
        cordic_m_axis_dout_tdata  = {32'h3243_F6A9, 32'h0000_7FFF};
        cordic_m_axis_dout_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Unpack: magnitude == 0x0000_7FFF (lower 32 bits)",
              magnitude === 32'h0000_7FFF);
        check("Unpack: phase == 0x3243_F6A9 (upper 32 bits)",
              phase === 32'h3243_F6A9);
        check("Unpack: valid_out asserted",
              valid_out === 1'b1);

        // -------------------------------------------------------
        // Test 6: valid_out follows CORDIC output valid
        // -------------------------------------------------------
        cordic_m_axis_dout_tvalid = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("valid_out: deasserts when CORDIC invalid",
              valid_out === 1'b0);

        cordic_m_axis_dout_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("valid_out: reasserts when CORDIC valid",
              valid_out === 1'b1);

        // -------------------------------------------------------
        // Test 7: Multiple sequential I/Q values
        // -------------------------------------------------------
        ce       = 1'b1;
        valid_in = 1'b1;

        i_in = 32'h0000_0001;
        q_in = 32'h0000_0000;

        @(posedge clock);
        @(negedge clock);
        check("Seq 1: I=1 Q=0 packed correctly",
              cordic_s_axis_cartesian_tdata === {32'h0000_0000, 32'h0000_0001});

        i_in = 32'h0000_0000;
        q_in = 32'h0000_0001;

        @(posedge clock);
        @(negedge clock);
        check("Seq 2: I=0 Q=1 packed correctly",
              cordic_s_axis_cartesian_tdata === {32'h0000_0001, 32'h0000_0000});

        i_in = 32'hFFFF_FFFF;
        q_in = 32'hFFFF_FFFF;

        @(posedge clock);
        @(negedge clock);
        check("Seq 3: I=-1 Q=-1 packed correctly",
              cordic_s_axis_cartesian_tdata === {32'hFFFF_FFFF, 32'hFFFF_FFFF});

        // -------------------------------------------------------
        // Test 8: Reset mid-operation clears outputs
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);

        check("Mid-reset: CORDIC tvalid cleared",
              cordic_s_axis_cartesian_tvalid === 1'b0);
        check("Mid-reset: magnitude cleared",  magnitude === '0);
        check("Mid-reset: phase cleared",      phase === '0);
        check("Mid-reset: valid_out cleared",  valid_out === 1'b0);

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
