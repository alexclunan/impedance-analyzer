// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
// Date        : Tue Feb 24 12:54:11 2026
// Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
//               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ dac_driver_sim_netlist.v
// Design      : dac_driver
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg484-2
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* DEV_W = "16" *) (* SYS_W = "16" *) 
(* NotValidForBitStream *)
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix
   (data_out_from_device,
    data_out_to_pins_p,
    data_out_to_pins_n,
    clk_to_pins_p,
    clk_to_pins_n,
    clk_in_p,
    clk_in_n,
    clk_out,
    clk_reset,
    io_reset);
  input [15:0]data_out_from_device;
  output [15:0]data_out_to_pins_p;
  output [15:0]data_out_to_pins_n;
  output clk_to_pins_p;
  output clk_to_pins_n;
  input clk_in_p;
  input clk_in_n;
  output clk_out;
  input clk_reset;
  input io_reset;

  (* DIFF_TERM = 0 *) (* IBUF_LOW_PWR *) (* IOSTANDARD = "DIFF_SSTL18_I" *) wire clk_in_n;
  (* DIFF_TERM = 0 *) (* IBUF_LOW_PWR *) (* IOSTANDARD = "DIFF_SSTL18_I" *) wire clk_in_p;
  wire clk_out;
  wire clk_reset;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire clk_to_pins_n;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire clk_to_pins_p;
  wire [15:0]data_out_from_device;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire [15:0]data_out_to_pins_n;
  (* IOSTANDARD = "DIFF_SSTL18_I" *) (* SLEW = "SLOW" *) wire [15:0]data_out_to_pins_p;
  wire io_reset;

  (* DEV_W = "16" *) 
  (* SYS_W = "16" *) 
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz inst
       (.clk_in_n(clk_in_n),
        .clk_in_p(clk_in_p),
        .clk_out(clk_out),
        .clk_reset(clk_reset),
        .clk_to_pins_n(clk_to_pins_n),
        .clk_to_pins_p(clk_to_pins_p),
        .data_out_from_device(data_out_from_device),
        .data_out_to_pins_n(data_out_to_pins_n),
        .data_out_to_pins_p(data_out_to_pins_p),
        .io_reset(io_reset));
endmodule

