// Testbench for phase_accumulator_slave
// Verifies: baseline accumulation, +1/-1 correction, integration with master + synchronizer
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_phase_accumulator_slave;

    localparam ACCUM_WIDTH = 48;
    localparam PHASE_WIDTH = 16;
    localparam CLK_PERIOD  = 5.0; // 200 MHz

    logic                       clock;
    logic                       reset_n;
    logic [ACCUM_WIDTH-1:0]     fcw;
    logic [1:0]                 correction;
    logic [PHASE_WIDTH-1:0]     phase_out;
    logic                       phase_msb;

    phase_accumulator_slave #(
        .ACCUM_WIDTH(ACCUM_WIDTH),
        .PHASE_WIDTH(PHASE_WIDTH)
    ) uut (
        .clock      (clock),
        .reset_n    (reset_n),
        .fcw        (fcw),
        .correction (correction),
        .phase_out  (phase_out),
        .phase_msb  (phase_msb)
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

    // -------------------------------------------------------
    // Integration test infrastructure (module-level)
    // -------------------------------------------------------
    localparam INT_CLK_PERIOD = 5.0; // same frequency, different phase
    localparam ADC_PHASE_OFFSET = 1.3; // ns offset to make clocks async

    logic int_dac_clock, int_adc_clock, int_reset_n;
    logic [ACCUM_WIDTH-1:0] int_fcw;
    logic [PHASE_WIDTH-1:0] int_master_phase, int_slave_phase;
    logic int_master_msb, int_slave_msb;
    logic int_synced_msb;
    logic [ACCUM_WIDTH-1:0] int_synced_fcw;
    logic [1:0] int_correction;

    initial int_dac_clock = 1'b0;
    always #(INT_CLK_PERIOD / 2.0) int_dac_clock = ~int_dac_clock;

    initial begin
        int_adc_clock = 1'b0;
        #(ADC_PHASE_OFFSET);
        forever #(INT_CLK_PERIOD / 2.0) int_adc_clock = ~int_adc_clock;
    end

    phase_accumulator #(
        .ACCUM_WIDTH(ACCUM_WIDTH),
        .PHASE_WIDTH(PHASE_WIDTH)
    ) master (
        .clock     (int_dac_clock),
        .reset_n   (int_reset_n),
        .fcw       (int_fcw),
        .phase_out (int_master_phase),
        .phase_msb (int_master_msb)
    );

    phase_synchronizer #(
        .FCW_WIDTH(ACCUM_WIDTH)
    ) sync (
        .dac_clock        (int_dac_clock),
        .adc_clock        (int_adc_clock),
        .reset_n          (int_reset_n),
        .dac_phase_msb    (int_master_msb),
        .slave_phase_msb  (int_slave_msb),
        .fcw              (int_fcw),
        .synced_phase_msb (int_synced_msb),
        .synced_fcw       (int_synced_fcw),
        .correction       (int_correction)
    );

    phase_accumulator_slave #(
        .ACCUM_WIDTH(ACCUM_WIDTH),
        .PHASE_WIDTH(PHASE_WIDTH)
    ) slave (
        .clock      (int_adc_clock),
        .reset_n    (int_reset_n),
        .fcw        (int_synced_fcw),
        .correction (int_correction),
        .phase_out  (int_slave_phase),
        .phase_msb  (int_slave_msb)
    );

    initial begin
        $display("=== Phase Accumulator Slave Testbench ===");
        $display("Accumulator width: %0d, Phase width: %0d", ACCUM_WIDTH, PHASE_WIDTH);

        // hold integration test in reset until Test 6
        int_reset_n = 1'b0;
        int_fcw     = '0;

        // -------------------------------------------------------
        // Test 1: Reset clears accumulator
        // -------------------------------------------------------
        reset_n    = 1'b0;
        fcw        = '0;
        correction = 2'b00;
        repeat (4) @(posedge clock);

        check("Reset: phase_out is zero", phase_out === '0);
        check("Reset: phase_msb is zero", phase_msb === 1'b0);

        // -------------------------------------------------------
        // Test 2: Without correction, behaves identically to master
        // -------------------------------------------------------
        fcw = 48'h0001_0000_0000;
        correction = 2'b00;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        repeat (10) @(posedge clock);
        @(negedge clock);
        check("No correction: phase_out == 10 after 10 cycles (same as master)",
              phase_out === 16'd10);

        // -------------------------------------------------------
        // Test 3: +1 correction advances phase by 1 extra LSB
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'h0001_0000_0000;
        correction = 2'b00;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // run 5 cycles without correction
        repeat (5) @(posedge clock);
        @(negedge clock);
        check("+1 setup: phase_out == 5 before correction",
              phase_out === 16'd5);

        // apply +1 correction for 1 cycle
        correction = 2'b01;
        @(posedge clock);
        correction = 2'b00;
        @(negedge clock);

        // accumulated = 5*FCW + FCW + 1 = 6*FCW + 1
        // phase_out = 6 (the +1 is in the accumulator LSB, below phase_out bits)
        check("+1 correction: phase_out == 6 after correction cycle",
              phase_out === 16'd6);

        // run 4 more cycles
        repeat (4) @(posedge clock);
        @(negedge clock);
        check("+1 aftermath: phase_out == 10 after 4 more cycles",
              phase_out === 16'd10);

        // -------------------------------------------------------
        // Test 4: -1 correction slows phase by 1 LSB
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'h0001_0000_0000;
        correction = 2'b00;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // run 5 cycles without correction
        repeat (5) @(posedge clock);
        @(negedge clock);
        check("-1 setup: phase_out == 5 before correction",
              phase_out === 16'd5);

        // apply -1 correction (2'b11) for 1 cycle
        correction = 2'b11;
        @(posedge clock);
        correction = 2'b00;
        @(negedge clock);

        // accumulated = 5*FCW + (FCW - 1) = 5*FCW + 0x0000_FFFF_FFFF
        // = 0x0005_FFFF_FFFF, phase_out = bits[47:32] = 5
        // the -1 makes the total increment 0x0000_FFFF_FFFF (upper 16 bits = 0)
        check("-1 correction: phase_out == 5 (increment upper bits == 0 this cycle)",
              phase_out === 16'd5);

        // -------------------------------------------------------
        // Test 5: Multiple consecutive corrections accumulate
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        fcw = 48'h0001_0000_0000;
        correction = 2'b00;
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // apply +1 every cycle for 10 cycles
        correction = 2'b01;
        repeat (10) @(posedge clock);
        correction = 2'b00;
        @(negedge clock);

        // accumulated = 10*(FCW + 1) = 10*FCW + 10
        // phase_out = 10 (the +10 is below phase_out bits)
        check("Multi +1: phase_out == 10 after 10 cycles with +1 each",
              phase_out === 16'd10);

        // -------------------------------------------------------
        // Test 6: Integration - master + synchronizer + slave
        // -------------------------------------------------------
        // The slave has a constant phase offset from the master due to
        // the FCW registration delay (synced_fcw takes 1 ADC cycle to
        // propagate). This offset is by design -- the Phase Adjuster
        // (Section 4.13) compensates for it in the real system.
        // This test verifies the offset is STABLE (slave tracks master
        // at the same rate) rather than expecting zero offset.
        $display("--- Integration Test: Master + Synchronizer + Slave ---");

        int_fcw = 48'h0080_0000_0000;
        repeat (10) @(posedge int_adc_clock);
        @(posedge int_adc_clock);
        @(negedge int_adc_clock);
        int_reset_n = 1'b1;

        // let the system settle
        repeat (1000) @(posedge int_adc_clock);

        begin
            integer diff_early, diff_late, drift;

            // sample phase difference at first checkpoint
            @(negedge int_adc_clock);
            diff_early = $signed({1'b0, int_master_phase}) -
                         $signed({1'b0, int_slave_phase});

            $display("  Early - Master: 0x%04h, Slave: 0x%04h, Diff: %0d",
                     int_master_phase, int_slave_phase, diff_early);

            // run 1000 more cycles
            repeat (1000) @(posedge int_adc_clock);

            // sample phase difference at second checkpoint
            @(negedge int_adc_clock);
            diff_late = $signed({1'b0, int_master_phase}) -
                        $signed({1'b0, int_slave_phase});

            $display("  Late  - Master: 0x%04h, Slave: 0x%04h, Diff: %0d",
                     int_master_phase, int_slave_phase, diff_late);

            // drift = change in offset between the two checkpoints
            drift = diff_late - diff_early;
            if (drift < 0) drift = -drift;

            $display("  Drift between checkpoints: %0d phase_out counts", drift);

            check("Integration: offset is stable (drift < 4 between checkpoints)",
                  drift < 4);

            // sanity check: offset should be reasonable (within ~2x FCW/2^32)
            begin
                integer abs_diff;
                abs_diff = diff_late;
                if (abs_diff < 0) abs_diff = -abs_diff;
                check("Integration: absolute offset within expected range",
                      abs_diff < 300);
            end
        end

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
