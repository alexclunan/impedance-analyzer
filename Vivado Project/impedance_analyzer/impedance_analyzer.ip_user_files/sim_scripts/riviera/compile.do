transcript off
onbreak {quit -force}
onerror {quit -force}
transcript on

vlib work
vlib riviera/xpm
vlib riviera/fifo_generator_v13_2_14
vlib riviera/xil_defaultlib
vlib riviera/xbip_utils_v3_0_15
vlib riviera/c_reg_fd_v12_0_11
vlib riviera/xbip_dsp48_wrapper_v3_0_7
vlib riviera/xbip_pipe_v3_0_11
vlib riviera/c_addsub_v12_0_21
vlib riviera/mult_gen_v12_0_24
vlib riviera/axi_utils_v2_0_11
vlib riviera/cordic_v6_0_25

vmap xpm riviera/xpm
vmap fifo_generator_v13_2_14 riviera/fifo_generator_v13_2_14
vmap xil_defaultlib riviera/xil_defaultlib
vmap xbip_utils_v3_0_15 riviera/xbip_utils_v3_0_15
vmap c_reg_fd_v12_0_11 riviera/c_reg_fd_v12_0_11
vmap xbip_dsp48_wrapper_v3_0_7 riviera/xbip_dsp48_wrapper_v3_0_7
vmap xbip_pipe_v3_0_11 riviera/xbip_pipe_v3_0_11
vmap c_addsub_v12_0_21 riviera/c_addsub_v12_0_21
vmap mult_gen_v12_0_24 riviera/mult_gen_v12_0_24
vmap axi_utils_v2_0_11 riviera/axi_utils_v2_0_11
vmap cordic_v6_0_25 riviera/cordic_v6_0_25

vlog -work xpm  -incr "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l xbip_pipe_v3_0_11 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l axi_utils_v2_0_11 -l cordic_v6_0_25 \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_cdc/hdl/xpm_cdc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_memory/hdl/xpm_memory.sv" \

vcom -work xpm -93  -incr \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_VCOMP.vhd" \

vlog -work fifo_generator_v13_2_14  -incr -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l xbip_pipe_v3_0_11 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l axi_utils_v2_0_11 -l cordic_v6_0_25 \
"../../ipstatic/simulation/fifo_generator_vlog_beh.v" \

vcom -work fifo_generator_v13_2_14 -93  -incr \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.vhd" \

vlog -work fifo_generator_v13_2_14  -incr -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l xbip_pipe_v3_0_11 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l axi_utils_v2_0_11 -l cordic_v6_0_25 \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.v" \

vlog -work xil_defaultlib  -incr -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l xbip_pipe_v3_0_11 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l axi_utils_v2_0_11 -l cordic_v6_0_25 \
"../../../impedance_analyzer.gen/sources_1/ip/wave_delay_fifo/sim/wave_delay_fifo.v" \

vcom -work xbip_utils_v3_0_15 -93  -incr \
"../../ipstatic/hdl/xbip_utils_v3_0_vh_rfs.vhd" \

vcom -work c_reg_fd_v12_0_11 -93  -incr \
"../../ipstatic/hdl/c_reg_fd_v12_0_vh_rfs.vhd" \

vcom -work xbip_dsp48_wrapper_v3_0_7 -93  -incr \
"../../ipstatic/hdl/xbip_dsp48_wrapper_v3_0_vh_rfs.vhd" \

vcom -work xbip_pipe_v3_0_11 -93  -incr \
"../../ipstatic/hdl/xbip_pipe_v3_0_vh_rfs.vhd" \

vcom -work c_addsub_v12_0_21 -93  -incr \
"../../ipstatic/hdl/c_addsub_v12_0_vh_rfs.vhd" \

vcom -work mult_gen_v12_0_24 -93  -incr \
"../../ipstatic/hdl/mult_gen_v12_0_vh_rfs.vhd" \

vcom -work axi_utils_v2_0_11 -93  -incr \
"../../ipstatic/hdl/axi_utils_v2_0_vh_rfs.vhd" \

vcom -work cordic_v6_0_25 -93  -incr \
"../../ipstatic/hdl/cordic_v6_0_vh_rfs.vhd" \

vcom -work xil_defaultlib -93  -incr \
"../../../impedance_analyzer.gen/sources_1/ip/DDS_Generator/sim/DDS_Generator.vhd" \

vlog -work xil_defaultlib  -incr -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l xbip_pipe_v3_0_11 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l axi_utils_v2_0_11 -l cordic_v6_0_25 \
"../../../impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver.v" \
"../../../impedance_analyzer.gen/sources_1/ip/ADC_Input/ADC_Input_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/ADC_Input/ADC_Input.v" \

vlog -work xil_defaultlib \
"glbl.v"

