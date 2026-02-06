`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 02/05/2026 01:31:28 PM
// Design Name: 
// Module Name: phase_accumulator
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module phase_accumulator(
    input clock,
    input rst_n,
    input [47:0] fcw,
    output [15:0] phase_out
    );
    
    reg [47:0] accumulated_phase;
    
    always @(posedge clock or negedge rst_n) begin
        if (!rst_n) begin
            accumulated_phase <= 0;
        end else begin
            accumulated_phase <= accumulated_phase + fcw;
        end
    end
    
    
    assign phase_out = accumulated_phase[47:32];
    
    
endmodule
