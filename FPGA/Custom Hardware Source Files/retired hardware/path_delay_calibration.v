// path delay calibration for analog round-trip measurement
// DAC-side step generator + ADC-side threshold detector, dual clock domain
// Author: Alex Clunan
module path_delay_calibration
    // width and timing parameters
    #(parameter DATA_WIDTH      = 16,
      parameter TIMESTAMP_WIDTH = 64,
      parameter SETTLE_CYCLES   = 100)
(
    // DAC domain (step generator)
    input                           dac_clock,
    input                           reset_n,
    input                           calibration_start,
    input   [TIMESTAMP_WIDTH-1:0]   dac_timestamp,
    output  [DATA_WIDTH-1:0]        test_pulse_data,
    output                          test_mode,
    output  [TIMESTAMP_WIDTH-1:0]   tx_timestamp,
    output                          tx_timestamp_valid,
    // ADC domain (threshold detector)
    input                           adc_clock,
    input                           calibration_armed,
    input   [DATA_WIDTH-1:0]        adc_sample,
    input   [DATA_WIDTH-1:0]        threshold,
    input   [TIMESTAMP_WIDTH-1:0]   adc_timestamp,
    output  [TIMESTAMP_WIDTH-1:0]   rx_timestamp,
    output                          rx_timestamp_valid);

// mid-scale (zero) and full-scale positive constants
localparam [DATA_WIDTH-1:0] MID_SCALE  = {DATA_WIDTH{1'b0}};
localparam [DATA_WIDTH-1:0] FULL_SCALE = {1'b0, {(DATA_WIDTH-1){1'b1}}};

// ===== DAC-side step generator (dac_clock domain) =====

localparam [1:0] DAC_IDLE    = 2'b00;
localparam [1:0] DAC_SETTLE  = 2'b01;
localparam [1:0] DAC_STEPPED = 2'b10;

reg [1:0]                   dac_state;
reg [15:0]                  settle_count;
reg [DATA_WIDTH-1:0]        test_pulse_reg;
reg                         test_mode_reg;
reg [TIMESTAMP_WIDTH-1:0]   tx_timestamp_reg;
reg                         tx_valid_reg;

always @(posedge dac_clock or negedge reset_n) begin
    if (reset_n == 1'b0) begin
        dac_state       <= DAC_IDLE;
        settle_count    <= 16'd0;
        test_pulse_reg  <= MID_SCALE;
        test_mode_reg   <= 1'b0;
        tx_timestamp_reg <= {TIMESTAMP_WIDTH{1'b0}};
        tx_valid_reg    <= 1'b0;

    end else begin
        case (dac_state)
            DAC_IDLE: begin
                test_pulse_reg <= MID_SCALE;
                test_mode_reg  <= 1'b0;
                tx_valid_reg   <= 1'b0;
                if (calibration_start == 1'b1) begin
                    dac_state     <= DAC_SETTLE;
                    test_mode_reg <= 1'b1;
                    settle_count  <= 16'd0;
                end
            end

            DAC_SETTLE: begin
                test_pulse_reg <= MID_SCALE;
                test_mode_reg  <= 1'b1;
                if (settle_count >= SETTLE_CYCLES - 1) begin
                    dac_state        <= DAC_STEPPED;
                    test_pulse_reg   <= FULL_SCALE;
                    tx_timestamp_reg <= dac_timestamp;
                    tx_valid_reg     <= 1'b1;
                end else begin
                    settle_count <= settle_count + 16'd1;
                end
            end

            DAC_STEPPED: begin
                test_pulse_reg <= FULL_SCALE;
                test_mode_reg  <= 1'b1;
                tx_valid_reg   <= 1'b1;
                if (calibration_start == 1'b0) begin
                    dac_state <= DAC_IDLE;
                end
            end

            default: dac_state <= DAC_IDLE;
        endcase
    end
end

assign test_pulse_data   = test_pulse_reg;
assign test_mode         = test_mode_reg;
assign tx_timestamp      = tx_timestamp_reg;
assign tx_timestamp_valid = tx_valid_reg;

// ===== ADC-side threshold detector (adc_clock domain) =====

reg [TIMESTAMP_WIDTH-1:0]   rx_timestamp_reg;
reg                         rx_valid_reg;

always @(posedge adc_clock or negedge reset_n) begin
    if (reset_n == 1'b0) begin
        rx_timestamp_reg <= {TIMESTAMP_WIDTH{1'b0}};
        rx_valid_reg     <= 1'b0;

    end else begin
        // clear when not armed (allows re-use across calibration runs)
        if (calibration_armed == 1'b0) begin
            rx_valid_reg <= 1'b0;

        // detect threshold crossing (signed comparison, capture once)
        end else if (calibration_armed == 1'b1 && rx_valid_reg == 1'b0 &&
                     $signed(adc_sample) >= $signed(threshold)) begin
            rx_timestamp_reg <= adc_timestamp;
            rx_valid_reg     <= 1'b1;
        end
    end
end

assign rx_timestamp       = rx_timestamp_reg;
assign rx_timestamp_valid = rx_valid_reg;

endmodule
