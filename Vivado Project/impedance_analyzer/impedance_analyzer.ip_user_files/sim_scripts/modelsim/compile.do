vlib modelsim_lib/work
vlib modelsim_lib/msim

vlib modelsim_lib/msim/xpm
vlib modelsim_lib/msim/fifo_generator_v13_2_14
vlib modelsim_lib/msim/xil_defaultlib
vlib modelsim_lib/msim/xbip_utils_v3_0_15
vlib modelsim_lib/msim/c_reg_fd_v12_0_11
vlib modelsim_lib/msim/xbip_dsp48_wrapper_v3_0_7
vlib modelsim_lib/msim/xbip_pipe_v3_0_11
vlib modelsim_lib/msim/c_addsub_v12_0_21
vlib modelsim_lib/msim/mult_gen_v12_0_24
vlib modelsim_lib/msim/axi_utils_v2_0_11
vlib modelsim_lib/msim/cordic_v6_0_25

vmap xpm modelsim_lib/msim/xpm
vmap fifo_generator_v13_2_14 modelsim_lib/msim/fifo_generator_v13_2_14
vmap xil_defaultlib modelsim_lib/msim/xil_defaultlib
vmap xbip_utils_v3_0_15 modelsim_lib/msim/xbip_utils_v3_0_15
vmap c_reg_fd_v12_0_11 modelsim_lib/msim/c_reg_fd_v12_0_11
vmap xbip_dsp48_wrapper_v3_0_7 modelsim_lib/msim/xbip_dsp48_wrapper_v3_0_7
vmap xbip_pipe_v3_0_11 modelsim_lib/msim/xbip_pipe_v3_0_11
vmap c_addsub_v12_0_21 modelsim_lib/msim/c_addsub_v12_0_21
vmap mult_gen_v12_0_24 modelsim_lib/msim/mult_gen_v12_0_24
vmap axi_utils_v2_0_11 modelsim_lib/msim/axi_utils_v2_0_11
vmap cordic_v6_0_25 modelsim_lib/msim/cordic_v6_0_25

vlog -work xpm  -incr -mfcu  -sv "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_cdc/hdl/xpm_cdc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_memory/hdl/xpm_memory.sv" \

vcom -work xpm  -93  \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_VCOMP.vhd" \

vlog -work fifo_generator_v13_2_14  -incr -mfcu  "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" \
"../../ipstatic/simulation/fifo_generator_vlog_beh.v" \

vcom -work fifo_generator_v13_2_14  -93  \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.vhd" \

vlog -work fifo_generator_v13_2_14  -incr -mfcu  "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.v" \

vlog -work xil_defaultlib  -incr -mfcu  "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" \
"../../../impedance_analyzer.gen/sources_1/ip/wave_delay_fifo/sim/wave_delay_fifo.v" \

vcom -work xbip_utils_v3_0_15  -93  \
"../../ipstatic/hdl/xbip_utils_v3_0_vh_rfs.vhd" \

vcom -work c_reg_fd_v12_0_11  -93  \
"../../ipstatic/hdl/c_reg_fd_v12_0_vh_rfs.vhd" \

vcom -work xbip_dsp48_wrapper_v3_0_7  -93  \
"../../ipstatic/hdl/xbip_dsp48_wrapper_v3_0_vh_rfs.vhd" \

vcom -work xbip_pipe_v3_0_11  -93  \
"../../ipstatic/hdl/xbip_pipe_v3_0_vh_rfs.vhd" \

vcom -work c_addsub_v12_0_21  -93  \
"../../ipstatic/hdl/c_addsub_v12_0_vh_rfs.vhd" \

vcom -work mult_gen_v12_0_24  -93  \
"../../ipstatic/hdl/mult_gen_v12_0_vh_rfs.vhd" \

vcom -work axi_utils_v2_0_11  -93  \
"../../ipstatic/hdl/axi_utils_v2_0_vh_rfs.vhd" \

vcom -work cordic_v6_0_25  -93  \
"../../ipstatic/hdl/cordic_v6_0_vh_rfs.vhd" \

vcom -work xil_defaultlib  -93  \
"../../../impedance_analyzer.gen/sources_1/ip/DDS_Generator/sim/DDS_Generator.vhd" \

vlog -work xil_defaultlib  -incr -mfcu  "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" \
"../../../impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver.v" \
"../../../impedance_analyzer.gen/sources_1/ip/ADC_Input/ADC_Input_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/ADC_Input/ADC_Input.v" \

vlog -work xil_defaultlib \
"glbl.v"

