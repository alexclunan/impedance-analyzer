-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
-- Date        : Mon Feb 16 01:01:24 2026
-- Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
-- Command     : write_vhdl -force -mode synth_stub {c:/Users/Alex/Documents/GitHub/impedance-analyzer/Vivado
--               Project/impedance_analyzer/impedance_analyzer.gen/sources_1/ip/DAC_Driver/DAC_Driver_stub.vhdl}
-- Design      : DAC_Driver
-- Purpose     : Stub declaration of top-level module interface
-- Device      : xc7z020clg484-2
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity DAC_Driver is
  Port ( 
    data_out_from_device : in STD_LOGIC_VECTOR ( 31 downto 0 );
    data_out_to_pins_p : out STD_LOGIC_VECTOR ( 7 downto 0 );
    data_out_to_pins_n : out STD_LOGIC_VECTOR ( 7 downto 0 );
    clk_to_pins_p : out STD_LOGIC;
    clk_to_pins_n : out STD_LOGIC;
    clk_in_p : in STD_LOGIC;
    clk_in_n : in STD_LOGIC;
    clk_div_out : out STD_LOGIC;
    clk_reset : in STD_LOGIC;
    io_reset : in STD_LOGIC
  );

  attribute CORE_GENERATION_INFO : string;
  attribute CORE_GENERATION_INFO of DAC_Driver : entity is "DAC_Driver,selectio_wiz_v5_1_20,{component_name=DAC_Driver,bus_dir=OUTPUTS,bus_sig_type=DIFF,bus_io_std=DIFF_SSTL18_I,use_serialization=true,use_phase_detector=false,serialization_factor=4,enable_bitslip=false,enable_train=false,system_data_width=8,bus_in_delay=NONE,bus_out_delay=NONE,clk_sig_type=SINGLE,clk_io_std=LVCMOS18,clk_buf=BUFIO2,active_edge=RISING,clk_delay=NONE,selio_bus_in_delay=NONE,selio_bus_out_delay=NONE,selio_clk_buf=BUFIO,selio_active_edge=DDR,selio_ddr_alignment=SAME_EDGE_PIPELINED,selio_oddr_alignment=SAME_EDGE,ddr_alignment=C0,selio_interface_type=NETWORKING,interface_type=NETWORKING,selio_bus_in_tap=0,selio_bus_out_tap=0,selio_clk_io_std=DIFF_SSTL18_I,selio_clk_sig_type=DIFF}";
  attribute DEV_W : integer;
  attribute DEV_W of DAC_Driver : entity is 32;
  attribute SYS_W : integer;
  attribute SYS_W of DAC_Driver : entity is 8;
end DAC_Driver;

architecture stub of DAC_Driver is
  attribute syn_black_box : boolean;
  attribute black_box_pad_pin : string;
  attribute syn_black_box of stub : architecture is true;
  attribute black_box_pad_pin of stub : architecture is "data_out_from_device[31:0],data_out_to_pins_p[7:0],data_out_to_pins_n[7:0],clk_to_pins_p,clk_to_pins_n,clk_in_p,clk_in_n,clk_div_out,clk_reset,io_reset";
begin
end;
