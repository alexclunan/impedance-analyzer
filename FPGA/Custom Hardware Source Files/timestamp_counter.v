// free-running 64-bit timestamp counter for measurement timing
// Author: Alex Clunan
module timestamp_counter
    // counter parameters
    #(parameter COUNT_WIDTH = 64)
(
    input                       clock,
    input                       reset_n,
    // timestamp output
    output  [COUNT_WIDTH-1:0]   timestamp);

// counter register
reg [COUNT_WIDTH-1:0] count;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        count <= {COUNT_WIDTH{1'b0}};

    // increment
    end else begin
        count <= count + {{(COUNT_WIDTH-1){1'b0}}, 1'b1};
    end
end

assign timestamp = count;

endmodule
