// triggering and detection logic for impedance measurements
// monitors magnitude and/or phase for configurable threshold crossings
// Author: Alex Clunan
module trigger_logic
    // data width parameter
    #(parameter DATA_WIDTH = 32)
(
    input                       clock,
    input                       reset_n,
    // measurement inputs (decimated rate, from mag/phase calculator)
    input   [DATA_WIDTH-1:0]    magnitude,
    input   [DATA_WIDTH-1:0]    corrected_phase,
    input                       data_valid,
    // configuration (from registers)
    input   [DATA_WIDTH-1:0]    trigger_threshold,
    input   [DATA_WIDTH-1:0]    trigger_config,
    // trigger outputs
    output                      trigger_flag,
    output                      gpio_out);

// config field extraction
// [1:0] mode: 00=disabled, 01=magnitude, 10=phase, 11=either
// [2]   edge: 0=rising (above), 1=falling (below)
wire [1:0] trigger_mode = trigger_config[1:0];
wire       trigger_edge = trigger_config[2];

// signed threshold comparison
wire mag_above   = ($signed(magnitude)       >= $signed(trigger_threshold));
wire phase_above = ($signed(corrected_phase) >= $signed(trigger_threshold));

// crossing detection (combinational, uses registered previous values)
wire mag_rising    = mag_above   && !prev_mag_above;
wire mag_falling   = !mag_above  && prev_mag_above;
wire phase_rising  = phase_above && !prev_phase_above;
wire phase_falling = !phase_above && prev_phase_above;

wire mag_crossing   = trigger_edge ? mag_falling   : mag_rising;
wire phase_crossing = trigger_edge ? phase_falling  : phase_rising;

// state registers
reg prev_mag_above;
reg prev_phase_above;
reg trigger_flag_reg;
reg gpio_out_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        prev_mag_above   <= 1'b0;
        prev_phase_above <= 1'b0;
        trigger_flag_reg <= 1'b0;
        gpio_out_reg     <= 1'b0;

    end else begin
        // single-cycle pulse: default low
        trigger_flag_reg <= 1'b0;

        // update only on valid data (decimated rate)
        if (data_valid == 1'b1) begin
            prev_mag_above   <= mag_above;
            prev_phase_above <= phase_above;

            case (trigger_mode)
                2'b01:   trigger_flag_reg <= mag_crossing;
                2'b10:   trigger_flag_reg <= phase_crossing;
                2'b11:   trigger_flag_reg <= mag_crossing | phase_crossing;
                default: trigger_flag_reg <= 1'b0;
            endcase
        end

        // GPIO latches on trigger, cleared only by reset
        if (trigger_flag_reg == 1'b1)
            gpio_out_reg <= 1'b1;
    end
end

assign trigger_flag = trigger_flag_reg;
assign gpio_out     = gpio_out_reg;

endmodule
