// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
// Date        : Mon Feb 16 01:01:24 2026
// Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim {c:/Users/Alex/Documents/GitHub/impedance-analyzer/Vivado
//               Project/impedance_analyzer/impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver_sim_netlist.v}
// Design      : DAC_Driver
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg484-2
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* DEV_W = "32" *) (* SYS_W = "8" *) 
(* NotValidForBitStream *)
module DAC_Driver
   (data_out_from_device,
    data_out_to_pins_p,
    data_out_to_pins_n,
    clk_to_pins_p,
    clk_to_pins_n,
    clk_in_p,
    clk_in_n,
    clk_div_out,
    clk_reset,
    io_reset);
  input [31:0]data_out_from_device;
  output [7:0]data_out_to_pins_p;
  output [7:0]data_out_to_pins_n;
  output clk_to_pins_p;
  output clk_to_pins_n;
  input clk_in_p;
  input clk_in_n;
  output clk_div_out;
  input clk_reset;
  input io_reset;

  wire clk_div_out;
  (* DIFF_TERM = 0 *) (* IBUF_LOW_PWR *) (* IOSTANDARD = "DIFF_SSTL18_I" *) wire clk_in_n;
  (* DIFF_TERM = 0 *) (* IBUF_LOW_PWR *) (* IOSTANDARD = "DIFF_SSTL18_I" *) wire clk_in_p;
  wire clk_reset;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire clk_to_pins_n;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire clk_to_pins_p;
  wire [31:0]data_out_from_device;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire [7:0]data_out_to_pins_n;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire [7:0]data_out_to_pins_p;
  wire io_reset;

  (* DEV_W = "32" *) 
  (* SYS_W = "8" *) 
  (* num_serial_bits = "4" *) 
  DAC_Driver_selectio_wiz inst
       (.clk_div_out(clk_div_out),
        .clk_in_n(clk_in_n),
        .clk_in_p(clk_in_p),
        .clk_reset(clk_reset),
        .clk_to_pins_n(clk_to_pins_n),
        .clk_to_pins_p(clk_to_pins_p),
        .data_out_from_device(data_out_from_device),
        .data_out_to_pins_n(data_out_to_pins_n),
        .data_out_to_pins_p(data_out_to_pins_p),
        .io_reset(io_reset));
endmodule

