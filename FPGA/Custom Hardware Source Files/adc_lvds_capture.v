// adc_lvds_capture.v
// Author: Alex Clunan
//
// Forked from the Vivado SelectIO Wizard IP `adc_input` (selectio_wiz_v5_1) to
// enable internal 100 ohm LVDS termination (DIFF_TERM) on the AD9467 inputs --
// the wizard hardcodes IBUFDS DIFF_TERM="FALSE" and it cannot be overridden from
// XDC (port property ignored, cell property unsupported -- Netlist 29-75).
// Requires VCCO(bank 35) = 2.5 V for LVDS_25 + DIFF_TERM.
//
// Simplified vs the wizard: the fixed IDELAYE2 input-delay chain (and therefore
// IDELAYCTRL + its ref_clock/delay_locked) is REMOVED -- the wizard parked it at
// IDELAY_VALUE=0 (unused), so data goes straight IBUFDS -> IDDR. Note this also
// drops the ~600 ps matched insertion delay, so data is more edge-aligned to the
// DCO at the IDDR. If capture shows bit errors, re-introduce an input delay or
// shift/invert the capture clock. DDR capture (SAME_EDGE_PIPELINED, SYS_W=9 ->
// DEV_W=18) is otherwise identical to the validated wizard output.
//
// BD swap: delete the `adc_input` IP block, Add Module `adc_lvds_capture`, name
// the block instance `adc_input` and keep the port connections. Inner instance
// is `inst` and the clock buffers are `ibufds_clk_inst`/`clkout_buf_inst`, so the
// generated_clock XDC path (full_design_i/adc_input/inst/...) needs no change.

`timescale 1ps/1ps

module adc_lvds_capture
 #(parameter SYS_W = 9,     // differential pairs from the ADC
   parameter DEV_W = 18)    // fabric width (2:1 DDR)
 (
  input  [SYS_W-1:0] data_in_from_pins_p,
  input  [SYS_W-1:0] data_in_from_pins_n,
  output [DEV_W-1:0] data_in_to_device,
  input              clk_in_p,       // DCO from the AD9467
  input              clk_in_n,
  output             clk_out,
  input              io_reset);

  adc_lvds_capture_selectio
  #(.SYS_W(SYS_W),
    .DEV_W(DEV_W))
  inst
  (.data_in_from_pins_p (data_in_from_pins_p),
   .data_in_from_pins_n (data_in_from_pins_n),
   .data_in_to_device   (data_in_to_device),
   .clk_in_p            (clk_in_p),
   .clk_in_n            (clk_in_n),
   .clk_out             (clk_out),
   .io_reset            (io_reset));

endmodule


module adc_lvds_capture_selectio
 #(parameter SYS_W = 9,
   parameter DEV_W = 18)
 (
  input  [SYS_W-1:0] data_in_from_pins_p,
  input  [SYS_W-1:0] data_in_from_pins_n,
  output [DEV_W-1:0] data_in_to_device,
  input              clk_in_p,
  input              clk_in_n,
  output             clk_out,
  input              io_reset);

  wire clock_enable = 1'b1;
  wire [SYS_W-1:0] data_in_from_pins_int;   // after the buffer
  wire clk_in_int, clk_in_int_buf, clk_div;

  // --- DCO clock input: internal 100 ohm termination ---
  IBUFDS
    #(.DIFF_TERM  ("TRUE"),
      .IOSTANDARD ("LVDS_25"))
   ibufds_clk_inst
     (.I  (clk_in_p),
      .IB (clk_in_n),
      .O  (clk_in_int));

  BUFIO bufio_inst
   (.O (clk_in_int_buf),
    .I (clk_in_int));

  BUFR
    #(.SIM_DEVICE ("7SERIES"),
      .BUFR_DIVIDE("BYPASS"))
    clkout_buf_inst
    (.O  (clk_div),
     .CE (1'b1),
     .CLR(1'b0),
     .I  (clk_in_int));

  assign clk_out = clk_div;   // regional clock

  // --- per-lane data buffers + DDR capture (no input delay) ---
  genvar pin_count;
  generate for (pin_count = 0; pin_count < SYS_W; pin_count = pin_count + 1) begin: pins
    // internal 100 ohm termination on each data pair
    IBUFDS
      #(.DIFF_TERM  ("TRUE"),
        .IOSTANDARD ("LVDS_25"))
     ibufds_inst
       (.I  (data_in_from_pins_p  [pin_count]),
        .IB (data_in_from_pins_n  [pin_count]),
        .O  (data_in_from_pins_int[pin_count]));

    IDDR
      #(.DDR_CLK_EDGE ("SAME_EDGE_PIPELINED"),
        .INIT_Q1      (1'b0),
        .INIT_Q2      (1'b0),
        .SRTYPE       ("ASYNC"))
     iddr_inst
      (.Q1 (data_in_to_device[pin_count]),
       .Q2 (data_in_to_device[SYS_W + pin_count]),
       .C  (clk_in_int_buf),
       .CE (clock_enable),
       .D  (data_in_from_pins_int[pin_count]),
       .R  (io_reset),
       .S  (1'b0));
  end
  endgenerate

endmodule
