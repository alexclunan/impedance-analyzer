// adc_bit_reorder.v
// Author: Alex Clunan
//
// Pure combinational deinterleave of the AD9467 DDR-interleaved capture word.
// ONLY reorders bits -- no clocking, no latency.
//
// Input `din[17:0]` is adc_lvds_capture's data_in_to_device (SYS_W=9, DEV_W=18):
//   din[i]     = IDDR Q1 (rising edge)  of pair i,  i = 0..8   -> bits [8:0]
//   din[9+i]   = IDDR Q2 (falling edge) of pair i,  i = 0..8   -> bits [17:9]
//
// Each LVDS pair carries two data bits (DDR). Per the board FMC net table, pair i
// (= adc_inputp[i]) carries D(2i+1)/D(2i); pair 8 is OR (over-range):
//   pair0 F18 D1/D0    pair1 E15 D3/D2    pair2 F16 D5/D4    pair3 A21 D7/D6
//   pair4 E21 D9/D8    pair5 G15 D11/D10  pair6 G19 D13/D12  pair7 G20 D15/D14
//   pair8 D18 OR
//
// MSB-first (D15 first): the rising-edge sample (Q1, din[i]) is the odd/upper bit
// D(2i+1); the falling-edge sample (Q2, din[9+i]) is the even/lower bit D(2i).
// If the data comes out still scrambled (i.e. the DCO phase makes the falling edge
// the "first" bit), set MSB_ON_RISING = 0 to swap the edge assignment.
module adc_bit_reorder
    #(parameter MSB_ON_RISING = 1)
(
    input  wire [17:0] din,        // raw captured word (adc_lvds_capture / FIFO out)
    output wire [17:0] adc_data   // reassembled D[15:0], two's complement
);

    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : reorder
            if (MSB_ON_RISING) begin : msb_rise
                assign adc_data[2*i+1] = din[i];     // odd  D(2i+1) on rising  (Q1)
                assign adc_data[2*i]   = din[9+i];   // even D(2i)   on falling (Q2)
            end else begin : msb_fall
                assign adc_data[2*i+1] = din[9+i];   // odd  D(2i+1) on falling (Q2)
                assign adc_data[2*i]   = din[i];     // even D(2i)   on rising  (Q1)
            end
        end
    endgenerate

    // OR (over-range), pin index 8
    assign adc_data[16] = din[8];     // rising-edge OR sample
    assign adc_data[17] = din[17];    // falling-edge OR sample

endmodule
