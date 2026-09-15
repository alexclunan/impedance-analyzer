// trigger_engine.v — deterministic "fire at absolute timestamp" outputs (Plan
// 07, Stage 2), DUAL channel.  The PS (iza_replay.c) does all the detection and,
// when it decides to fire, loads a target timestamp T and pulse width W for each
// output into spare AXI registers.  Each output goes HIGH exactly when the free-
// running timestamp counter reaches its T, holds for its W, then LOW — jitter-
// free and independent of software timing.  Two outputs support the reference's
// dual-actuator (two-solenoid) pattern: the PS sets T1 = T0 + pair_delay.
//
// Register interface (AXI_register_file, base 0x43C00000; PS macros REG_TRIG*):
//   output 0:  SPARE12 = t0_lo   SPARE13 = t0_hi   SPARE14 = w0
//   output 1:  reg9    = t1_lo   reg10   = t1_hi   reg11   = w1
//   shared  :  SPARE15 = cmd  [0] arm  [1] mode(1=hw)  [8] fire-strobe
// (reg9/reg10/reg11 were the unused per-tone phase-offset regs, repurposed here.)
//
// The PS writes cmd with the strobe low, then high, to make one rising edge that
// latches BOTH outputs at once; each then fires at its own T.  A width of 0
// disables that output (single-output configs leave w1 = 0), so it never fires.
//
// `timestamp` is the SAME free-running counter (timestamp_counter, 100 MHz,
// +2/cycle = 5 ns/count) that stamps every demod record, so T is a value the PS
// read straight off the data stream — no PC<->board clock sync anywhere.  Runs
// in the 100 MHz control/timestamp domain (clk_out2), same clock as the register
// file and the counter (no CDC on the inputs or the output edge).
//
// One shot at a time per output: a fire arriving before the previous pulse ends
// is ignored until that output returns to idle (PS delays are ms..100s of ms and
// pulses are ms, so overlap never happens; add a small FIFO later if it does).

module trigger_engine (
    input  wire        clk,          // 100 MHz control clock (main_clk_wiz clk_out2)
    input  wire        resetn,       // active-low; release at boot, leave high
    input  wire [63:0] timestamp,    // free-running 5 ns counter (timestamp_counter)

    input  wire [31:0] cmd,          // SPARE15  [0]arm [1]mode [8]fire-strobe
    input  wire [31:0] t0_lo,        // SPARE12
    input  wire [31:0] t0_hi,        // SPARE13
    input  wire [31:0] w0,           // SPARE14  output-0 pulse width (counts)
    input  wire [31:0] t1_lo,        // reg9
    input  wire [31:0] t1_hi,        // reg10
    input  wire [31:0] w1,           // reg11    output-1 pulse width (0 = disabled)

    output wire [1:0]  trigger_out,  // -> two physical actuation pins
    output wire [31:0] status        // -> axi_gpio readback (optional)
);
    wire arm    = cmd[0];
    wire strobe = cmd[8];

    // one-cycle load pulse, shared by both outputs (rising edge of the strobe)
    reg  strobe_d;
    always @(posedge clk or negedge resetn)
        if (!resetn) strobe_d <= 1'b0;
        else         strobe_d <= strobe;
    wire load = arm & strobe & ~strobe_d;

    wire [15:0] cnt0, cnt1;
    trigger_shot shot0 (
        .clk(clk), .resetn(resetn), .timestamp(timestamp), .arm(arm),
        .load(load), .t_lo(t0_lo), .t_hi(t0_hi), .width(w0),
        .out(trigger_out[0]), .count(cnt0));
    trigger_shot shot1 (
        .clk(clk), .resetn(resetn), .timestamp(timestamp), .arm(arm),
        .load(load), .t_lo(t1_lo), .t_hi(t1_hi), .width(w1),
        .out(trigger_out[1]), .count(cnt1));

    // low half = output-0 fire count, high half = output-1 (a 32-bit axi_gpio
    // shows both; a 16-bit one shows output 0).
    assign status = {cnt1, cnt0};

endmodule


// One deterministic single-shot output.
module trigger_shot (
    input  wire        clk,
    input  wire        resetn,
    input  wire [63:0] timestamp,
    input  wire        arm,
    input  wire        load,         // one-cycle: latch T,W and arm this shot
    input  wire [31:0] t_lo,
    input  wire [31:0] t_hi,
    input  wire [31:0] width,        // pulse width in counts; 0 = disabled
    output reg         out,
    output reg  [15:0] count         // completed pulses (for readback)
);
    localparam ST_IDLE = 2'd0, ST_WAIT = 2'd1, ST_FIRE = 2'd2;
    reg [1:0]  state;
    reg [63:0] t_fire, t_end;

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state  <= ST_IDLE;
            out    <= 1'b0;
            count  <= 16'd0;
            t_fire <= 64'd0;
            t_end  <= 64'd0;
        end else begin
            case (state)
            ST_IDLE: begin
                out <= 1'b0;
                if (load && (width != 32'd0)) begin   // width 0 => output disabled
                    t_fire <= {t_hi, t_lo};
                    t_end  <= {t_hi, t_lo} + {32'd0, width};
                    state  <= ST_WAIT;
                end
            end
            // fire when the live counter reaches T (">=" also covers a T already
            // in the past -- a very short/late delay fires next cycle).
            ST_WAIT: begin
                if (!arm)
                    state <= ST_IDLE;                  // disarmed: cancel shot
                else if (timestamp >= t_fire) begin
                    out   <= 1'b1;
                    state <= ST_FIRE;
                end
            end
            // hold the pulse for W counts, then release.
            ST_FIRE: begin
                if (timestamp >= t_end) begin
                    out   <= 1'b0;
                    count <= count + 16'd1;
                    state <= ST_IDLE;
                end
            end
            default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
