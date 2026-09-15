// reset_sync.v
// -----------------------------------------------------------------------------
// Asynchronous-assert / synchronous-deassert reset synchronizer.
//
// Purpose: never wire a register-file bit (or any cross-domain signal) straight
// into an IP's reset. A raw reg bit has no reset tree, huge fanout, and an
// unrelated clock edge -> recovery/removal failures on deassert, and metastable
// release when it crosses into another clock domain (e.g. the DCO capture
// domain). This module gives every functional-group reset a clean release:
//
//   * ASSERT   is asynchronous  -> the instant arst_n falls, srst_n falls too,
//              so logic stops immediately regardless of clock state.
//   * DEASSERT is synchronous   -> release ripples up the STAGES flop chain on
//              THIS domain's clock, so every flop leaves reset on the same edge
//              with removal timing met and no metastability.
//
// Instantiate ONE per (functional group x clock domain). A soft reset that
// touches logic in both CLKin (processing) and DCO (capture) domains needs two
// instances, each clocked locally -- do not share one srst_n across the CDC.
//
// Feed arst_n with the gated source:  system_aresetn & soft_reset_n[group]
// (system_aresetn comes from proc_sys_reset; soft_reset_n[group] from reg2).
//
// The assert edge into sync_reg[0] is a genuine false path; constrain it (see
// the set_false_path note in the project XDC) so the tool doesn't try to time
// the async reg bit into the first flop.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module reset_sync #(
    parameter integer STAGES = 3   // 2 minimum; 3 for extra MTBF margin
) (
    input  wire clk,       // destination-domain clock
    input  wire arst_n,    // async source: system_aresetn & soft_reset_n[group]
    output wire srst_n     // clean active-low reset for this group/domain
);

    (* ASYNC_REG = "TRUE" *) reg [STAGES-1:0] sync_reg = {STAGES{1'b0}};

    always @(posedge clk or negedge arst_n) begin
        if (!arst_n)
            sync_reg <= {STAGES{1'b0}};              // async assert
        else
            sync_reg <= {sync_reg[STAGES-2:0], 1'b1}; // sync deassert, walks a 1 up
    end

    assign srst_n = sync_reg[STAGES-1];

endmodule
