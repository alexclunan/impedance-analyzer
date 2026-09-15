// decimator and low-pass filter wrapper for one I or Q channel
// handles AXI-Stream plumbing between CIC and FIR, config loading, enable gating
// Author: Alex Clunan
module decimator_lpf_wrapper
    // data width parameters
    #(parameter DATA_WIDTH   = 32,
      parameter CONFIG_WIDTH = 16,
      parameter RELOAD_WIDTH = 24)
(
    input                       clock,
    input                       aresetn,
    // mixer data input
    input   [DATA_WIDTH-1:0]    data_in,
    input                       data_valid,
    // pipeline control
    input                       processing_enable,
    // CIC decimation ratio configuration
    input   [CONFIG_WIDTH-1:0]  decimation_ratio,
    input                       config_load,
    // FIR coefficient reload (from PS)
    input   [RELOAD_WIDTH-1:0]  fir_reload_data,
    input                       fir_reload_valid,
    input                       fir_reload_last,
    // filtered output
    output  [DATA_WIDTH-1:0]    data_out,
    output                      data_valid_out,
    // CIC IP interface (active-low reset exposed separately)
    output  [DATA_WIDTH-1:0]    cic_s_axis_data_tdata,
    output                      cic_s_axis_data_tvalid,
    output  [CONFIG_WIDTH-1:0]  cic_s_axis_config_tdata,
    output                      cic_s_axis_config_tvalid,
    input   [DATA_WIDTH-1:0]    cic_m_axis_data_tdata,
    input                       cic_m_axis_data_tvalid,
    // FIR IP interface
    output  [DATA_WIDTH-1:0]    fir_s_axis_data_tdata,
    output                      fir_s_axis_data_tvalid,
    output  [RELOAD_WIDTH-1:0]  fir_s_axis_reload_tdata,
    output                      fir_s_axis_reload_tvalid,
    output                      fir_s_axis_reload_tlast,
    input   [DATA_WIDTH-1:0]    fir_m_axis_data_tdata,
    input                       fir_m_axis_data_tvalid);

// CIC config loading: pulse config_tvalid for one cycle on config_load
reg config_pending;
reg cic_config_tvalid_reg;
reg [CONFIG_WIDTH-1:0] cic_config_tdata_reg;

always @(posedge clock or negedge aresetn) begin
    if (aresetn == 1'b0) begin
        config_pending        <= 1'b0;
        cic_config_tvalid_reg <= 1'b0;
        cic_config_tdata_reg  <= {CONFIG_WIDTH{1'b0}};
    end else begin
        if (config_load && !config_pending) begin
            cic_config_tdata_reg  <= decimation_ratio;
            cic_config_tvalid_reg <= 1'b1;
            config_pending        <= 1'b1;
        end else begin
            cic_config_tvalid_reg <= 1'b0;
        end

        if (!config_load)
            config_pending <= 1'b0;
    end
end

// CIC data input: gate with processing_enable
assign cic_s_axis_data_tdata   = data_in;
assign cic_s_axis_data_tvalid  = data_valid && processing_enable;
assign cic_s_axis_config_tdata  = cic_config_tdata_reg;
assign cic_s_axis_config_tvalid = cic_config_tvalid_reg;

// CIC output -> FIR input (direct AXI-Stream connection)
assign fir_s_axis_data_tdata  = cic_m_axis_data_tdata;
assign fir_s_axis_data_tvalid = cic_m_axis_data_tvalid;

// FIR reload passthrough
assign fir_s_axis_reload_tdata  = fir_reload_data;
assign fir_s_axis_reload_tvalid = fir_reload_valid;
assign fir_s_axis_reload_tlast  = fir_reload_last;

// filtered output from FIR
assign data_out       = fir_m_axis_data_tdata;
assign data_valid_out = fir_m_axis_data_tvalid;

endmodule
