transcript off
onbreak {quit -force}
onerror {quit -force}
transcript on

vlib work
vlib activehdl/xpm
vlib activehdl/fifo_generator_v13_2_14
vlib activehdl/xil_defaultlib
vlib activehdl/xbip_utils_v3_0_15
vlib activehdl/axi_utils_v2_0_11
vlib activehdl/xbip_pipe_v3_0_11
vlib activehdl/fir_compiler_v7_2_26
vlib activehdl/c_reg_fd_v12_0_11
vlib activehdl/xbip_dsp48_wrapper_v3_0_7
vlib activehdl/c_addsub_v12_0_21
vlib activehdl/mult_gen_v12_0_24
vlib activehdl/cordic_v6_0_25
vlib activehdl/cic_compiler_v4_0_22
vlib activehdl/axi_bram_ctrl_v4_1_13
vlib activehdl/blk_mem_gen_v8_4_12

vmap xpm activehdl/xpm
vmap fifo_generator_v13_2_14 activehdl/fifo_generator_v13_2_14
vmap xil_defaultlib activehdl/xil_defaultlib
vmap xbip_utils_v3_0_15 activehdl/xbip_utils_v3_0_15
vmap axi_utils_v2_0_11 activehdl/axi_utils_v2_0_11
vmap xbip_pipe_v3_0_11 activehdl/xbip_pipe_v3_0_11
vmap fir_compiler_v7_2_26 activehdl/fir_compiler_v7_2_26
vmap c_reg_fd_v12_0_11 activehdl/c_reg_fd_v12_0_11
vmap xbip_dsp48_wrapper_v3_0_7 activehdl/xbip_dsp48_wrapper_v3_0_7
vmap c_addsub_v12_0_21 activehdl/c_addsub_v12_0_21
vmap mult_gen_v12_0_24 activehdl/mult_gen_v12_0_24
vmap cordic_v6_0_25 activehdl/cordic_v6_0_25
vmap cic_compiler_v4_0_22 activehdl/cic_compiler_v4_0_22
vmap axi_bram_ctrl_v4_1_13 activehdl/axi_bram_ctrl_v4_1_13
vmap blk_mem_gen_v8_4_12 activehdl/blk_mem_gen_v8_4_12

vlog -work xpm  -sv2k12 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_cdc/hdl/xpm_cdc.sv" \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_memory/hdl/xpm_memory.sv" \

vcom -work xpm -93  \
"C:/AMDDesignTools/2025.2/Vivado/data/ip/xpm/xpm_VCOMP.vhd" \

vlog -work fifo_generator_v13_2_14  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../ipstatic/simulation/fifo_generator_vlog_beh.v" \

vcom -work fifo_generator_v13_2_14 -93  \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.vhd" \

vlog -work fifo_generator_v13_2_14  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../ipstatic/hdl/fifo_generator_v13_2_rfs.v" \

vlog -work xil_defaultlib  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../../impedance_analyzer.gen/sources_1/ip/wave_delay_fifo/sim/wave_delay_fifo.v" \

vcom -work xbip_utils_v3_0_15 -93  \
"../../ipstatic/hdl/xbip_utils_v3_0_vh_rfs.vhd" \

vcom -work axi_utils_v2_0_11 -93  \
"../../ipstatic/hdl/axi_utils_v2_0_vh_rfs.vhd" \

vcom -work xbip_pipe_v3_0_11 -93  \
"../../ipstatic/hdl/xbip_pipe_v3_0_vh_rfs.vhd" \

vcom -work fir_compiler_v7_2_26 -93  \
"../../ipstatic/hdl/fir_compiler_v7_2_vh_rfs.vhd" \

vcom -work xil_defaultlib -93  \
"../../../impedance_analyzer.gen/sources_1/ip/fir_filter_q/sim/fir_filter_q.vhd" \
"../../../impedance_analyzer.gen/sources_1/ip/fir_filter_i/sim/fir_filter_i.vhd" \

vlog -work xil_defaultlib  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../../impedance_analyzer.gen/sources_1/ip/dac_driver/dac_driver_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/dac_driver/dac_driver.v" \

vcom -work c_reg_fd_v12_0_11 -93  \
"../../ipstatic/hdl/c_reg_fd_v12_0_vh_rfs.vhd" \

vcom -work xbip_dsp48_wrapper_v3_0_7 -93  \
"../../ipstatic/hdl/xbip_dsp48_wrapper_v3_0_vh_rfs.vhd" \

vcom -work c_addsub_v12_0_21 -93  \
"../../ipstatic/hdl/c_addsub_v12_0_vh_rfs.vhd" \

vcom -work mult_gen_v12_0_24 -93  \
"../../ipstatic/hdl/mult_gen_v12_0_vh_rfs.vhd" \

vcom -work cordic_v6_0_25 -93  \
"../../ipstatic/hdl/cordic_v6_0_vh_rfs.vhd" \

vcom -work xil_defaultlib -93  \
"../../../impedance_analyzer.gen/sources_1/ip/cordic_vectoring/sim/cordic_vectoring.vhd" \
"../../../impedance_analyzer.gen/sources_1/ip/cordic_sincos_dac/sim/cordic_sincos_dac.vhd" \
"../../../impedance_analyzer.gen/sources_1/ip/cordic_sincos_adc/sim/cordic_sincos_adc.vhd" \

vcom -work cic_compiler_v4_0_22 -93  \
"../../ipstatic/hdl/cic_compiler_v4_0_vh_rfs.vhd" \

vcom -work xil_defaultlib -93  \
"../../../impedance_analyzer.gen/sources_1/ip/cic_decimator_i/sim/cic_decimator_i.vhd" \
"../../../impedance_analyzer.gen/sources_1/ip/cic_compiler_0/sim/cic_compiler_0.vhd" \

vcom -work axi_bram_ctrl_v4_1_13 -93  \
"../../ipstatic/hdl/axi_bram_ctrl_v4_1_rfs.vhd" \

vcom -work xil_defaultlib -93  \
"../../../impedance_analyzer.gen/sources_1/ip/bram_ctrl/sim/bram_ctrl.vhd" \

vlog -work blk_mem_gen_v8_4_12  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../ipstatic/simulation/blk_mem_gen_v8_4.v" \

vlog -work xil_defaultlib  -v2k5 "+incdir+../../../../../../../../../../AMDDesignTools/2025.2/Vivado/data/rsb/busdef" -l xpm -l fifo_generator_v13_2_14 -l xil_defaultlib -l xbip_utils_v3_0_15 -l axi_utils_v2_0_11 -l xbip_pipe_v3_0_11 -l fir_compiler_v7_2_26 -l c_reg_fd_v12_0_11 -l xbip_dsp48_wrapper_v3_0_7 -l c_addsub_v12_0_21 -l mult_gen_v12_0_24 -l cordic_v6_0_25 -l cic_compiler_v4_0_22 -l axi_bram_ctrl_v4_1_13 -l blk_mem_gen_v8_4_12 \
"../../../impedance_analyzer.gen/sources_1/ip/blk_mem_gen_0/sim/blk_mem_gen_0.v" \
"../../../impedance_analyzer.gen/sources_1/ip/analog_delay_fifo/sim/analog_delay_fifo.v" \
"../../../impedance_analyzer.gen/sources_1/ip/adc_input/adc_input_selectio_wiz.v" \
"../../../impedance_analyzer.gen/sources_1/ip/adc_input/adc_input.v" \

vlog -work xil_defaultlib \
"glbl.v"

