// Testbench for trigger_logic
// Verifies: threshold crossing, modes, edge polarity, GPIO latch, valid gating
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_trigger_logic;

    localparam DATA_WIDTH = 32;
    localparam CLK_PERIOD = 5.0; // 200 MHz

    logic                       clock;
    logic                       reset_n;
    logic [DATA_WIDTH-1:0]      magnitude;
    logic [DATA_WIDTH-1:0]      corrected_phase;
    logic                       data_valid;
    logic [DATA_WIDTH-1:0]      trigger_threshold;
    logic [DATA_WIDTH-1:0]      trigger_config;
    logic                       trigger_flag;
    logic                       gpio_out;

    trigger_logic #(
        .DATA_WIDTH(DATA_WIDTH)
    ) uut (
        .clock             (clock),
        .reset_n           (reset_n),
        .magnitude         (magnitude),
        .corrected_phase   (corrected_phase),
        .data_valid        (data_valid),
        .trigger_threshold (trigger_threshold),
        .trigger_config    (trigger_config),
        .trigger_flag      (trigger_flag),
        .gpio_out          (gpio_out)
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

    // helper: pulse data_valid for one cycle then sample at negedge
    task automatic pulse_valid;
        data_valid = 1'b1;
        @(posedge clock);
        @(negedge clock);
        data_valid = 1'b0;
    endtask

    initial begin
        $display("=== Trigger Logic Testbench ===");

        // initialize
        reset_n           = 1'b0;
        magnitude         = '0;
        corrected_phase   = '0;
        data_valid        = 1'b0;
        trigger_threshold = 32'sd1000;
        trigger_config    = '0; // disabled

        repeat (4) @(posedge clock);

        // -------------------------------------------------------
        // Test 1: Reset state
        // -------------------------------------------------------
        check("Reset: trigger_flag is low", trigger_flag === 1'b0);
        check("Reset: gpio_out is low",     gpio_out === 1'b0);

        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // -------------------------------------------------------
        // Test 2: Disabled mode -- no trigger on crossing
        // -------------------------------------------------------
        trigger_config = 32'h0000_0000; // mode=00 (disabled)
        magnitude = 32'sd500;
        pulse_valid;
        magnitude = 32'sd2000; // crosses above threshold
        pulse_valid;

        // trigger_flag should appear one cycle after the data_valid pulse
        @(posedge clock);
        @(negedge clock);
        check("Disabled: trigger_flag stays low", trigger_flag === 1'b0);

        // -------------------------------------------------------
        // Test 3: Magnitude rising threshold crossing
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0001; // mode=01 (magnitude), edge=0 (rising)
        trigger_threshold = 32'sd1000;

        // establish baseline below threshold
        magnitude = 32'sd500;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Mag rising baseline: trigger_flag low", trigger_flag === 1'b0);

        // cross above threshold
        magnitude = 32'sd1500;
        pulse_valid;
        // trigger flag is a single-cycle pulse that appears after the data_valid cycle
        @(posedge clock);
        @(negedge clock);
        check("Mag rising: trigger_flag asserted", trigger_flag === 1'b1);

        // next cycle: should clear
        @(posedge clock);
        @(negedge clock);
        check("Mag rising: trigger_flag clears next cycle", trigger_flag === 1'b0);

        // -------------------------------------------------------
        // Test 4: GPIO latches on trigger
        // -------------------------------------------------------
        check("GPIO: latched high after trigger", gpio_out === 1'b1);

        // GPIO stays high without reset
        repeat (5) @(posedge clock);
        @(negedge clock);
        check("GPIO: still latched after 5 cycles", gpio_out === 1'b1);

        // -------------------------------------------------------
        // Test 5: Magnitude falling threshold crossing
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0005; // mode=01, edge=1 (falling)

        // start above threshold
        magnitude = 32'sd2000;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Mag falling baseline: trigger_flag low", trigger_flag === 1'b0);

        // drop below threshold
        magnitude = 32'sd500;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Mag falling: trigger_flag asserted", trigger_flag === 1'b1);

        // -------------------------------------------------------
        // Test 6: Phase-only trigger
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0002; // mode=10 (phase), edge=0 (rising)
        magnitude = 32'sd0; // magnitude stays below, should not trigger

        corrected_phase = 32'sd500;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Phase baseline: trigger_flag low", trigger_flag === 1'b0);

        corrected_phase = 32'sd2000;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Phase rising: trigger_flag asserted", trigger_flag === 1'b1);

        // -------------------------------------------------------
        // Test 7: Combined mode (either triggers)
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0003; // mode=11 (either), edge=0 (rising)

        magnitude       = 32'sd500;
        corrected_phase = 32'sd500;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Combined baseline: trigger_flag low", trigger_flag === 1'b0);

        // only magnitude crosses
        magnitude = 32'sd2000;
        corrected_phase = 32'sd500; // phase stays below
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Combined mag-only: trigger_flag asserted", trigger_flag === 1'b1);

        // -------------------------------------------------------
        // Test 8: No false trigger when staying below threshold
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0001; // magnitude rising

        magnitude = 32'sd100;
        pulse_valid;
        magnitude = 32'sd200;
        pulse_valid;
        magnitude = 32'sd300;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);

        check("No false trigger: stays low below threshold", trigger_flag === 1'b0);
        check("No false trigger: GPIO stays low",           gpio_out === 1'b0);

        // -------------------------------------------------------
        // Test 9: No trigger without data_valid
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config = 32'h0000_0001; // magnitude rising

        // set baseline
        magnitude = 32'sd500;
        pulse_valid;
        @(posedge clock);
        @(negedge clock);

        // magnitude crosses but data_valid stays low
        magnitude = 32'sd2000;
        repeat (5) @(posedge clock);
        @(negedge clock);

        check("Valid gating: trigger_flag stays low without data_valid",
              trigger_flag === 1'b0);

        // -------------------------------------------------------
        // Test 10: Negative values with signed comparison
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        trigger_config    = 32'h0000_0001; // magnitude rising
        trigger_threshold = -32'sd500;     // negative threshold

        magnitude = -32'sd1000; // below -500
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Negative baseline: trigger_flag low", trigger_flag === 1'b0);

        magnitude = -32'sd200; // above -500
        pulse_valid;
        @(posedge clock);
        @(negedge clock);
        check("Negative rising: trigger_flag asserted", trigger_flag === 1'b1);

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