(* DEV_W = "16" *) (* SYS_W = "16" *) 
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz
   (data_out_from_device,
    data_out_to_pins_p,
    data_out_to_pins_n,
    clk_to_pins_p,
    clk_to_pins_n,
    clk_in_p,
    clk_in_n,
    clk_out,
    clk_reset,
    io_reset);
  input [15:0]data_out_from_device;
  output [15:0]data_out_to_pins_p;
  output [15:0]data_out_to_pins_n;
  output clk_to_pins_p;
  output clk_to_pins_n;
  input clk_in_p;
  input clk_in_n;
  output clk_out;
  input clk_reset;
  input io_reset;

  wire clk_fwd_out;
  wire clk_in_int;
  wire clk_in_n;
  wire clk_in_p;
  wire clk_out;
  wire clk_reset;
  wire clk_to_pins_n;
  wire clk_to_pins_p;
  wire [15:0]data_out_from_device;
  wire [15:0]data_out_to_pins_n;
  wire [15:0]data_out_to_pins_p;
  wire io_reset;
  wire \pins[0].data_out_from_device_q ;
  wire \pins[10].data_out_from_device_q ;
  wire \pins[11].data_out_from_device_q ;
  wire \pins[12].data_out_from_device_q ;
  wire \pins[13].data_out_from_device_q ;
  wire \pins[14].data_out_from_device_q ;
  wire \pins[15].data_out_from_device_q ;
  wire \pins[1].data_out_from_device_q ;
  wire \pins[2].data_out_from_device_q ;
  wire \pins[3].data_out_from_device_q ;
  wire \pins[4].data_out_from_device_q ;
  wire \pins[5].data_out_from_device_q ;
  wire \pins[6].data_out_from_device_q ;
  wire \pins[7].data_out_from_device_q ;
  wire \pins[8].data_out_from_device_q ;
  wire \pins[9].data_out_from_device_q ;
  wire NLW_oddr_inst_S_UNCONNECTED;

  (* BOX_TYPE = "PRIMITIVE" *) 
  BUFR #(
    .BUFR_DIVIDE("BYPASS"),
    .SIM_DEVICE("7SERIES")) 
    clkout_buf_inst
       (.CE(1'b1),
        .CLR(1'b0),
        .I(clk_in_int),
        .O(clk_out));
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
  (* OPT_MODIFIED = "MLO" *) 
  (* __SRVAL = "FALSE" *) 
  ODDR #(
    .DDR_CLK_EDGE("SAME_EDGE"),
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D1_INVERTED(1'b0),
    .IS_D2_INVERTED(1'b0),
    .SRTYPE("ASYNC")) 
    oddr_inst
       (.C(clk_out),
        .CE(1'b1),
        .D1(1'b1),
        .D2(1'b0),
        .Q(clk_fwd_out),
        .R(clk_reset),
        .S(NLW_oddr_inst_S_UNCONNECTED));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[0].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[0]),
        .Q(\pins[0].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[0].obufds_inst 
       (.I(\pins[0].data_out_from_device_q ),
        .O(data_out_to_pins_p[0]),
        .OB(data_out_to_pins_n[0]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[10].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[10]),
        .Q(\pins[10].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[10].obufds_inst 
       (.I(\pins[10].data_out_from_device_q ),
        .O(data_out_to_pins_p[10]),
        .OB(data_out_to_pins_n[10]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[11].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[11]),
        .Q(\pins[11].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[11].obufds_inst 
       (.I(\pins[11].data_out_from_device_q ),
        .O(data_out_to_pins_p[11]),
        .OB(data_out_to_pins_n[11]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[12].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[12]),
        .Q(\pins[12].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[12].obufds_inst 
       (.I(\pins[12].data_out_from_device_q ),
        .O(data_out_to_pins_p[12]),
        .OB(data_out_to_pins_n[12]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[13].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[13]),
        .Q(\pins[13].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[13].obufds_inst 
       (.I(\pins[13].data_out_from_device_q ),
        .O(data_out_to_pins_p[13]),
        .OB(data_out_to_pins_n[13]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[14].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[14]),
        .Q(\pins[14].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[14].obufds_inst 
       (.I(\pins[14].data_out_from_device_q ),
        .O(data_out_to_pins_p[14]),
        .OB(data_out_to_pins_n[14]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[15].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[15]),
        .Q(\pins[15].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[15].obufds_inst 
       (.I(\pins[15].data_out_from_device_q ),
        .O(data_out_to_pins_p[15]),
        .OB(data_out_to_pins_n[15]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[1].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[1]),
        .Q(\pins[1].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[1].obufds_inst 
       (.I(\pins[1].data_out_from_device_q ),
        .O(data_out_to_pins_p[1]),
        .OB(data_out_to_pins_n[1]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[2].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[2]),
        .Q(\pins[2].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[2].obufds_inst 
       (.I(\pins[2].data_out_from_device_q ),
        .O(data_out_to_pins_p[2]),
        .OB(data_out_to_pins_n[2]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[3].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[3]),
        .Q(\pins[3].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[3].obufds_inst 
       (.I(\pins[3].data_out_from_device_q ),
        .O(data_out_to_pins_p[3]),
        .OB(data_out_to_pins_n[3]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[4].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[4]),
        .Q(\pins[4].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[4].obufds_inst 
       (.I(\pins[4].data_out_from_device_q ),
        .O(data_out_to_pins_p[4]),
        .OB(data_out_to_pins_n[4]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[5].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[5]),
        .Q(\pins[5].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[5].obufds_inst 
       (.I(\pins[5].data_out_from_device_q ),
        .O(data_out_to_pins_p[5]),
        .OB(data_out_to_pins_n[5]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[6].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[6]),
        .Q(\pins[6].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[6].obufds_inst 
       (.I(\pins[6].data_out_from_device_q ),
        .O(data_out_to_pins_p[6]),
        .OB(data_out_to_pins_n[6]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[7].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[7]),
        .Q(\pins[7].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[7].obufds_inst 
       (.I(\pins[7].data_out_from_device_q ),
        .O(data_out_to_pins_p[7]),
        .OB(data_out_to_pins_n[7]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[8].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[8]),
        .Q(\pins[8].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[8].obufds_inst 
       (.I(\pins[8].data_out_from_device_q ),
        .O(data_out_to_pins_p[8]),
        .OB(data_out_to_pins_n[8]));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* IOB = "TRUE" *) 
  FDRE #(
    .INIT(1'b0),
    .IS_C_INVERTED(1'b0),
    .IS_D_INVERTED(1'b0),
    .IS_R_INVERTED(1'b0)) 
    \pins[9].fdre_out_inst 
       (.C(clk_out),
        .CE(1'b1),
        .D(data_out_from_device[9]),
        .Q(\pins[9].data_out_from_device_q ),
        .R(io_reset));
  (* BOX_TYPE = "PRIMITIVE" *) 
  (* CAPACITANCE = "DONT_CARE" *) 
  (* XILINX_LEGACY_PRIM = "OBUFDS" *) 
  OBUFDS \pins[9].obufds_inst 
       (.I(\pins[9].data_out_from_device_q ),
        .O(data_out_to_pins_p[9]),
        .OB(data_out_to_pins_n[9]));
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
