// continuous master-slave phase synchronizer across DAC/ADC clock domains
// double-flop CDC on master MSB, edge detect, correction output to slave
// Author: Alex Clunan
module phase_synchronizer
    // width parameters
    #(parameter FCW_WIDTH = 48)
(
    input                       dac_clock,
    input                       adc_clock,
    input                       reset_n,
    // master phase accumulator MSB (DAC domain)
    input                       dac_phase_msb,
    // slave phase accumulator MSB (ADC domain, feedback)
    input                       slave_phase_msb,
    // frequency control word (static during operation)
    input   [FCW_WIDTH-1:0]     fcw,
    // synchronized outputs (ADC domain)
    output                      synced_phase_msb,
    output  [FCW_WIDTH-1:0]     synced_fcw,
    // correction to slave: 2'b01 = +1, 2'b00 = 0, 2'b11 = -1
    output  [1:0]               correction);

// DAC domain: register input for clean CDC launch point
reg dac_msb_reg;

always @(posedge dac_clock or negedge reset_n) begin
    if (reset_n == 1'b0)
        dac_msb_reg <= 1'b0;
    else
        dac_msb_reg <= dac_phase_msb;
end

// ADC domain: double-flop synchronizer
reg msb_meta, msb_sync;

always @(posedge adc_clock or negedge reset_n) begin
    if (reset_n == 1'b0) begin
        msb_meta <= 1'b0;
        msb_sync <= 1'b0;
    end else begin
        msb_meta <= dac_msb_reg;
        msb_sync <= msb_meta;
    end
end

// edge detector and correction logic
reg msb_sync_prev;
reg [1:0] correction_reg;

always @(posedge adc_clock or negedge reset_n) begin
    if (reset_n == 1'b0) begin
        msb_sync_prev  <= 1'b0;
        correction_reg <= 2'b00;

    end else begin
        msb_sync_prev <= msb_sync;

        // on detected master MSB transition, compare with slave
        if (msb_sync != msb_sync_prev) begin
            if (msb_sync != slave_phase_msb)
                correction_reg <= 2'b01;
            else
                correction_reg <= 2'b00;

        // no edge: no correction
        end else begin
            correction_reg <= 2'b00;
        end
    end
end

// FCW registered into ADC domain (static, captured after reset release)
reg [FCW_WIDTH-1:0] fcw_adc;

always @(posedge adc_clock or negedge reset_n) begin
    if (reset_n == 1'b0)
        fcw_adc <= {FCW_WIDTH{1'b0}};
    else
        fcw_adc <= fcw;
end

assign synced_phase_msb = msb_sync;
assign synced_fcw       = fcw_adc;
assign correction       = correction_reg;

endmodule
