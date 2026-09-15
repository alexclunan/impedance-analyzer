module output_packetizer #(
    parameter SAMPLES_PER_PACKET = 1024
)(
    input  wire        clk,
    input  wire        rst_n,

    // Input signals (sampled on valid)
    input  wire [31:0] signal_out,
    input  wire [31:0] phase_out,
    input  wire [63:0] timestamp,
    input  wire        valid,          // 1-cycle pulse from CIC/FIR

    // AXI4-Stream output to DMA S2MM
    output reg  [31:0] m_axis_tdata,
    output reg         m_axis_tvalid,
    output reg         m_axis_tlast,
    input  wire        m_axis_tready
);

    // Word counter (0-3 per sample)
    reg [1:0]  word_idx;
    // Sample counter
    reg [$clog2(SAMPLES_PER_PACKET)-1:0] sample_idx;

    // Capture registers (latch on valid)
    reg [31:0] sig_reg;
    reg [31:0] phase_reg;
    reg [63:0] ts_reg;

    // State machine
    localparam IDLE   = 2'd0;
    localparam OUTPUT = 2'd1;

    reg [1:0] state;

    // Timestamp comes from the system timestamp_counter on the `timestamp`
    // input port (wired in the block design).  We latch it per sample in IDLE;
    // there is deliberately no local counter here, so the per-record timestamp
    // is coherent with the rest of the system (e.g. calibration).

    // Main FSM
    always @(posedge clk) begin
        if (!rst_n) begin
            word_idx       <= 2'd0;
            sample_idx     <= 0;
            m_axis_tdata   <= 32'h0;
            m_axis_tvalid  <= 1'b0;
            m_axis_tlast   <= 1'b0;
            sig_reg        <= 32'h0;
            phase_reg      <= 32'h0;
            ts_reg         <= 64'h0;
            state          <= IDLE;
        end else begin
            case (state)

                // Wait for valid pulse, capture inputs
                IDLE: begin
                    m_axis_tvalid <= 1'b0;
                    m_axis_tlast  <= 1'b0;
                    if (valid) begin
                        sig_reg   <= signal_out;
                        phase_reg <= phase_out;
                        ts_reg    <= timestamp;
                        word_idx  <= 2'd0;
                        state     <= OUTPUT;
                    end
                end

                // Stream 4 words to DMA.  Every word — including the last —
                // is held stable until the DMA accepts it (tvalid && tready).
                // word_idx is the index of the word currently on the bus.
                OUTPUT: begin
                    if (!m_axis_tvalid) begin
                        // present first word of this sample
                        m_axis_tvalid <= 1'b1;
                        m_axis_tdata  <= sig_reg;
                        m_axis_tlast  <= 1'b0;
                    end else if (m_axis_tready) begin
                        // current word accepted
                        if (word_idx == 2'd3) begin
                            // last word of sample accepted — only now is it
                            // safe to drop tvalid/tlast and leave OUTPUT
                            m_axis_tvalid <= 1'b0;
                            m_axis_tlast  <= 1'b0;
                            word_idx      <= 2'd0;
                            if (sample_idx == SAMPLES_PER_PACKET - 1)
                                sample_idx <= 0;
                            else
                                sample_idx <= sample_idx + 1;
                            state <= IDLE;
                        end else begin
                            word_idx <= word_idx + 1;
                            case (word_idx)
                                2'd0: m_axis_tdata <= phase_reg;
                                2'd1: m_axis_tdata <= ts_reg[31:0];
                                2'd2: m_axis_tdata <= ts_reg[63:32];
                                default: m_axis_tdata <= 32'h0;
                            endcase
                            // TLAST accompanies word 3 of the packet's final
                            // sample and holds until that beat is accepted.
                            m_axis_tlast <= (word_idx == 2'd2) &&
                                            (sample_idx == SAMPLES_PER_PACKET - 1);
                        end
                    end
                end

                default: state <= IDLE;

            endcase
        end
    end

endmodule