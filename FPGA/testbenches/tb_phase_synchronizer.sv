// Testbench for phase_synchronizer
// Verifies: CDC transfer, edge detection, correction output, FCW registration
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_phase_synchronizer;

    localparam FCW_WIDTH      = 48;
    localparam DAC_CLK_PERIOD = 5.0;    // 200 MHz
    localparam ADC_CLK_PERIOD = 5.008;  // ~199.68 MHz (slightly slower, async)

    logic                   dac_clock;
    logic                   adc_clock;
    logic                   reset_n;
    logic                   dac_phase_msb;
    logic                   slave_phase_msb;
    logic [FCW_WIDTH-1:0]   fcw;
    logic                   synced_phase_msb;
    logic [FCW_WIDTH-1:0]   synced_fcw;
    logic [1:0]             correction;

    phase_synchronizer #(
        .FCW_WIDTH(FCW_WIDTH)
    ) uut (
        .dac_clock        (dac_clock),
        .adc_clock        (adc_clock),
        .reset_n          (reset_n),
        .dac_phase_msb    (dac_phase_msb),
        .slave_phase_msb  (slave_phase_msb),
        .fcw              (fcw),
        .synced_phase_msb (synced_phase_msb),
        .synced_fcw       (synced_fcw),
        .correction       (correction)
    );

    // Independent clock generators (async relationship)
    initial dac_clock = 1'b0;
    always #(DAC_CLK_PERIOD / 2.0) dac_clock = ~dac_clock;

    initial adc_clock = 1'b0;
    always #(ADC_CLK_PERIOD / 2.0) adc_clock = ~adc_clock;

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
        $display("=== Phase Synchronizer Testbench ===");
        $display("DAC clock period: %0.3f ns, ADC clock period: %0.3f ns",
                 DAC_CLK_PERIOD, ADC_CLK_PERIOD);

        // -------------------------------------------------------
        // Test 1: Reset clears all outputs
        // -------------------------------------------------------
        reset_n        = 1'b0;
        dac_phase_msb  = 1'b0;
        slave_phase_msb = 1'b0;
        fcw            = '0;
        repeat (4) @(posedge adc_clock);

        check("Reset: synced_phase_msb is zero", synced_phase_msb === 1'b0);
        check("Reset: correction is zero",       correction === 2'b00);
        check("Reset: synced_fcw is zero",        synced_fcw === '0);

        // -------------------------------------------------------
        // Test 2: MSB transition propagates through double-flop
        // -------------------------------------------------------
        @(posedge adc_clock);
        @(negedge adc_clock);
        reset_n = 1'b1;

        // wait a few cycles for reset to settle
        repeat (4) @(posedge adc_clock);

        // toggle master MSB in DAC domain
        @(posedge dac_clock);
        dac_phase_msb = 1'b1;

        // synced_phase_msb should appear within 4 ADC cycles
        // (1 DAC reg + 2 double-flop = 3 pipeline stages, plus clock alignment)
        repeat (5) @(posedge adc_clock);
        @(negedge adc_clock);
        check("CDC: synced_phase_msb == 1 after master MSB transition",
              synced_phase_msb === 1'b1);

        // -------------------------------------------------------
        // Test 3: Correction is non-zero when slave disagrees
        // -------------------------------------------------------
        // reset and set up a controlled scenario
        reset_n = 1'b0;
        dac_phase_msb   = 1'b0;
        slave_phase_msb = 1'b0;
        repeat (4) @(posedge adc_clock);
        @(posedge adc_clock);
        @(negedge adc_clock);
        reset_n = 1'b1;
        repeat (4) @(posedge adc_clock);

        // master MSB transitions to 1 but slave stays at 0
        @(posedge dac_clock);
        dac_phase_msb = 1'b1;
        slave_phase_msb = 1'b0;

        // correction is a single-cycle pulse; monitor each cycle in the window
        begin : correction_disagree_test
            logic saw_correction;
            integer cyc;
            saw_correction = 1'b0;
            for (cyc = 0; cyc < 8; cyc++) begin
                @(posedge adc_clock);
                @(negedge adc_clock);
                if (correction === 2'b01)
                    saw_correction = 1'b1;
            end
            check("Correction: non-zero when slave MSB disagrees with synced master MSB",
                  saw_correction === 1'b1);
        end

        // -------------------------------------------------------
        // Test 4: Correction is zero when slave agrees
        // -------------------------------------------------------
        reset_n = 1'b0;
        dac_phase_msb   = 1'b0;
        slave_phase_msb = 1'b0;
        repeat (4) @(posedge adc_clock);
        @(posedge adc_clock);
        @(negedge adc_clock);
        reset_n = 1'b1;
        repeat (4) @(posedge adc_clock);

        // master MSB transitions to 1 and slave also at 1
        @(posedge dac_clock);
        dac_phase_msb = 1'b1;
        slave_phase_msb = 1'b1;

        // monitor full window to confirm correction never fires when aligned
        begin : correction_agree_test
            logic saw_correction;
            integer cyc;
            saw_correction = 1'b0;
            for (cyc = 0; cyc < 8; cyc++) begin
                @(posedge adc_clock);
                @(negedge adc_clock);
                if (correction !== 2'b00)
                    saw_correction = 1'b1;
            end
            check("Correction: zero when slave MSB agrees with synced master MSB",
                  saw_correction === 1'b0);
        end

        // -------------------------------------------------------
        // Test 5: Correction returns to zero after single-cycle pulse
        // -------------------------------------------------------
        // after the previous edge, with no new edges, correction should be 0
        repeat (4) @(posedge adc_clock);
        @(negedge adc_clock);
        check("Correction: returns to zero when no edge detected",
              correction === 2'b00);

        // -------------------------------------------------------
        // Test 6: FCW registered into ADC domain
        // -------------------------------------------------------
        reset_n = 1'b0;
        fcw = 48'hAAAA_5555_1234;
        repeat (4) @(posedge adc_clock);
        @(posedge adc_clock);
        @(negedge adc_clock);
        reset_n = 1'b1;

        // FCW needs a few ADC cycles to propagate through the register
        repeat (4) @(posedge adc_clock);
        @(negedge adc_clock);
        check("FCW: synced_fcw matches input after registration",
              synced_fcw === 48'hAAAA_5555_1234);

        // -------------------------------------------------------
        // Test 7: Multiple MSB transitions with async clocks
        // -------------------------------------------------------
        reset_n = 1'b0;
        dac_phase_msb   = 1'b0;
        slave_phase_msb = 1'b0;
        repeat (4) @(posedge adc_clock);
        @(posedge adc_clock);
        @(negedge adc_clock);
        reset_n = 1'b1;
        repeat (4) @(posedge adc_clock);

        // toggle master MSB several times, verify synced output follows
        begin : multi_toggle_test
            integer i;
            logic expected_msb;
            logic all_passed;
            all_passed = 1'b1;
            expected_msb = 1'b0;

            for (i = 0; i < 10; i++) begin
                @(posedge dac_clock);
                expected_msb = ~expected_msb;
                dac_phase_msb = expected_msb;
                slave_phase_msb = expected_msb;

                repeat (6) @(posedge adc_clock);
                @(negedge adc_clock);

                if (synced_phase_msb !== expected_msb) begin
                    $error("FAIL: Multi-toggle iteration %0d: expected %b, got %b",
                           i, expected_msb, synced_phase_msb);
                    errors++;
                    all_passed = 1'b0;
                end
            end

            if (all_passed)
                $display("PASS: Multi-toggle: 10 MSB transitions all propagated correctly");
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
