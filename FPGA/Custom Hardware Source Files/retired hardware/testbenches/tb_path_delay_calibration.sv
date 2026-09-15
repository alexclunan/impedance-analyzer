// Testbench for path_delay_calibration
// Verifies: step generation, timestamp capture, threshold detection, known delay
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_path_delay_calibration;

    localparam DATA_WIDTH      = 16;
    localparam TIMESTAMP_WIDTH = 64;
    localparam SETTLE_CYCLES   = 10; // reduced for simulation speed
    localparam CLK_PERIOD      = 5.0; // 200 MHz

    localparam [DATA_WIDTH-1:0] MID_SCALE  = {DATA_WIDTH{1'b0}};
    localparam [DATA_WIDTH-1:0] FULL_SCALE = {1'b0, {(DATA_WIDTH-1){1'b1}}};

    // DAC domain signals
    logic                       dac_clock;
    logic                       reset_n;
    logic                       calibration_start;
    logic [TIMESTAMP_WIDTH-1:0] dac_timestamp;
    logic [DATA_WIDTH-1:0]      test_pulse_data;
    logic                       test_mode;
    logic [TIMESTAMP_WIDTH-1:0] tx_timestamp;
    logic                       tx_timestamp_valid;

    // ADC domain signals
    logic                       adc_clock;
    logic                       calibration_armed;
    logic [DATA_WIDTH-1:0]      adc_sample;
    logic [DATA_WIDTH-1:0]      threshold;
    logic [TIMESTAMP_WIDTH-1:0] adc_timestamp;
    logic [TIMESTAMP_WIDTH-1:0] rx_timestamp;
    logic                       rx_timestamp_valid;

    path_delay_calibration #(
        .DATA_WIDTH     (DATA_WIDTH),
        .TIMESTAMP_WIDTH(TIMESTAMP_WIDTH),
        .SETTLE_CYCLES  (SETTLE_CYCLES)
    ) uut (
        .dac_clock          (dac_clock),
        .reset_n            (reset_n),
        .calibration_start  (calibration_start),
        .dac_timestamp      (dac_timestamp),
        .test_pulse_data    (test_pulse_data),
        .test_mode          (test_mode),
        .tx_timestamp       (tx_timestamp),
        .tx_timestamp_valid (tx_timestamp_valid),
        .adc_clock          (adc_clock),
        .calibration_armed  (calibration_armed),
        .adc_sample         (adc_sample),
        .threshold          (threshold),
        .adc_timestamp      (adc_timestamp),
        .rx_timestamp       (rx_timestamp),
        .rx_timestamp_valid (rx_timestamp_valid)
    );

    // Clock generation (same frequency for deterministic delay testing)
    initial dac_clock = 1'b0;
    always #(CLK_PERIOD / 2.0) dac_clock = ~dac_clock;

    initial adc_clock = 1'b0;
    always #(CLK_PERIOD / 2.0) adc_clock = ~adc_clock;

    // Simple timestamp counters for both domains
    always @(posedge dac_clock or negedge reset_n) begin
        if (!reset_n) dac_timestamp <= '0;
        else          dac_timestamp <= dac_timestamp + 1;
    end

    always @(posedge adc_clock or negedge reset_n) begin
        if (!reset_n) adc_timestamp <= '0;
        else          adc_timestamp <= adc_timestamp + 1;
    end

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
        $display("=== Path Delay Calibration Testbench ===");
        $display("SETTLE_CYCLES: %0d", SETTLE_CYCLES);

        // initialize
        reset_n           = 1'b0;
        calibration_start = 1'b0;
        calibration_armed = 1'b0;
        adc_sample        = 16'sh0000;
        threshold         = 16'sh3FFF;

        repeat (4) @(posedge dac_clock);

        // -------------------------------------------------------
        // Test 1: Reset state
        // -------------------------------------------------------
        check("Reset: test_mode is low",           test_mode === 1'b0);
        check("Reset: test_pulse_data is mid-scale", test_pulse_data === MID_SCALE);
        check("Reset: tx_timestamp_valid is low",   tx_timestamp_valid === 1'b0);
        check("Reset: rx_timestamp_valid is low",   rx_timestamp_valid === 1'b0);

        // -------------------------------------------------------
        // Test 2: Step generator settling phase
        // -------------------------------------------------------
        @(posedge dac_clock);
        @(negedge dac_clock);
        reset_n = 1'b1;

        // start calibration
        @(posedge dac_clock);
        @(negedge dac_clock);
        calibration_start = 1'b1;

        // after one cycle, should be in settling mode
        @(posedge dac_clock);
        @(negedge dac_clock);
        check("Settle: test_mode asserted",            test_mode === 1'b1);
        check("Settle: test_pulse_data is mid-scale",  test_pulse_data === MID_SCALE);
        check("Settle: tx_timestamp_valid still low",  tx_timestamp_valid === 1'b0);

        // -------------------------------------------------------
        // Test 3: Step transition after settling
        // -------------------------------------------------------
        // settle_count starts at 0 on entry; needs SETTLE_CYCLES posedges to reach
        // the comparison (settle_count >= SETTLE_CYCLES-1) and one more for the
        // non-blocking output update to be visible
        repeat (SETTLE_CYCLES) @(posedge dac_clock);
        @(negedge dac_clock);

        check("Step: test_pulse_data is full-scale",   test_pulse_data === FULL_SCALE);
        check("Step: tx_timestamp_valid asserted",     tx_timestamp_valid === 1'b1);
        check("Step: test_mode still asserted",        test_mode === 1'b1);

        // -------------------------------------------------------
        // Test 4: tx_timestamp captured at step edge
        // -------------------------------------------------------
        begin
            logic [TIMESTAMP_WIDTH-1:0] captured_tx;
            captured_tx = tx_timestamp;
            check("TX capture: tx_timestamp is non-zero",  captured_tx !== '0);
        end

        // -------------------------------------------------------
        // Test 5: Threshold detector with known delay
        // -------------------------------------------------------
        begin
            integer delay_cycles;
            logic [TIMESTAMP_WIDTH-1:0] saved_tx, saved_rx;
            integer measured_delay;

            delay_cycles = 20;
            saved_tx = tx_timestamp;

            // arm the detector
            calibration_armed = 1'b1;

            // simulate ADC seeing the step after delay_cycles
            repeat (delay_cycles) @(posedge adc_clock);
            @(negedge adc_clock);

            // verify not yet triggered (sample still below threshold)
            check("Delay: rx_timestamp_valid still low before crossing",
                  rx_timestamp_valid === 1'b0);

            // ADC sample crosses threshold
            adc_sample = 16'sh7FFF;

            @(posedge adc_clock);
            @(negedge adc_clock);
            check("Threshold: rx_timestamp_valid asserted",
                  rx_timestamp_valid === 1'b1);

            saved_rx = rx_timestamp;
            measured_delay = $signed(saved_rx) - $signed(saved_tx);
            $display("  TX timestamp: %0d, RX timestamp: %0d, Measured delay: %0d cycles",
                     saved_tx, saved_rx, measured_delay);
            check("Delay: measured delay is positive",
                  measured_delay > 0);
        end

        // -------------------------------------------------------
        // Test 6: Detector does not re-trigger while armed
        // -------------------------------------------------------
        begin
            logic [TIMESTAMP_WIDTH-1:0] first_rx;
            first_rx = rx_timestamp;

            adc_sample = 16'sh0000;
            @(posedge adc_clock);
            adc_sample = 16'sh7FFF;
            @(posedge adc_clock);
            @(negedge adc_clock);

            check("No re-trigger: rx_timestamp unchanged",
                  rx_timestamp === first_rx);
        end

        // -------------------------------------------------------
        // Test 7: Disarming clears rx_valid, allows re-arm
        // -------------------------------------------------------
        calibration_armed = 1'b0;
        @(posedge adc_clock);
        @(negedge adc_clock);
        check("Disarm: rx_timestamp_valid cleared",
              rx_timestamp_valid === 1'b0);

        // re-arm with sample already above threshold
        adc_sample = 16'sh7FFF;
        calibration_armed = 1'b1;
        @(posedge adc_clock);
        @(negedge adc_clock);
        check("Re-arm: rx_timestamp_valid re-triggers on armed sample",
              rx_timestamp_valid === 1'b1);

        // -------------------------------------------------------
        // Test 8: calibration_start deassert returns to IDLE
        // -------------------------------------------------------
        calibration_armed = 1'b0;
        calibration_start = 1'b0;
        // first posedge: STEPPED sees cal_start=0, transitions to IDLE (outputs still STEPPED)
        // second posedge: IDLE applies its assignments (mid-scale, test_mode=0)
        repeat (2) @(posedge dac_clock);
        @(negedge dac_clock);

        check("Deassert: test_mode returns low",       test_mode === 1'b0);
        check("Deassert: test_pulse_data is mid-scale", test_pulse_data === MID_SCALE);

        // -------------------------------------------------------
        // Test 9: Sub-threshold sample does not trigger
        // -------------------------------------------------------
        adc_sample = 16'sh1000; // below threshold (0x3FFF)
        calibration_armed = 1'b1;
        repeat (10) @(posedge adc_clock);
        @(negedge adc_clock);
        check("Sub-threshold: rx_timestamp_valid stays low",
              rx_timestamp_valid === 1'b0);

        calibration_armed = 1'b0;

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