(* DEV_W = "32" *) (* SYS_W = "8" *) (* num_serial_bits = "4" *) 
module DAC_Driver_selectio_wiz
   (data_out_from_device,
    data_out_to_pins_p,
    data_out_to_pins_n,
    clk_to_pins_p,
    clk_to_pins_n,
    clk_in_p,
    clk_in_n,
    clk_div_out,
    clk_reset,
    io_reset);
  input [31:0]data_out_from_device;
  output [7:0]data_out_to_pins_p;
  output [7:0]data_out_to_pins_n;
  output clk_to_pins_p;
  output clk_to_pins_n;
  input clk_in_p;
  input clk_in_n;
  output clk_div_out;
  input clk_reset;
  input io_reset;

  wire clk_div_out;
  wire clk_fwd_out;
  wire clk_in_int;
  wire clk_in_int_buf;
  wire clk_in_n;
  wire clk_in_p;
  wire clk_reset;
  wire clk_to_pins_n;
  wire clk_to_pins_p;
  wire [31:0]data_out_from_device;
  wire [7:0]data_out_to_pins_int;
  wire [7:0]data_out_to_pins_n;
  wire [7:0]data_out_to_pins_p;
  wire io_reset;
  wire NLW_clk_fwd_OFB_UNCONNECTED;
  wire NLW_clk_fwd_SHIFTOUT1_UNCONNECTED;
  wire NLW_clk_fwd_SHIFTOUT2_UNCONNECTED;
  wire NLW_clk_fwd_TBYTEOUT_UNCONNECTED;
  wire NLW_clk_fwd_TFB_UNCONNECTED;
  wire NLW_clk_fwd_TQ_UNCONNECTED;
  wire \NLW_pins[0].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[0].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[0].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[0].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[0].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[0].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[1].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[2].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[3].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[4].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[5].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[6].oserdese2_master_TQ_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_OFB_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_SHIFTOUT1_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_SHIFTOUT2_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_TBYTEOUT_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_TFB_UNCONNECTED ;
  wire \NLW_pins[7].oserdese2_master_TQ_UNCONNECTED ;

  (* BOX_TYPE = "PRIMITIVE" *) 
  BUFIO bufio_inst
       (.I(clk_in_int),
        .O(clk_in_int_buf));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("SDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(1)) 
    clk_fwd
       (.CLK(clk_div_out),
        .CLKDIV(clk_div_out),
        .D1(1'b1),
        .D2(1'b0),
        .D3(1'b1),
        .D4(1'b0),
        .D5(1'b1),
        .D6(1'b0),
        .D7(1'b1),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(NLW_clk_fwd_OFB_UNCONNECTED),
        .OQ(clk_fwd_out),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(NLW_clk_fwd_SHIFTOUT1_UNCONNECTED),
        .SHIFTOUT2(NLW_clk_fwd_SHIFTOUT2_UNCONNECTED),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(NLW_clk_fwd_TBYTEOUT_UNCONNECTED),
        .TCE(1'b0),
        .TFB(NLW_clk_fwd_TFB_UNCONNECTED),
        .TQ(NLW_clk_fwd_TQ_UNCONNECTED));
  (* BOX_TYPE = "PRIMITIVE" *) 
  BUFR #(
    .BUFR_DIVIDE("2"),
    .SIM_DEVICE("7SERIES")) 
    clkout_buf_inst
       (.CE(1'b1),
        .CLR(clk_reset),
        .I(clk_in_int),
        .O(clk_div_out));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* IBUF_DELAY_VALUE = "0" *) 
  (* IFD_DELAY_VALUE = "AUTO" *) 
  IBUFDS ibufds_clk_inst
       (.I(clk_in_p),
        .IB(clk_in_n),
        .O(clk_in_int));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS obufds_inst
       (.I(clk_fwd_out),
        .O(clk_to_pins_p),
        .OB(clk_to_pins_n));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[0].obufds_inst 
       (.I(data_out_to_pins_int[0]),
        .O(data_out_to_pins_p[0]),
        .OB(data_out_to_pins_n[0]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[0].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[0]),
        .D2(data_out_from_device[8]),
        .D3(data_out_from_device[16]),
        .D4(data_out_from_device[24]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[0].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[0]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[0].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[0].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[0].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[0].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[0].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[1].obufds_inst 
       (.I(data_out_to_pins_int[1]),
        .O(data_out_to_pins_p[1]),
        .OB(data_out_to_pins_n[1]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[1].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[1]),
        .D2(data_out_from_device[9]),
        .D3(data_out_from_device[17]),
        .D4(data_out_from_device[25]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[1].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[1]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[1].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[1].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[1].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[1].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[1].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[2].obufds_inst 
       (.I(data_out_to_pins_int[2]),
        .O(data_out_to_pins_p[2]),
        .OB(data_out_to_pins_n[2]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[2].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[2]),
        .D2(data_out_from_device[10]),
        .D3(data_out_from_device[18]),
        .D4(data_out_from_device[26]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[2].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[2]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[2].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[2].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[2].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[2].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[2].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[3].obufds_inst 
       (.I(data_out_to_pins_int[3]),
        .O(data_out_to_pins_p[3]),
        .OB(data_out_to_pins_n[3]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[3].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[3]),
        .D2(data_out_from_device[11]),
        .D3(data_out_from_device[19]),
        .D4(data_out_from_device[27]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[3].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[3]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[3].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[3].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[3].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[3].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[3].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[4].obufds_inst 
       (.I(data_out_to_pins_int[4]),
        .O(data_out_to_pins_p[4]),
        .OB(data_out_to_pins_n[4]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[4].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[4]),
        .D2(data_out_from_device[12]),
        .D3(data_out_from_device[20]),
        .D4(data_out_from_device[28]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[4].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[4]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[4].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[4].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[4].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[4].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[4].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[5].obufds_inst 
       (.I(data_out_to_pins_int[5]),
        .O(data_out_to_pins_p[5]),
        .OB(data_out_to_pins_n[5]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[5].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[5]),
        .D2(data_out_from_device[13]),
        .D3(data_out_from_device[21]),
        .D4(data_out_from_device[29]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[5].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[5]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[5].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[5].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[5].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[5].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[5].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[6].obufds_inst 
       (.I(data_out_to_pins_int[6]),
        .O(data_out_to_pins_p[6]),
        .OB(data_out_to_pins_n[6]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[6].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[6]),
        .D2(data_out_from_device[14]),
        .D3(data_out_from_device[22]),
        .D4(data_out_from_device[30]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[6].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[6]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[6].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[6].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[6].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[6].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[6].oserdese2_master_TQ_UNCONNECTED ));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[7].obufds_inst 
       (.I(data_out_to_pins_int[7]),
        .O(data_out_to_pins_p[7]),
        .OB(data_out_to_pins_n[7]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  OSERDESE2 #(
    .DATA_RATE_OQ("DDR"),
    .DATA_RATE_TQ("DDR"),
    .DATA_WIDTH(4),
    .INIT_OQ(1'b0),
    .INIT_TQ(1'b0),
    .IS_CLKDIV_INVERTED(1'b0),
    .IS_CLK_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .IS_D3_INVERTED(1'b0),
    .IS_D4_INVERTED(1'b0),
    .IS_D5_INVERTED(1'b0),
    .IS_D6_INVERTED(1'b0),
    .IS_D7_INVERTED(1'b0),
    .IS_D8_INVERTED(1'b0),
    .IS_T1_INVERTED(1'b0),
    .IS_T2_INVERTED(1'b0),
    .IS_T3_INVERTED(1'b0),
    .IS_T4_INVERTED(1'b0),
    .SERDES_MODE("MASTER"),
    .SRVAL_OQ(1'b0),
    .SRVAL_TQ(1'b0),
    .TBYTE_CTL("FALSE"),
    .TBYTE_SRC("FALSE"),
    .TRISTATE_WIDTH(4)) 
    \pins[7].oserdese2_master 
       (.CLK(clk_in_int_buf),
        .CLKDIV(clk_div_out),
        .D1(data_out_from_device[7]),
        .D2(data_out_from_device[15]),
        .D3(data_out_from_device[23]),
        .D4(data_out_from_device[31]),
        .D5(1'b0),
        .D6(1'b0),
        .D7(1'b0),
        .D8(1'b0),
        .OCE(1'b1),
        .OFB(\NLW_pins[7].oserdese2_master_OFB_UNCONNECTED ),
        .OQ(data_out_to_pins_int[7]),
        .RST(io_reset),
        .SHIFTIN1(1'b0),
        .SHIFTIN2(1'b0),
        .SHIFTOUT1(\NLW_pins[7].oserdese2_master_SHIFTOUT1_UNCONNECTED ),
        .SHIFTOUT2(\NLW_pins[7].oserdese2_master_SHIFTOUT2_UNCONNECTED ),
        .T1(1'b0),
        .T2(1'b0),
        .T3(1'b0),
        .T4(1'b0),
        .TBYTEIN(1'b0),
        .TBYTEOUT(\NLW_pins[7].oserdese2_master_TBYTEOUT_UNCONNECTED ),
        .TCE(1'b0),
        .TFB(\NLW_pins[7].oserdese2_master_TFB_UNCONNECTED ),
        .TQ(\NLW_pins[7].oserdese2_master_TQ_UNCONNECTED ));
endmodule
`ifndef GLBL
`define GLBL
`timescale  1 ps / 1 ps

module glbl ();

    parameter ROC_WIDTH = 100000;
    parameter TOC_WIDTH = 0;
    parameter GRES_WIDTH = 10000;
    parameter GRES_START = 10000;

//--------   STARTUP Globals --------------
    wire GSR;
    wire GTS;
    wire GWE;
    wire PRLD;
    wire GRESTORE;
    tri1 p_up_tmp;
    tri (weak1, strong0) PLL_LOCKG = p_up_tmp;

    wire PROGB_GLBL;
    wire CCLKO_GLBL;
    wire FCSBO_GLBL;
    wire [3:0] DO_GLBL;
    wire [3:0] DI_GLBL;
   
    reg GSR_int;
    reg GTS_int;
    reg PRLD_int;
    reg GRESTORE_int;

//--------   JTAG Globals --------------
    wire JTAG_TDO_GLBL;
    wire JTAG_TCK_GLBL;
    wire JTAG_TDI_GLBL;
    wire JTAG_TMS_GLBL;
    wire JTAG_TRST_GLBL;

    reg JTAG_CAPTURE_GLBL;
    reg JTAG_RESET_GLBL;
    reg JTAG_SHIFT_GLBL;
    reg JTAG_UPDATE_GLBL;
    reg JTAG_RUNTEST_GLBL;

    reg JTAG_SEL1_GLBL = 0;
    reg JTAG_SEL2_GLBL = 0 ;
    reg JTAG_SEL3_GLBL = 0;
    reg JTAG_SEL4_GLBL = 0;

    reg JTAG_USER_TDO1_GLBL = 1'bz;
    reg JTAG_USER_TDO2_GLBL = 1'bz;
    reg JTAG_USER_TDO3_GLBL = 1'bz;
    reg JTAG_USER_TDO4_GLBL = 1'bz;

    assign (strong1, weak0) GSR = GSR_int;
    assign (strong1, weak0) GTS = GTS_int;
    assign (weak1, weak0) PRLD = PRLD_int;
    assign (strong1, weak0) GRESTORE = GRESTORE_int;

    initial begin
	GSR_int = 1'b1;
	PRLD_int = 1'b1;
	#(ROC_WIDTH)
	GSR_int = 1'b0;
	PRLD_int = 1'b0;
    end

    initial begin
	GTS_int = 1'b1;
	#(TOC_WIDTH)
	GTS_int = 1'b0;
    end

    initial begin 
	GRESTORE_int = 1'b0;
	#(GRES_START);
	GRESTORE_int = 1'b1;
	#(GRES_WIDTH);
	GRESTORE_int = 1'b0;
    end

endmodule
`endif
