// Handles DAC output at 200 MHz
// Author: Alex Clunan

module DAC_driver_top 
    #(parameter WIDTH = 16,
      parameter AXI_REGISTER_SIZE = 32) 
(
    // configuration setup 
    input [AXI_REGISTER_SIZE-1:0] axi_config0,
    input [AXI_REGISTER_SIZE-1:0] axi_config1,
    input [AXI_REGISTER_SIZE-1:0] axi_config2,
    input [AXI_REGISTER_SIZE-1:0] axi_config3,
    input [AXI_REGISTER_SIZE-1:0] axi_config4,
    input [AXI_REGISTER_SIZE-1:0] axi_config5,
    input [AXI_REGISTER_SIZE-1:0] axi_config6,

    // DAC Output
    output [WIDTH-1:0] DAC_output
);