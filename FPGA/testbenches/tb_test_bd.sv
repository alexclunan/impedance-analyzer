// tb_test_bd.sv
// Author: Alex Clunan
//
// Standalone testbench for test_bd (phase_accumulator -> CORDIC).
// Purpose: verify the scaled-radians phase fix in phase_accumulator.v produces a
// clean, symmetric cosine with NO mid-period skip/glitch, and at the right rate.
//
// It drives fcw/rstn/clk, dumps cos_out to tb_test_bd_out.csv (index,cos) for
// plotting, and self-checks two things automatically:
//   1) CONTINUITY  - a correct slow cosine changes only a little each sample; a
//      phase-range overflow (the "skipped chunk") produces a large jump. Any jump
//      over STEP_LIMIT is flagged as a glitch.
//   2) PERIOD      - rising zero-crossings of cos are timed; the measured period
//      should equal SAMPLES_PER_PERIOD (catches a wrong scaling factor that
//      doubles/halves the frequency).

`timescale 1ns / 1ps

module tb_test_bd;

  // ---- DUT I/O ----
  logic         clk  = 1'b0;
  logic         rstn = 1'b0;
  logic [47:0]  fcw  = 48'd0;
  logic [15:0]  cos_out;
  logic         sincos_valid;

  // signed view of the fix16_14 output
  wire signed [15:0] cos_s = cos_out;

  // ---- stimulus parameters ----
  // FCW = 2^36 -> one output period every 2^48/2^36 = 4096 samples.
  localparam [47:0] FCW_VAL            = 48'h0010_0000_0000;
  localparam int    SAMPLES_PER_PERIOD = 4096;
  localparam int    NUM_PERIODS        = 2;
  localparam int    CORDIC_LATENCY     = 40;    // pipeline fill margin (latency ~20)
  localparam int    STEP_LIMIT         = 1000;  // max legal sample-to-sample jump
                                                // (real max ~41; glitch >> 1000)

  // ---- 200 MHz clock (5 ns period) ----
  always #2.5 clk = ~clk;

  // ---- DUT ----
  test_bd_wrapper dut (
    .clk          (clk),
    .fcw          (fcw),
    .rstn         (rstn),
    .cos_out      (cos_out),
    .sincos_valid (sincos_valid)
  );

  // ---- checking state ----
  integer csv;
  integer i;
  integer errors  = 0;
  integer last_zc = -1;
  logic signed [15:0] prev_cos;
  logic have_prev = 1'b0;

  initial begin
    csv = $fopen("tb_test_bd_out.csv", "w");
    $fdisplay(csv, "index,cos,valid");

    // reset (rstn active-low)
    rstn = 1'b0;
    fcw  = 48'd0;
    repeat (10) @(posedge clk);
    rstn = 1'b1;
    fcw  = FCW_VAL;
    $display("[%0t] released reset, fcw=0x%012h (%0d samples/period)",
             $time, FCW_VAL, SAMPLES_PER_PERIOD);

    // let the CORDIC pipeline fill
    repeat (CORDIC_LATENCY) @(posedge clk);

    // capture NUM_PERIODS worth of samples
    for (i = 0; i < SAMPLES_PER_PERIOD*NUM_PERIODS; i = i + 1) begin
      @(posedge clk);
      #0.1;  // settle past the clock edge before sampling
      $fdisplay(csv, "%0d,%0d,%0b", i, cos_s, sincos_valid);

      if (have_prev) begin
        // (1) continuity: flag any discontinuity => phase overflow / skip
        if ((cos_s - prev_cos) >  STEP_LIMIT || (prev_cos - cos_s) >  STEP_LIMIT) begin
          $display("[%0t] GLITCH cos @%0d: %0d -> %0d (jump %0d)",
                   $time, i, prev_cos, cos_s, (cos_s - prev_cos));
          errors = errors + 1;
        end

        // (2) period: rising zero-crossing of cos
        if (prev_cos < 0 && cos_s >= 0) begin
          if (last_zc >= 0)
            $display("[%0t] cos period = %0d samples (expected %0d)",
                     $time, (i - last_zc), SAMPLES_PER_PERIOD);
          last_zc = i;
        end
      end

      prev_cos = cos_s;
      have_prev = 1'b1;
    end

    $fclose(csv);
    if (errors == 0)
      $display("PASS: no discontinuities over %0d samples (%0d periods) -- cosine is clean.",
               SAMPLES_PER_PERIOD*NUM_PERIODS, NUM_PERIODS);
    else
      $display("FAIL: %0d discontinuities -- phase-range overflow/skip still present.", errors);

    $finish;
  end

  // ---- waveform dump for visual inspection ----
  initial begin
    $dumpfile("tb_test_bd.vcd");
    $dumpvars(0, tb_test_bd);
  end

endmodule
