// parameterized N-to-1 multiplexer
// selects one of N input words (each WIDTH bits) onto the output
// Author: Alex Clunan
module mux
    // configuration parameters
    #(parameter N        = 4,                 // number of inputs
      parameter WIDTH    = 16,                // bit width of each input/output
      parameter SEL_BITS = $clog2(N))         // select line width
(
    input                       clk,
    // flattened input bus: input i occupies bits [i*WIDTH +: WIDTH]
    input   [N*WIDTH-1:0]       data_in,
    // select line
    input   [SEL_BITS-1:0]      sel,
    // selected output
    output  reg [WIDTH-1:0]     data_out);

always @(posedge(clk)) begin
    // index out the selected slice
    data_out <= data_in[sel*WIDTH +: WIDTH];
end
   

endmodule
