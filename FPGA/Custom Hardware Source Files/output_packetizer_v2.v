// output_packetizer_v2.v
// -----------------------------------------------------------------------------
// Reconfigurable, self-describing packetizer (Plan 05 Stage B).
//
// Runs in the 100 MHz control/output domain. Consumes wide "super-record"
// frames from the demod->packetizer CDC FIFO (all 4 demod channels + raw-ADC
// monitor + OR flags, captured coherently in the 200 MHz domain), stamps each
// with the LOCAL 100 MHz timestamp, and serializes ONLY the channels selected
// by channel_mask into 32-bit AXIS beats for the DMA S2MM.
//
// Fixed field order (disabled channels omitted -> the software header's mask
// tells the PC the layout):
//   ts_lo, ts_hi(+OR)                     (always)
//   sig_i, phase_i  for each enabled i    (ascending)
//   adc                                   (if channel_mask[4])
//
// records_per_packet sets tlast (= one S2MM buffer). Both mask and count are
// quasi-static register inputs; they are latched at each packet boundary so a
// mid-packet change can't corrupt framing.
//
// Backpressure: one frame is popped per record (s_axis_tready = idle between
// records); every beat is held until m_axis_tready, including tlast.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module output_packetizer_v2 #(
    parameter integer NCH     = 4,      // demod channels
    parameter integer SIGW    = 32,
    parameter integer PHW     = 32,
    parameter integer ADCW    = 16,
    // frame layout (byte-aligned for the AXIS FIFO): per channel {phase,sig}
    // (ch0 in LSBs), then a 32-bit status word {OR[1:0], 14'b0, adc[15:0]}.
    parameter integer FRAME_W = NCH*(SIGW+PHW) + 32          // 288 = 36 B
)(
    input  wire                 clk,       // 100 MHz (clk_out2)
    input  wire                 rst_n,     // pipe_srst_n_100

    // quasi-static config (register file, 100 domain)
    input  wire                 run,                 // SYS_CTRL0[5]; see below
    input  wire [4:0]           channel_mask,        // {adc_en, ch3..ch0}
    input  wire [7:0]           records_per_packet,  // >=1

    // local 100 MHz timestamp (timestamp_counter, increments by 2)
    input  wire [63:0]          timestamp,

    // frame in from the CDC FIFO (axis_data_fifo, indep clocks 200->100)
    input  wire [FRAME_W-1:0]   s_axis_tdata,
    input  wire                 s_axis_tvalid,
    output wire                 s_axis_tready,

    // AXIS out to DMA S2MM
    output reg  [31:0]          m_axis_tdata,
    output reg                  m_axis_tvalid,
    output reg                  m_axis_tlast,
    input  wire                 m_axis_tready
);
    localparam CHW = SIGW + PHW;          // 64 bits per channel

    // ---- captured frame + timestamp ----
    reg  [SIGW-1:0] sig_r   [0:NCH-1];
    reg  [PHW-1:0]  phase_r [0:NCH-1];
    reg  [ADCW-1:0] adc_r;
    reg  [1:0]      or_r;
    reg  [63:0]     ts_r;                 // ts with OR folded into top 2 bits

    // ---- latched-at-packet-start config ----
    reg  [4:0]      mask_r;
    reg  [7:0]      rpp_r;                // records_per_packet, >=1
    reg  [7:0]      rec_idx;              // 0..rpp_r-1

    // ---- field walker (fixed slots 0..10) ----
    // 0 ts_lo | 1 ts_hi | 2 sig0 3 ph0 | 4 sig1 5 ph1 | 6 sig2 7 ph2 |
    // 8 sig3 9 ph3 | 10 adc
    reg  [3:0]      field_idx;

    localparam IDLE = 1'b0, EMIT = 1'b1;
    reg             state;

    integer i;

    // presence of each fixed slot given the mask
    wire [10:0] present;
    assign present[0]  = 1'b1;
    assign present[1]  = 1'b1;
    assign present[2]  = mask_r[0];
    assign present[3]  = mask_r[0];
    assign present[4]  = mask_r[1];
    assign present[5]  = mask_r[1];
    assign present[6]  = mask_r[2];
    assign present[7]  = mask_r[2];
    assign present[8]  = mask_r[3];
    assign present[9]  = mask_r[3];
    assign present[10] = mask_r[4];

    // highest present slot -> carries tlast for the packet's final record
    reg  [3:0] last_field;
    always @(*) begin
        last_field = 4'd1;
        for (i = 0; i < 11; i = i + 1)
            if (present[i]) last_field = i[3:0];
    end

    // data for the current slot
    reg [31:0] fdat;
    always @(*) begin
        case (field_idx)
            4'd0:  fdat = ts_r[31:0];
            4'd1:  fdat = ts_r[63:32];
            4'd2:  fdat = sig_r[0];
            4'd3:  fdat = phase_r[0];
            4'd4:  fdat = sig_r[1];
            4'd5:  fdat = phase_r[1];
            4'd6:  fdat = sig_r[2];
            4'd7:  fdat = phase_r[2];
            4'd8:  fdat = sig_r[3];
            4'd9:  fdat = phase_r[3];
            4'd10: fdat = {{(32-ADCW){adc_r[ADCW-1]}}, adc_r};  // sign-extend i16
            default: fdat = 32'h0;
        endcase
    end

    // ---- graceful stop -----------------------------------------------------
    // Dropping the stream the instant `run` goes low is NOT safe: deasserting
    // m_axis_tvalid before m_axis_tready violates AXI-Stream, and it leaves the
    // DMA S2MM holding a partial transfer that never completes -- the FINISH
    // ioctl then blocks forever and the dma_proxy driver has to be reloaded
    // (a `reset` while streaming used to require a reboot).
    //
    // Instead: stop accepting NEW frames, let the record already in flight run
    // to its last field, and force TLAST on that final beat.  The DMA sees a
    // short-but-complete packet, closes the buffer, and FINISH returns normally.
    reg stopping;

    wire last_record = (rec_idx == (rpp_r - 8'd1));
    wire beat_is_last = (field_idx == last_field) && (last_record || stopping);

    // pop one frame per record while idle -- but never start a new record once
    // a stop has been requested
    assign s_axis_tready = (state == IDLE) && run;

    always @(posedge clk) begin
        if (!rst_n) begin
            state         <= IDLE;
            m_axis_tvalid <= 1'b0;
            m_axis_tlast  <= 1'b0;
            m_axis_tdata  <= 32'h0;
            field_idx     <= 4'd0;
            rec_idx       <= 8'd0;
            stopping      <= 1'b0;
            rpp_r         <= 8'd1;
            mask_r        <= 5'd0;
            or_r          <= 2'd0;
            adc_r         <= {ADCW{1'b0}};
            ts_r          <= 64'h0;
            for (i = 0; i < NCH; i = i + 1) begin
                sig_r[i]   <= {SIGW{1'b0}};
                phase_r[i] <= {PHW{1'b0}};
            end
        end else begin
            // A stop requested mid-record is remembered so the record still
            // finishes and closes the packet with TLAST.  It is cleared only
            // once run is back AND we are idle, so it can never leak into the
            // next run and truncate its first packet.
            if (!run)
                stopping <= 1'b1;
            else if (state == IDLE)
                stopping <= 1'b0;

            case (state)
                IDLE: begin
                    m_axis_tvalid <= 1'b0;
                    m_axis_tlast  <= 1'b0;
                    if (s_axis_tvalid && run) begin
                        // unpack the wide frame
                        for (i = 0; i < NCH; i = i + 1) begin
                            sig_r[i]   <= s_axis_tdata[i*CHW        +: SIGW];
                            phase_r[i] <= s_axis_tdata[i*CHW + SIGW +: PHW];
                        end
                        // status word {OR[1:0], 14'b0, adc[15:0]} at NCH*CHW
                        adc_r <= s_axis_tdata[NCH*CHW      +: ADCW];
                        or_r  <= s_axis_tdata[NCH*CHW + 30 +: 2];
                        // local timestamp, OR folded into the top 2 bits
                        ts_r  <= {s_axis_tdata[NCH*CHW + 30 +: 2],
                                  timestamp[61:0]};
                        // latch config at the start of each packet only
                        if (rec_idx == 8'd0) begin
                            mask_r <= channel_mask;
                            rpp_r  <= (records_per_packet == 8'd0)
                                      ? 8'd1 : records_per_packet;
                        end
                        field_idx <= 4'd0;
                        state     <= EMIT;
                    end
                end

                EMIT: begin
                    if (!m_axis_tvalid) begin
                        if (present[field_idx]) begin
                            m_axis_tdata  <= fdat;
                            m_axis_tvalid <= 1'b1;
                            m_axis_tlast  <= beat_is_last;
                        end else begin
                            field_idx <= field_idx + 4'd1;   // skip empty slot
                        end
                    end else if (m_axis_tready) begin
                        m_axis_tvalid <= 1'b0;
                        m_axis_tlast  <= 1'b0;
                        if (field_idx == last_field) begin
                            // record complete; a stop ends the packet here
                            field_idx <= 4'd0;
                            rec_idx   <= (last_record || stopping)
                                         ? 8'd0 : (rec_idx + 8'd1);
                            state     <= IDLE;
                        end else begin
                            field_idx <= field_idx + 4'd1;
                        end
                    end
                end
            endcase
        end
    end

endmodule
