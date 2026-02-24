
// Author: Alex Clunan

module phase_accumulator
(
    input           clock,
    input           reset_n,
    input  [63:0]   fcw,
    output [15:0]   phase_out);
    
    reg [63:0] accumulated_phase;
    
    always @(posedge(clock) or negedge(reset_n)) begin
        if (reset_n == 0) begin
            accumulated_phase <= 0;
        end else begin
            accumulated_phase <= accumulated_phase + fcw;
        end
    end
    
    assign phase_out = accumulated_phase[63:48];
    
endmodule
