// system-level state machine for impedance analyzer measurement flow
// controls pipeline reset, startup sequencing, calibration, and run/stop
// Author: Alex Clunan
module state_machine
(
    input                   clock,
    input                   reset_n,
    // PS command interface (REG10)
    input   [31:0]          state_machine_ctrl,
    output  [31:0]          state_machine_status,
    // pipeline control
    output                  pipeline_reset_n,
    output                  processing_enable,
    // CIC config trigger (single-cycle pulse)
    output                  cic_config_load,
    // FIR reload status (from PS via REG5)
    input                   fir_reload_done,
    // calibration handshake
    output                  calibration_start,
    output                  calibration_armed,
    input                   tx_timestamp_valid,
    input                   rx_timestamp_valid);

// state encoding
localparam [3:0] STATE_IDLE         = 4'd0;
localparam [3:0] STATE_CONFIGURE    = 4'd1;
localparam [3:0] STATE_STARTUP_CIC  = 4'd2;
localparam [3:0] STATE_STARTUP_FIR  = 4'd3;
localparam [3:0] STATE_RUN          = 4'd4;
localparam [3:0] STATE_STOP         = 4'd5;
localparam [3:0] STATE_CAL_START    = 4'd6;
localparam [3:0] STATE_CAL_ARM      = 4'd7;
localparam [3:0] STATE_CAL_DONE     = 4'd8;

// command encoding (from ctrl[3:0])
localparam [3:0] CMD_NOP       = 4'd0;
localparam [3:0] CMD_CONFIGURE = 4'd1;
localparam [3:0] CMD_START     = 4'd2;
localparam [3:0] CMD_STOP      = 4'd3;
localparam [3:0] CMD_CALIBRATE = 4'd4;

// state and command registers
reg [3:0] current_state;
reg [3:0] prev_cmd;

// output registers
reg pipeline_reset_n_reg;
reg processing_enable_reg;
reg cic_config_load_reg;
reg calibration_start_reg;
reg calibration_armed_reg;
reg calibration_done_reg;

// command extraction and edge detection
wire [3:0] cmd = state_machine_ctrl[3:0];
wire cmd_edge = (cmd != CMD_NOP) && (cmd != prev_cmd);

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        current_state        <= STATE_IDLE;
        prev_cmd             <= CMD_NOP;
        pipeline_reset_n_reg <= 1'b0;
        processing_enable_reg <= 1'b0;
        cic_config_load_reg  <= 1'b0;
        calibration_start_reg <= 1'b0;
        calibration_armed_reg <= 1'b0;
        calibration_done_reg <= 1'b0;

    end else begin
        prev_cmd            <= cmd;
        cic_config_load_reg <= 1'b0; // default: single-cycle pulse

        case (current_state)
            STATE_IDLE: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                calibration_start_reg <= 1'b0;
                calibration_armed_reg <= 1'b0;

                if (cmd_edge) begin
                    case (cmd)
                        CMD_CONFIGURE: current_state <= STATE_CONFIGURE;
                        CMD_CALIBRATE: begin
                            current_state <= STATE_CAL_START;
                            calibration_done_reg <= 1'b0;
                        end
                        default: ; // ignore invalid commands
                    endcase
                end
            end

            STATE_CONFIGURE: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;

                if (cmd_edge && cmd == CMD_START) begin
                    current_state       <= STATE_STARTUP_CIC;
                    cic_config_load_reg <= 1'b1;
                end
            end

            STATE_STARTUP_CIC: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                // CIC config pulse was asserted on entry; advance after one cycle
                current_state <= STATE_STARTUP_FIR;
            end

            STATE_STARTUP_FIR: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;

                if (fir_reload_done == 1'b1) begin
                    current_state         <= STATE_RUN;
                    pipeline_reset_n_reg  <= 1'b1;
                    processing_enable_reg <= 1'b1;
                end
            end

            STATE_RUN: begin
                pipeline_reset_n_reg  <= 1'b1;
                processing_enable_reg <= 1'b1;

                if (cmd_edge && cmd == CMD_STOP) begin
                    current_state         <= STATE_STOP;
                    pipeline_reset_n_reg  <= 1'b0;
                    processing_enable_reg <= 1'b0;
                end
            end

            STATE_STOP: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                current_state         <= STATE_IDLE;
            end

            STATE_CAL_START: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                calibration_start_reg <= 1'b1;

                if (tx_timestamp_valid == 1'b1) begin
                    current_state         <= STATE_CAL_ARM;
                    calibration_armed_reg <= 1'b1;
                end
            end

            STATE_CAL_ARM: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                calibration_start_reg <= 1'b1;
                calibration_armed_reg <= 1'b1;

                if (rx_timestamp_valid == 1'b1) begin
                    current_state <= STATE_CAL_DONE;
                end
            end

            STATE_CAL_DONE: begin
                pipeline_reset_n_reg  <= 1'b0;
                processing_enable_reg <= 1'b0;
                calibration_start_reg <= 1'b0;
                calibration_armed_reg <= 1'b0;
                calibration_done_reg  <= 1'b1;
                current_state         <= STATE_IDLE;
            end

            default: current_state <= STATE_IDLE;
        endcase
    end
end

// status register: [3:0]=state, [4]=pipeline_active, [5]=calibration_done
assign state_machine_status = {26'b0,
                               calibration_done_reg,
                               processing_enable_reg,
                               current_state};

assign pipeline_reset_n  = pipeline_reset_n_reg;
assign processing_enable = processing_enable_reg;
assign cic_config_load   = cic_config_load_reg;
assign calibration_start = calibration_start_reg;
assign calibration_armed = calibration_armed_reg;

endmodule
