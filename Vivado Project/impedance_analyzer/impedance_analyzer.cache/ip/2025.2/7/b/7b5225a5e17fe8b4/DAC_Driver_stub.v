// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
// Date        : Mon Feb 16 01:01:23 2026
// Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode synth_stub -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
//               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ DAC_Driver_stub.v
// Design      : DAC_Driver
// Purpose     : Stub declaration of top-level module interface
// Device      : xc7z020clg484-2
// --------------------------------------------------------------------------------

// This empty module with port declaration file causes synthesis tools to infer a black box for IP.
// The synthesis directives are for Synopsys Synplify support to prevent IO buffer insertion.
// Please paste the declaration into a Verilog source file or add the file as an additional source.
(* CORE_GENERATION_INFO = "DAC_Driver,selectio_wiz_v5_1_20,{component_name=DAC_Driver,bus_dir=OUTPUTS,bus_sig_type=DIFF,bus_io_std=DIFF_SSTL18_I,use_serialization=true,use_phase_detector=false,serialization_factor=4,enable_bitslip=false,enable_train=false,system_data_width=8,bus_in_delay=NONE,bus_out_delay=NONE,clk_sig_type=SINGLE,clk_io_std=LVCMOS18,clk_buf=BUFIO2,active_edge=RISING,clk_delay=NONE,selio_bus_in_delay=NONE,selio_bus_out_delay=NONE,selio_clk_buf=BUFIO,selio_active_edge=DDR,selio_ddr_alignment=SAME_EDGE_PIPELINED,selio_oddr_alignment=SAME_EDGE,ddr_alignment=C0,selio_interface_type=NETWORKING,interface_type=NETWORKING,selio_bus_in_tap=0,selio_bus_out_tap=0,selio_clk_io_std=DIFF_SSTL18_I,selio_clk_sig_type=DIFF}" *) (* DEV_W = "32" *) (* SYS_W = "8" *) 
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix(data_out_from_device, data_out_to_pins_p, 
  data_out_to_pins_n, clk_to_pins_p, clk_to_pins_n, clk_in_p, clk_in_n, clk_div_out, clk_reset, 
  io_reset)
/* synthesis syn_black_box black_box_pad_pin="data_out_from_device[31:0],data_out_to_pins_p[7:0],data_out_to_pins_n[7:0],clk_to_pins_p,clk_to_pins_n,clk_in_p,clk_in_n,clk_reset,io_reset" */
/* synthesis syn_force_seq_prim="clk_div_out" */;
  input [31:0]data_out_from_device;
  output [7:0]data_out_to_pins_p;
  output [7:0]data_out_to_pins_n;
  output clk_to_pins_p;
  output clk_to_pins_n;
  input clk_in_p;
  input clk_in_n;
  output clk_div_out /* synthesis syn_isclock = 1 */;
  input clk_reset;
  input io_reset;
endmodule
