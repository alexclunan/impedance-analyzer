// fir_coeff_loader.v — stage reloadable FIR coefficients from a control register
// and reconfigure the whole demod chain: four FIR reload + config interfaces and
// four CIC config interfaces, one group per modulator_chain.
//
// Instantiate ONE of these at the top level and wire, for each chain n:
//   m_axis_reload<n> / m_axis_config<n> -> that chain's FIR S_AXIS_RELOAD /
//                                          S_AXIS_CONFIG
//   m_axis_cicfg<n>                     -> that chain's CIC rate config input
//
// All four chains run the same filter, so every group carries identical data.
// The chain fans its single cicfg input to BOTH of its CICs (I and Q) inside
// modulator_chain: they must share a rate, or the two halves of a complex
// sample would arrive at different rates and the demodulated phase would be
// meaningless.
//
// The PS (iza_ctrl.fir_load) writes coefficients one at a time into REG3; this
// module collects them into a RAM and, on a commit, streams them into all four
// reload interfaces (tlast on the last coefficient), pulses the four FIR config
// interfaces so the new taps take effect, and then — only if the commit carried
// a rate — pulses the four CIC config interfaces with that rate.
//
// REG3 command word (written by the PS; see iza_ctrl.py):
//   [15:0]  coefficient data (signed, two's complement)
//   [17:16] opcode : 0 = nop, 1 = reset index, 2 = push coeff, 3 = commit
//   [30:18] CIC decimation rate, 1000..8000.  ZERO = leave the rate unchanged,
//           which is what every pre-existing REG3 write already sends, so old
//           software cannot disturb the rate.  Applied on COMMIT only: the
//           coefficients and the rate they were designed for take effect
//           together, so the chain is never running a filter against a sample
//           rate it was not designed for.  Out-of-range values are ignored
//           (not clamped) — iza_ctrl rejects them before the wire.
//   [31]    strobe toggle — the PS FLIPS this every write so each command is a
//           unique edge (works even when two coefficients are identical)
//
// A commit carrying a rate steps the output sample rate, which is a framing
// discontinuity for everything downstream.  Quiesce the packetizer/DMA across
// it and re-arm afterwards, the same discipline as any other mid-stream config
// change.
//
// NO BACKPRESSURE.  These masters have no tready: every beat is assumed taken
// the cycle it is presented.  If a destination ever deasserts ready, the beat
// is lost silently and the filter that ends up loaded is not the one designed —
// the same class of failure as an NCOEF mismatch, with nothing reported.  The
// STRIDE parameter exists as insurance: raise it to hold each beat for more
// cycles without touching the logic.
//
// Clock domain: run this in the FIRs' aclk (the 200 MHz demod domain).  REG3 is
// produced in the 100 MHz control domain, so the toggle is brought across with a
// 2-FF synchronizer; the data bits are quasi-static (held in the register until
// the next PS write, which are milliseconds apart over UDP), so they are stable
// long before the synchronized toggle edge — a standard "data + toggle" MCP
// handshake.  No back-to-back hazard at UDP write rates.
//
// Fan-out: ONE beat generator drives a PER-CHAIN output register stage, so each
// chain's signals leave the module from their own flip-flops and the tools can
// place each near its destination instead of routing one net to four corners of
// the die.  The pipeline depth is uniform, so every chain sees an identical beat
// sequence one cycle later; a FIR only cares about the order of its own
// coefficients, not about alignment with the other chains, so the skew between
// chains is harmless.

