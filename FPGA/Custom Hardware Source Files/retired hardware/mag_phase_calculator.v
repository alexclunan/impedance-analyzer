// magnitude and phase calculator wrapper for CORDIC vectoring IP
// packs I/Q into CORDIC input, unpacks magnitude and phase from output
// Author: Alex Clunan
module mag_phase_calculator
    // data width parameters
    #(parameter DATA_WIDTH    = 32,
      parameter CORDIC_WIDTH  = 64)
(
    input                           clock,
    input                           reset_n,
    // clock enable (decimated rate)
    input                           ce,
    // I/Q input from decimator
    input   [DATA_WIDTH-1:0]        i_in,
    input   [DATA_WIDTH-1:0]        q_in,
    input                           valid_in,
    // magnitude and phase output
    output  [DATA_WIDTH-1:0]        magnitude,
    output  [DATA_WIDTH-1:0]        phase,
    output                          valid_out,
    // CORDIC IP interface (exposed for top-level connection)
    output  [CORDIC_WIDTH-1:0]      cordic_s_axis_cartesian_tdata,
    output                          cordic_s_axis_cartesian_tvalid,
    input   [CORDIC_WIDTH-1:0]      cordic_m_axis_dout_tdata,
    input                           cordic_m_axis_dout_tvalid);

// pack I (X) into lower half, Q (Y) into upper half per CORDIC convention
reg [CORDIC_WIDTH-1:0]  cartesian_tdata_reg;
reg                     cartesian_tvalid_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        cartesian_tdata_reg  <= {CORDIC_WIDTH{1'b0}};
        cartesian_tvalid_reg <= 1'b0;

    // gate with clock enable
    end else if (ce == 1'b1) begin
        cartesian_tdata_reg  <= {q_in, i_in};
        cartesian_tvalid_reg <= valid_in;

    end else begin
        cartesian_tvalid_reg <= 1'b0;
    end
end

assign cordic_s_axis_cartesian_tdata  = cartesian_tdata_reg;
assign cordic_s_axis_cartesian_tvalid = cartesian_tvalid_reg;

// unpack CORDIC output: magnitude in lower half, phase in upper half
reg [DATA_WIDTH-1:0] magnitude_reg;
reg [DATA_WIDTH-1:0] phase_reg;
reg                  valid_out_reg;

always @(posedge clock or negedge reset_n) begin
    // asynchronous low reset
    if (reset_n == 1'b0) begin
        magnitude_reg <= {DATA_WIDTH{1'b0}};
        phase_reg     <= {DATA_WIDTH{1'b0}};
        valid_out_reg <= 1'b0;

    // register CORDIC output
    end else begin
        magnitude_reg <= cordic_m_axis_dout_tdata[DATA_WIDTH-1:0];
        phase_reg     <= cordic_m_axis_dout_tdata[CORDIC_WIDTH-1:DATA_WIDTH];
        valid_out_reg <= cordic_m_axis_dout_tvalid;
    end
end

assign magnitude = magnitude_reg;
assign phase     = phase_reg;
assign valid_out = valid_out_reg;

endmodule
