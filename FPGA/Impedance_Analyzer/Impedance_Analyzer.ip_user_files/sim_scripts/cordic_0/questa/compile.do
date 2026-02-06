vlib questa_lib/work
vlib questa_lib/msim

vlib questa_lib/msim/xbip_utils_v3_0_15
vlib questa_lib/msim/c_reg_fd_v12_0_11
vlib questa_lib/msim/xbip_dsp48_wrapper_v3_0_7
vlib questa_lib/msim/xbip_pipe_v3_0_11
vlib questa_lib/msim/c_addsub_v12_0_21
vlib questa_lib/msim/mult_gen_v12_0_24
vlib questa_lib/msim/axi_utils_v2_0_11
vlib questa_lib/msim/cordic_v6_0_25
vlib questa_lib/msim/xil_defaultlib

vmap xbip_utils_v3_0_15 questa_lib/msim/xbip_utils_v3_0_15
vmap c_reg_fd_v12_0_11 questa_lib/msim/c_reg_fd_v12_0_11
vmap xbip_dsp48_wrapper_v3_0_7 questa_lib/msim/xbip_dsp48_wrapper_v3_0_7
vmap xbip_pipe_v3_0_11 questa_lib/msim/xbip_pipe_v3_0_11
vmap c_addsub_v12_0_21 questa_lib/msim/c_addsub_v12_0_21
vmap mult_gen_v12_0_24 questa_lib/msim/mult_gen_v12_0_24
vmap axi_utils_v2_0_11 questa_lib/msim/axi_utils_v2_0_11
vmap cordic_v6_0_25 questa_lib/msim/cordic_v6_0_25
vmap xil_defaultlib questa_lib/msim/xil_defaultlib

vcom -work xbip_utils_v3_0_15  -93  \
"../../../ipstatic/hdl/xbip_utils_v3_0_vh_rfs.vhd" \

vcom -work c_reg_fd_v12_0_11  -93  \
"../../../ipstatic/hdl/c_reg_fd_v12_0_vh_rfs.vhd" \

vcom -work xbip_dsp48_wrapper_v3_0_7  -93  \
"../../../ipstatic/hdl/xbip_dsp48_wrapper_v3_0_vh_rfs.vhd" \

vcom -work xbip_pipe_v3_0_11  -93  \
"../../../ipstatic/hdl/xbip_pipe_v3_0_vh_rfs.vhd" \

vcom -work c_addsub_v12_0_21  -93  \
"../../../ipstatic/hdl/c_addsub_v12_0_vh_rfs.vhd" \

vcom -work mult_gen_v12_0_24  -93  \
"../../../ipstatic/hdl/mult_gen_v12_0_vh_rfs.vhd" \

vcom -work axi_utils_v2_0_11  -93  \
"../../../ipstatic/hdl/axi_utils_v2_0_vh_rfs.vhd" \

vcom -work cordic_v6_0_25  -93  \
"../../../ipstatic/hdl/cordic_v6_0_vh_rfs.vhd" \

vcom -work xil_defaultlib  -93  \
"../../../../Impedance_Analyzer.gen/sources_1/ip/cordic_0/sim/cordic_0.vhd" \