`timescale 1ns / 1ps
module fir_coeff_loader #(
    // HARDCODED to 999 — the reload length of the 999-tap NON-SYMMETRIC FIR
    // build. Do NOT override this from the block design and do not treat it as
    // tunable: it must equal the FIR Compiler's NUM_TAPS exactly, and the PC
    // must push exactly this many coefficients per commit.
    //
    // Why both sides must agree, and why a mismatch is dangerous:
    //   * commit always streams NCOEF beats (rd_ptr walks 0..NCOEF-1), so a
    //     short push leaves stale coefficients in the tail;
    //   * OP_PUSH SATURATES the write pointer at NCOEF-1 instead of erroring,
    //     so an over-long push is silently dropped.
    // Either way the board runs a filter nobody designed and nothing reports an
    // error. fir_design.LOADER_NCOEF holds the same 999 on the PC side, and
    // fir_design.loader_payload() pads/validates every push against it.
    //
    // Was 64 for the old symmetric 127-tap build, where the IP folded its taps
    // and took only the unique half, (127+1)/2 = 64. A non-symmetric build
    // takes all N taps, and a left-justified latency design needs the full
    // frame (its trailing zeros are what set the group delay).
    parameter integer NCOEF = 999,
    parameter integer CW    = 16,     // coefficient width (bits)
    parameter integer CFGW  = 8,      // FIR config tdata width

    // Cycles per beat. 1 = one coefficient per clock (999 beats ~ 5 us at
    // 200 MHz). Raise it only if hardware shows dropped coefficients: with no
    // tready there is nothing to tell us a destination was not ready, so this
    // is the one knob that buys margin.
    parameter integer STRIDE = 1,

    // ---- CIC programmable rate ----
    // CICW is the CIC Compiler's config tdata width. For a programmable-rate
    // CIC the config word carries the rate change value right-justified, and
    // tdata is rounded up to a byte multiple: RATE_MAX = 8000 needs 13 bits,
    // so 16.  ** Confirm the exact packing against PG140 for your IP options
    // before trusting a rate change on hardware ** — same caveat as the reload
    // order against PG149.
    parameter integer CICW     = 16,
    parameter integer RATE_MIN = 1000,   // CIC MIN_RATE — keep equal to the IP
    parameter integer RATE_MAX = 8000    // CIC MAX_RATE — keep equal to the IP
)(
    input  wire            clk,       // FIR aclk (200 MHz demod domain)
    input  wire            resetn,    // active-low
    input  wire [31:0]     reg3,      // command register (control domain)

    // ---- four FIR reload masters (S_AXIS_RELOAD of each chain) ----
    output wire [CW-1:0]   m_axis_reload0_tdata,
    output wire            m_axis_reload0_tvalid,
    output wire            m_axis_reload0_tlast,
    output wire [CW-1:0]   m_axis_reload1_tdata,
    output wire            m_axis_reload1_tvalid,
    output wire            m_axis_reload1_tlast,
    output wire [CW-1:0]   m_axis_reload2_tdata,
    output wire            m_axis_reload2_tvalid,
    output wire            m_axis_reload2_tlast,
    output wire [CW-1:0]   m_axis_reload3_tdata,
    output wire            m_axis_reload3_tvalid,
    output wire            m_axis_reload3_tlast,

    // ---- four FIR config masters (S_AXIS_CONFIG of each chain) ----
    output wire [CFGW-1:0] m_axis_config0_tdata,
    output wire            m_axis_config0_tvalid,
    output wire [CFGW-1:0] m_axis_config1_tdata,
    output wire            m_axis_config1_tvalid,
    output wire [CFGW-1:0] m_axis_config2_tdata,
    output wire            m_axis_config2_tvalid,
    output wire [CFGW-1:0] m_axis_config3_tdata,
    output wire            m_axis_config3_tvalid,

    // ---- four CIC config masters, one per chain ----
    // Carries the decimation rate; the chain fans it to its I and Q CICs.
    // Pulsed only when REG3's rate field is non-zero at commit, so a build with
    // a fixed-rate CIC can leave these unconnected.
    output wire [CICW-1:0] m_axis_cicfg0_tdata,
    output wire            m_axis_cicfg0_tvalid,
    output wire [CICW-1:0] m_axis_cicfg1_tdata,
    output wire            m_axis_cicfg1_tvalid,
    output wire [CICW-1:0] m_axis_cicfg2_tdata,
    output wire            m_axis_cicfg2_tvalid,
    output wire [CICW-1:0] m_axis_cicfg3_tdata,
    output wire            m_axis_cicfg3_tvalid,

    output wire [12:0]     rate_now,   // last accepted rate (0 = none yet)
    output wire            busy        // high while a reload is in progress
);
    localparam integer NCH = 4;                       // modulator chains
    localparam integer AW  = (NCOEF <= 1) ? 1 : $clog2(NCOEF);
    localparam integer SW  = (STRIDE <= 1) ? 1 : $clog2(STRIDE);
    localparam [1:0] OP_NOP = 2'd0, OP_RESET = 2'd1, OP_PUSH = 2'd2, OP_COMMIT = 2'd3;
    localparam [1:0] S_IDLE = 2'd0, S_RELOAD = 2'd1, S_CONFIG = 2'd2, S_CIC = 2'd3;

    integer j;

    // ---- CDC: bring the strobe toggle into this clock, edge-detect ----
    reg tog_meta, tog_sync, tog_prev;
    always @(posedge clk) begin
        tog_meta <= reg3[31];
        tog_sync <= tog_meta;
        tog_prev <= tog_sync;
    end
    wire cmd_stb        = tog_sync ^ tog_prev;   // one pulse per PS write
    wire [1:0]    op    = reg3[17:16];
    wire [CW-1:0] data  = reg3[CW-1:0];

    // ---- CIC decimation rate, REG3[30:18] ----
    // 13 bits, exactly enough for RATE_MAX = 8000. ZERO MEANS "LEAVE THE RATE
    // ALONE": every REG3 write that predates this field leaves those bits
    // clear, so old software keeps working and never disturbs the rate.
    // Out-of-range values are ignored rather than clamped — a clamp would run
    // the chain at a rate nobody asked for, and iza_ctrl already rejects them.
    wire [12:0] rate_field = reg3[30:18];
    wire        rate_ok    = (rate_field >= RATE_MIN) && (rate_field <= RATE_MAX);
    reg  [12:0] rate_q;                      // last accepted rate (0 = none yet)
    assign rate_now = rate_q;

    // ---- coefficient staging RAM (BLOCK RAM, 2-cycle read) ----
    // 999 x 16 = 15,984 bits, so one RAMB18 holds the whole coefficient set.
    // ram_style is forced because the fallback matters: left to itself the tool
    // may build this from LUTRAM, and a 999-deep distributed RAM is ~500 LUTs
    // with an asynchronous ~999:1 x 16 read mux, which cannot make 200 MHz.
    //
    // The read is deliberately FREE-RUNNING off the registered rd_ptr — no
    // enable, no adder in the address path — because that is the shape Vivado
    // maps straight onto a BRAM address port. ram_dout is the BRAM core
    // register and ram_dout_q its OUTPUT register; the output register is what
    // takes a 7-series BRAM comfortably past 200 MHz on a -1 part, and it is
    // free here because a reload has no throughput requirement.
    //
    // Cost: the read is now 2 cycles behind rd_ptr instead of 1, so tvalid and
    // tlast are delayed to match (see the alignment pipe below). Get that
    // matching wrong and the loaded filter is shifted by a coefficient.
    (* ram_style = "block" *)
    reg [CW-1:0] coeff [0:NCOEF-1];
    reg [CW-1:0] ram_dout, ram_dout_q;
    reg [AW-1:0] wr_ptr, rd_ptr;

    // ---- shared beat generator (one copy, before the output registers) ----
    reg [1:0]      state;
    reg [SW-1:0]   stride_cnt;
    reg            rl_valid_c, rl_last_c;
    reg [CFGW-1:0] cfg_data_c;
    reg            cfg_valid_c;
    reg [CICW-1:0] cic_data_c;
    reg            cic_valid_c;
    reg            cic_pend;             // this commit carries a rate change

    wire beat = (stride_cnt == {SW{1'b0}});   // this cycle advances the stream

    // ---- the RAM itself: one clocked block, write port + free-running read ----
    // Kept in its own always block with nothing else in it, which is the
    // canonical simple-dual-port template. Writes only happen while idle and
    // reads only while streaming, so the two never collide and the read-during-
    // write behaviour is irrelevant.
    wire ram_we = cmd_stb && (state == S_IDLE) && (op == OP_PUSH);
    always @(posedge clk) begin
        if (ram_we) coeff[wr_ptr] <= data;
        ram_dout   <= coeff[rd_ptr];   // BRAM core output register
        ram_dout_q <= ram_dout;        // BRAM optional output register
    end

    always @(posedge clk) begin
        if (!resetn) begin
            wr_ptr <= {AW{1'b0}}; rd_ptr <= {AW{1'b0}};
            state  <= S_IDLE;
            stride_cnt  <= {SW{1'b0}};
            rl_valid_c  <= 1'b0; rl_last_c <= 1'b0;
            cfg_data_c  <= {CFGW{1'b0}}; cfg_valid_c <= 1'b0;
            cic_data_c  <= {CICW{1'b0}}; cic_valid_c <= 1'b0;
            cic_pend    <= 1'b0;
            rate_q      <= 13'd0;
        end else begin
            // Latch the rate on any command write that carries a valid one. It
            // is quasi-static in REG3, so sampling it alongside the opcode is
            // safe; it is only ACTED on at commit, which keeps the coefficients
            // and the rate they were designed for atomic.
            if (cmd_stb && rate_ok) rate_q <= rate_field;

            case (state)
            // -------- accept commands from REG3 --------
            S_IDLE: begin
                rl_valid_c  <= 1'b0;
                cfg_valid_c <= 1'b0;
                cic_valid_c <= 1'b0;
                rl_last_c   <= 1'b0;
                if (cmd_stb) begin
                    case (op)
                        OP_RESET: wr_ptr <= {AW{1'b0}};
                        OP_PUSH: begin
                            // the write itself lives in the RAM block above
                            if (wr_ptr != NCOEF-1) wr_ptr <= wr_ptr + 1'b1;
                        end
                        OP_COMMIT: begin
                            rd_ptr     <= {AW{1'b0}};
                            rl_last_c  <= (NCOEF == 1);
                            rl_valid_c <= 1'b1;
                            stride_cnt <= STRIDE - 1;
                            // Only pulse the CICs when this commit actually
                            // carries a rate, so a fixed-rate build never sees
                            // a config beat it did not ask for.
                            cic_pend   <= rate_ok;
                            // Plain assignment zero-extends the 13-bit rate to
                            // CICW. Do not hand-pad with a replication: CICW=13
                            // would make the count zero, which is illegal.
                            cic_data_c <= rate_field;
                            state      <= S_RELOAD;
                        end
                        default: ; // nop
                    endcase
                end
            end
            // -------- stream coefficients to all four reload ports --------
            S_RELOAD: begin
                if (!beat) begin
                    stride_cnt <= stride_cnt - 1'b1;
                    rl_valid_c <= 1'b0;          // one valid cycle per beat
                end else if (rd_ptr == NCOEF-1) begin
                    rl_valid_c  <= 1'b0;
                    rl_last_c   <= 1'b0;
                    cfg_data_c  <= {CFGW{1'b0}}; // single coefficient set -> 0
                    cfg_valid_c <= 1'b1;
                    stride_cnt  <= STRIDE - 1;
                    state       <= S_CONFIG;
                end else begin
                    rd_ptr     <= rd_ptr + 1'b1;
                    rl_last_c  <= (rd_ptr + 1'b1 == NCOEF-1);
                    rl_valid_c <= 1'b1;
                    stride_cnt <= STRIDE - 1;
                end
            end
            // -------- commit via the four FIR config ports --------
            S_CONFIG: begin
                cfg_valid_c <= 1'b0;             // one-cycle pulse
                if (!beat) begin
                    stride_cnt <= stride_cnt - 1'b1;
                end else if (cic_pend) begin     // rate change rides this commit
                    cic_valid_c <= 1'b1;
                    stride_cnt  <= STRIDE - 1;
                    state       <= S_CIC;
                end else begin
                    state <= S_IDLE;
                end
            end
            // -------- push the decimation rate to the four CIC configs --------
            // After the FIR, so the new coefficients are already staged when the
            // rate — and therefore the sample rate they were designed for —
            // changes. The output rate steps here, which is a framing
            // discontinuity downstream; quiesce the packetizer/DMA across a
            // commit that carries a rate.
            S_CIC: begin
                cic_valid_c <= 1'b0;             // one-cycle pulse
                if (!beat) begin
                    stride_cnt <= stride_cnt - 1'b1;
                end else begin
                    cic_pend <= 1'b0;
                    state    <= S_IDLE;
                end
            end
            default: state <= S_IDLE;
            endcase
        end
    end

    // ---- alignment pipe: match the 2-cycle BRAM read ----
    // rd_ptr advances at cycle N; ram_dout has that coefficient at N+1 and
    // ram_dout_q at N+2. Every qualifier therefore needs the same two stages,
    // or tvalid would mark beats before their data arrives and the loaded
    // filter would be shifted.
    //
    // The config pulses are delayed by the same amount for a second reason:
    // they must still land AFTER the final reload beat, otherwise the FIR would
    // swap coefficient sets while the last taps were still in flight.
    // cfg_data_c / cic_data_c are static across the sequence, so only the
    // qualifiers need delaying.
    reg [1:0] rl_valid_pipe, rl_last_pipe, cfg_valid_pipe, cic_valid_pipe;

    always @(posedge clk) begin
        if (!resetn) begin
            rl_valid_pipe  <= 2'b0;
            rl_last_pipe   <= 2'b0;
            cfg_valid_pipe <= 2'b0;
            cic_valid_pipe <= 2'b0;
        end else begin
            rl_valid_pipe  <= {rl_valid_pipe[0],  rl_valid_c};
            rl_last_pipe   <= {rl_last_pipe[0],   rl_last_c};
            cfg_valid_pipe <= {cfg_valid_pipe[0], cfg_valid_c};
            cic_valid_pipe <= {cic_valid_pipe[0], cic_valid_c};
        end
    end

    // ---- per-chain output register stage ----
    // Each chain's signals leave from their own flip-flops so the tools can
    // place each register beside its destination chain. Depth is uniform, so
    // every chain gets an identical beat sequence one cycle later.
    reg [CW-1:0]   rl_data_q  [0:NCH-1];
    reg [CFGW-1:0] cfg_data_q [0:NCH-1];
    reg [CICW-1:0] cic_data_q [0:NCH-1];
    reg [NCH-1:0]  rl_valid_q, rl_last_q, cfg_valid_q, cic_valid_q;
    reg            busy_q;

    always @(posedge clk) begin
        if (!resetn) begin
            for (j = 0; j < NCH; j = j + 1) begin
                rl_data_q[j]  <= {CW{1'b0}};
                cfg_data_q[j] <= {CFGW{1'b0}};
                cic_data_q[j] <= {CICW{1'b0}};
            end
            rl_valid_q  <= {NCH{1'b0}};
            rl_last_q   <= {NCH{1'b0}};
            cfg_valid_q <= {NCH{1'b0}};
            cic_valid_q <= {NCH{1'b0}};
            busy_q      <= 1'b0;
        end else begin
            for (j = 0; j < NCH; j = j + 1) begin
                rl_data_q[j]  <= ram_dout_q;      // BRAM output register
                cfg_data_q[j] <= cfg_data_c;
                cic_data_q[j] <= cic_data_c;
            end
            rl_valid_q  <= {NCH{rl_valid_pipe[1]}};
            rl_last_q   <= {NCH{rl_last_pipe[1]}};
            cfg_valid_q <= {NCH{cfg_valid_pipe[1]}};
            cic_valid_q <= {NCH{cic_valid_pipe[1]}};
            // Registered alongside the data so busy still covers the beat that
            // is in the output stage when the state machine returns to idle.
            // Extended over the alignment pipe so busy stays high until the
            // last beat has actually left the output registers.
            busy_q      <= (state != S_IDLE) || (|rl_valid_pipe) ||
                           (|cfg_valid_pipe) || (|cic_valid_pipe);
        end
    end

    assign busy = busy_q;

    assign m_axis_reload0_tdata  = rl_data_q[0];
    assign m_axis_reload1_tdata  = rl_data_q[1];
    assign m_axis_reload2_tdata  = rl_data_q[2];
    assign m_axis_reload3_tdata  = rl_data_q[3];
    assign m_axis_reload0_tvalid = rl_valid_q[0];
    assign m_axis_reload1_tvalid = rl_valid_q[1];
    assign m_axis_reload2_tvalid = rl_valid_q[2];
    assign m_axis_reload3_tvalid = rl_valid_q[3];
    assign m_axis_reload0_tlast  = rl_last_q[0];
    assign m_axis_reload1_tlast  = rl_last_q[1];
    assign m_axis_reload2_tlast  = rl_last_q[2];
    assign m_axis_reload3_tlast  = rl_last_q[3];

    assign m_axis_config0_tdata  = cfg_data_q[0];
    assign m_axis_config1_tdata  = cfg_data_q[1];
    assign m_axis_config2_tdata  = cfg_data_q[2];
    assign m_axis_config3_tdata  = cfg_data_q[3];
    assign m_axis_config0_tvalid = cfg_valid_q[0];
    assign m_axis_config1_tvalid = cfg_valid_q[1];
    assign m_axis_config2_tvalid = cfg_valid_q[2];
    assign m_axis_config3_tvalid = cfg_valid_q[3];

    assign m_axis_cicfg0_tdata   = cic_data_q[0];
    assign m_axis_cicfg1_tdata   = cic_data_q[1];
    assign m_axis_cicfg2_tdata   = cic_data_q[2];
    assign m_axis_cicfg3_tdata   = cic_data_q[3];
    assign m_axis_cicfg0_tvalid  = cic_valid_q[0];
    assign m_axis_cicfg1_tvalid  = cic_valid_q[1];
    assign m_axis_cicfg2_tvalid  = cic_valid_q[2];
    assign m_axis_cicfg3_tvalid  = cic_valid_q[3];
endmodule
