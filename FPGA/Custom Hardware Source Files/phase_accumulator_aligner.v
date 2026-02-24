
// Author: Alex Clunan

module phase_accumulator_aligner
(
    input           clock,
    input           reset_n,
    // lower speed DDS to sync to
    input master_dds_msb,

    input  [63:0]   original_fcw,
    output [63:0]   adjusted_fcw);
    
    reg [63:0] adjusted_fcw_register;
    
    always @(posedge(clock) or negedge(reset_n)) begin
        if (reset_n == 0) begin
            accumulated_phase <= 0;
        end else begin
            accumulated_phase <= accumulated_phase + fcw;
        end
    end
    
    assign phase_out = accumulated_phase[63:48];
    
endmodule
