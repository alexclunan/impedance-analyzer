// Testbench for state_machine
// Verifies: state transitions, pipeline control, calibration sequence, invalid commands
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_state_machine;

    localparam CLK_PERIOD = 5.0; // 200 MHz

    // state encoding (must match RTL)
    localparam [3:0] STATE_IDLE         = 4'd0;
    localparam [3:0] STATE_CONFIGURE    = 4'd1;
    localparam [3:0] STATE_STARTUP_CIC  = 4'd2;
    localparam [3:0] STATE_STARTUP_FIR  = 4'd3;
    localparam [3:0] STATE_RUN          = 4'd4;
    localparam [3:0] STATE_STOP         = 4'd5;
    localparam [3:0] STATE_CAL_START    = 4'd6;
    localparam [3:0] STATE_CAL_ARM      = 4'd7;
    localparam [3:0] STATE_CAL_DONE     = 4'd8;

    // command encoding
    localparam [3:0] CMD_NOP       = 4'd0;
    localparam [3:0] CMD_CONFIGURE = 4'd1;
    localparam [3:0] CMD_START     = 4'd2;
    localparam [3:0] CMD_STOP      = 4'd3;
    localparam [3:0] CMD_CALIBRATE = 4'd4;

    logic                   clock;
    logic                   reset_n;
    logic [31:0]            state_machine_ctrl;
    logic [31:0]            state_machine_status;
    logic                   pipeline_reset_n;
    logic                   processing_enable;
    logic                   cic_config_load;
    logic                   fir_reload_done;
    logic                   calibration_start;
    logic                   calibration_armed;
    logic                   tx_timestamp_valid;
    logic                   rx_timestamp_valid;

    state_machine uut (
        .clock                (clock),
        .reset_n              (reset_n),
        .state_machine_ctrl   (state_machine_ctrl),
        .state_machine_status (state_machine_status),
        .pipeline_reset_n     (pipeline_reset_n),
        .processing_enable    (processing_enable),
        .cic_config_load      (cic_config_load),
        .fir_reload_done      (fir_reload_done),
        .calibration_start    (calibration_start),
        .calibration_armed    (calibration_armed),
        .tx_timestamp_valid   (tx_timestamp_valid),
        .rx_timestamp_valid   (rx_timestamp_valid)
    );

    // Clock generation
    initial clock = 1'b0;
    always #(CLK_PERIOD / 2.0) clock = ~clock;

    // extract current state from status register
    wire [3:0] current_state = state_machine_status[3:0];

    integer errors = 0;

    task automatic check(input string msg, input logic condition);
        if (!condition) begin
            $error("FAIL: %s", msg);
            errors++;
        end else begin
            $display("PASS: %s", msg);
        end
    endtask

    // helper: issue command, wait for it to be latched, then return to NOP
    task automatic issue_cmd(input logic [3:0] cmd);
        state_machine_ctrl = {28'b0, cmd};
        @(posedge clock);
        @(negedge clock);
        state_machine_ctrl = {28'b0, CMD_NOP};
    endtask

    initial begin
        $display("=== State Machine Testbench ===");

        // initialize
        reset_n              = 1'b0;
        state_machine_ctrl   = '0;
        fir_reload_done      = 1'b0;
        tx_timestamp_valid   = 1'b0;
        rx_timestamp_valid   = 1'b0;

        repeat (4) @(posedge clock);

        // -------------------------------------------------------
        // Test 1: Reset to IDLE
        // -------------------------------------------------------
        check("Reset: state is IDLE",              current_state === STATE_IDLE);
        check("Reset: pipeline_reset_n is low",    pipeline_reset_n === 1'b0);
        check("Reset: processing_enable is low",   processing_enable === 1'b0);
        check("Reset: calibration_start is low",   calibration_start === 1'b0);

        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        // -------------------------------------------------------
        // Test 2: IDLE -> CONFIGURE
        // -------------------------------------------------------
        issue_cmd(CMD_CONFIGURE);
        @(posedge clock);
        @(negedge clock);
        check("Configure: state is CONFIGURE",       current_state === STATE_CONFIGURE);
        check("Configure: pipeline_reset_n is low",  pipeline_reset_n === 1'b0);
        check("Configure: processing_enable is low", processing_enable === 1'b0);

        // -------------------------------------------------------
        // Test 3: CONFIGURE -> STARTUP_CIC (CMD_START triggers CIC config)
        // -------------------------------------------------------
        issue_cmd(CMD_START);

        // CIC config load should have been pulsed
        // (the pulse happens on the transition cycle)
        check("Startup CIC: state is STARTUP_CIC or beyond",
              current_state === STATE_STARTUP_CIC ||
              current_state === STATE_STARTUP_FIR);

        // -------------------------------------------------------
        // Test 4: STARTUP_CIC -> STARTUP_FIR (automatic after 1 cycle)
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        check("Startup FIR: state is STARTUP_FIR",   current_state === STATE_STARTUP_FIR);
        check("Startup FIR: pipeline still in reset", pipeline_reset_n === 1'b0);

        // -------------------------------------------------------
        // Test 5: STARTUP_FIR -> RUN (on fir_reload_done)
        // -------------------------------------------------------
        fir_reload_done = 1'b1;
        @(posedge clock);
        @(negedge clock);
        check("Run: state is RUN",                current_state === STATE_RUN);
        check("Run: pipeline_reset_n is high",     pipeline_reset_n === 1'b1);
        check("Run: processing_enable is high",    processing_enable === 1'b1);
        fir_reload_done = 1'b0;

        // verify pipeline stays active
        repeat (3) @(posedge clock);
        @(negedge clock);
        check("Run stable: pipeline_reset_n still high", pipeline_reset_n === 1'b1);
        check("Run stable: processing_enable still high", processing_enable === 1'b1);

        // -------------------------------------------------------
        // Test 6: RUN -> STOP -> IDLE
        // -------------------------------------------------------
        issue_cmd(CMD_STOP);
        @(posedge clock);
        @(negedge clock);
        // STOP transitions to IDLE after one cycle
        check("Stop: state is STOP or IDLE",
              current_state === STATE_STOP || current_state === STATE_IDLE);
        check("Stop: pipeline_reset_n is low",    pipeline_reset_n === 1'b0);
        check("Stop: processing_enable is low",   processing_enable === 1'b0);

        @(posedge clock);
        @(negedge clock);
        check("Back to IDLE: state is IDLE",       current_state === STATE_IDLE);

        // -------------------------------------------------------
        // Test 7: Calibration sequence
        // -------------------------------------------------------
        issue_cmd(CMD_CALIBRATE);
        @(posedge clock);
        @(negedge clock);
        check("Cal start: state is CAL_START",        current_state === STATE_CAL_START);
        check("Cal start: calibration_start asserted", calibration_start === 1'b1);
        check("Cal start: pipeline in reset",          pipeline_reset_n === 1'b0);

        // simulate tx_timestamp_valid from step generator
        tx_timestamp_valid = 1'b1;
        @(posedge clock);
        @(negedge clock);
        check("Cal arm: state is CAL_ARM",            current_state === STATE_CAL_ARM);
        check("Cal arm: calibration_armed asserted",  calibration_armed === 1'b1);
        tx_timestamp_valid = 1'b0;

        // simulate rx_timestamp_valid from threshold detector
        rx_timestamp_valid = 1'b1;
        @(posedge clock);
        @(negedge clock);
        // CAL_DONE transitions to IDLE in same cycle
        check("Cal done: state is CAL_DONE or IDLE",
              current_state === STATE_CAL_DONE || current_state === STATE_IDLE);
        rx_timestamp_valid = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Cal complete: state is IDLE",           current_state === STATE_IDLE);
        check("Cal complete: calibration_done in status",
              state_machine_status[5] === 1'b1);
        check("Cal complete: calibration_start deasserted",
              calibration_start === 1'b0);
        check("Cal complete: calibration_armed deasserted",
              calibration_armed === 1'b0);

        // -------------------------------------------------------
        // Test 8: Invalid command in wrong state
        // -------------------------------------------------------
        // in IDLE, CMD_STOP should be ignored
        issue_cmd(CMD_STOP);
        @(posedge clock);
        @(negedge clock);
        check("Invalid cmd: IDLE ignores CMD_STOP",   current_state === STATE_IDLE);

        // in IDLE, CMD_START should be ignored (must configure first)
        issue_cmd(CMD_START);
        @(posedge clock);
        @(negedge clock);
        check("Invalid cmd: IDLE ignores CMD_START",  current_state === STATE_IDLE);

        // go to CONFIGURE, try CMD_CALIBRATE (invalid from CONFIGURE)
        issue_cmd(CMD_CONFIGURE);
        @(posedge clock);
        @(negedge clock);
        issue_cmd(CMD_CALIBRATE);
        @(posedge clock);
        @(negedge clock);
        check("Invalid cmd: CONFIGURE ignores CMD_CALIBRATE",
              current_state === STATE_CONFIGURE);

        // -------------------------------------------------------
        // Test 9: Reset from RUN returns to IDLE
        // -------------------------------------------------------
        // get to RUN state
        issue_cmd(CMD_START);
        @(posedge clock);
        @(negedge clock);
        fir_reload_done = 1'b1;
        repeat (3) @(posedge clock);
        @(negedge clock);
        fir_reload_done = 1'b0;

        // verify we're in RUN
        check("Pre-reset: state is RUN", current_state === STATE_RUN);

        // assert async reset
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Mid-reset: state is IDLE",            current_state === STATE_IDLE);
        check("Mid-reset: pipeline_reset_n is low",  pipeline_reset_n === 1'b0);

        // release reset
        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);
        check("Post-reset: state is IDLE",           current_state === STATE_IDLE);

        // -------------------------------------------------------
        // Test 10: Full normal measurement flow
        // -------------------------------------------------------
        // IDLE -> CONFIGURE -> START -> RUN -> STOP -> IDLE
        issue_cmd(CMD_CONFIGURE);
        @(posedge clock);
        @(negedge clock);
        check("Flow: entered CONFIGURE", current_state === STATE_CONFIGURE);

        issue_cmd(CMD_START);
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Flow: in STARTUP_FIR waiting", current_state === STATE_STARTUP_FIR);

        fir_reload_done = 1'b1;
        @(posedge clock);
        @(negedge clock);
        fir_reload_done = 1'b0;
        check("Flow: entered RUN", current_state === STATE_RUN);
        check("Flow: pipeline active", processing_enable === 1'b1);

        issue_cmd(CMD_STOP);
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Flow: back to IDLE", current_state === STATE_IDLE);

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
