// reset_manager.v
// -----------------------------------------------------------------------------
// Central reset distribution for the impedance analyzer PL.
//
// Two clock domains after the 100/200 split:
//   * clk_200 -- signal datapath: DDS, mixers, CIC, FIR, mag_phase, ADC capture
//                read side, sample_hold, am_modulator, DAC path.
//   * clk_100 -- control + output: output_packetizer, timestamp_counter, DMA,
//                register file, GPIO, smartconnect, HP ports.
//
// Two-tier reset scheme:
//   * system_aresetn -- hardware, from proc_sys_reset (now in the clk_100
//                       domain, since the whole AXI/control fabric is 100).
//                       Used here only as an ASYNC assert source; each group is
//                       re-synchronized in its own target domain, so it does not
//                       matter that the source is a 100-domain reset.
//   * soft resets    -- reg2 bits (register file, clk_100 domain), gated with
//                       system_aresetn then run through reset_sync in the target
//                       clock domain (async-assert / sync-deassert).
//
// Groups -> target domain:
//   dds     : DDS compiler                                   -> clk_200
//   pipe    : SPLIT. CIC_I/Q, FIR, mag_phase                 -> clk_200
//             output_packetizer, timestamp_counter           -> clk_100
//             (one reg2 bit, TWO synchronizers -- same soft reset, released
//              cleanly in each domain)
//   dac     : dac_output_wrapper                             -> clk_200
//
// Special / not through reset_sync:
//   fifo_rst (active-HIGH) : fifo_generator_0/rst (ADC CDC FIFO) -- the IP
//                            synchronizes its own async rst into both its clock
//                            domains internally; just gate the soft bit.
//
// Left ALONE: DAC chip-reset output pin (reg2 GPIO to the AD9122),
//   adc_lvds_capture_0/io_reset (tied 0), dac_io/io_reset (tie 0),
//   spi_rd_tristate/resetn (tied 1). The AXI infra reset comes straight from
//   proc_sys_reset/peripheral_aresetn, not from here.
//
// SYS_CTRL bit positions are parameters -- match iza_replay.c reset masks.
// Active-low soft-reset: SYS_CTRL[bit]=1 -> run, =0 -> reset.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module reset_manager #(
    parameter integer STAGES     = 3,   // reset_sync depth (>=2)
    parameter integer BIT_DDS    = 0,   // SYS_CTRL bit: DDS excitation/LO
    parameter integer BIT_PIPE   = 1,   // SYS_CTRL bit: demod + packetizer pipeline
    parameter integer BIT_DAC    = 2,   // SYS_CTRL bit: DAC output path
    parameter integer BIT_FIFO   = 3,   // SYS_CTRL bit: ADC CDC FIFO
    parameter integer REG_WIDTH  = 32
) (
    input  wire                 clk_200,         // signal-datapath clock (clk_out1)
    input  wire                 clk_100,         // control/output clock (clk_out2)
    input  wire                 system_aresetn,  // proc_sys_reset/peripheral_aresetn (clk_100)
    input  wire [REG_WIDTH-1:0] SYS_CTRL,            // AXI_register_file_0/SYS_CTRL (clk_100)

    output wire                 dds_srst_n,        // clk_200 -> dds_compiler_0/aresetn
    output wire                 pipe_srst_n_200,   // clk_200 -> CIC_I/Q, FIR, mag_phase
    output wire                 pipe_srst_n_100,   // clk_100 -> output_packetizer, timestamp_counter
    output wire                 dac_srst_n,        // clk_200 -> dac_output_wrapper_0
    output wire                 fifo_rst           // -> fifo_generator_0/rst (ACTIVE HIGH)
);

    // ---- gate each soft group with the hardware system reset ----------------
    wire dds_arst_n  = system_aresetn & SYS_CTRL[BIT_DDS];
    wire pipe_arst_n = system_aresetn & SYS_CTRL[BIT_PIPE];
    wire dac_arst_n  = system_aresetn & SYS_CTRL[BIT_DAC];

    // ---- dds / dac : clk_200 targets ---------------------------------------
    reset_sync #(.STAGES(STAGES)) u_dds (
        .clk(clk_200), .arst_n(dds_arst_n), .srst_n(dds_srst_n));

    reset_sync #(.STAGES(STAGES)) u_dac (
        .clk(clk_200), .arst_n(dac_arst_n), .srst_n(dac_srst_n));

    // ---- pipe : one soft reset, synchronized in BOTH domains ---------------
    reset_sync #(.STAGES(STAGES)) u_pipe_200 (
        .clk(clk_200), .arst_n(pipe_arst_n), .srst_n(pipe_srst_n_200));

    reset_sync #(.STAGES(STAGES)) u_pipe_100 (
        .clk(clk_100), .arst_n(pipe_arst_n), .srst_n(pipe_srst_n_100));

    // ---- FIFO : active-high, IP self-synchronizes across the CDC -----------
    assign fifo_rst = ~system_aresetn | ~SYS_CTRL[BIT_FIFO];

endmodule
