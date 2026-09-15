vlib questa_lib/work
vlib questa_lib/msim

vlib questa_lib/msim/xilinx_vip
vlib questa_lib/msim/xpm
vlib questa_lib/msim/xil_defaultlib

vmap xilinx_vip questa_lib/msim/xilinx_vip
vmap xpm questa_lib/msim/xpm
vmap xil_defaultlib questa_lib/msim/xil_defaultlib

vlog -work xilinx_vip  -incr -mfcu  -sv -L smartconnect_v1_0 -L axi_vip_v1_1_22 -L processing_system7_vip_v1_0_24 -L xilinx_vip "+incdir+C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/include" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi4stream_vip_axi4streampc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi_vip_axi4pc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/xil_common_vip_pkg.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi4stream_vip_pkg.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi_vip_pkg.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi4stream_vip_if.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/axi_vip_if.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/clk_vip_if.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/hdl/rst_vip_if.sv" \

vlog -work xpm  -incr -mfcu  -sv -L smartconnect_v1_0 -L axi_vip_v1_1_22 -L processing_system7_vip_v1_0_24 -L xilinx_vip "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" "+incdir+../../../../ip_repo/Configuration_Register_1_0/drivers/Configuration_Register_v1_0/src" "+incdir+../../../../ip_repo/AXI_register_file_1_0/drivers/AXI_register_file_v1_0/src" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/ec67/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/9a25/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/f0b6/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/00fe/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/434f/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/a415" "+incdir+C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/include" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_cdc/hdl/xpm_cdc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_fifo/hdl/xpm_fifo.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_memory/hdl/xpm_memory.sv" \

vcom -work xpm  -93  \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_VCOMP.vhd" \

vlog -work xil_defaultlib  -incr -mfcu  "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" "+incdir+../../../../ip_repo/Configuration_Register_1_0/drivers/Configuration_Register_v1_0/src" "+incdir+../../../../ip_repo/AXI_register_file_1_0/drivers/AXI_register_file_v1_0/src" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/ec67/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/9a25/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/f0b6/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/00fe/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/434f/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/a415" "+incdir+C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/include" \
"../../../../../FPGA/Custom Hardware Source Files/phase_accumulator.v" \

vlog -work xil_defaultlib  -incr -mfcu  -sv -L smartconnect_v1_0 -L axi_vip_v1_1_22 -L processing_system7_vip_v1_0_24 -L xilinx_vip "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" "+incdir+../../../../ip_repo/Configuration_Register_1_0/drivers/Configuration_Register_v1_0/src" "+incdir+../../../../ip_repo/AXI_register_file_1_0/drivers/AXI_register_file_v1_0/src" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/ec67/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/9a25/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/f0b6/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/00fe/hdl/verilog" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/434f/hdl" "+incdir+../../../impedance_analyzer.gen/sources_1/bd/full_design/ipshared/a415" "+incdir+C:/AMDDesignTools/2025.2/Vivado/data/xilinx_vip/include" \
"../../../../../FPGA/testbenches/tb_phase_accumulator.sv" \

vlog -work xil_defaultlib \
"glbl.v"

