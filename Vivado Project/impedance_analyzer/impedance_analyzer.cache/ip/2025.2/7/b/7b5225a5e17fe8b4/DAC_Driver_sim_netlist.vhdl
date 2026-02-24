-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
-- Date        : Mon Feb 16 01:01:23 2026
-- Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
-- Command     : write_vhdl -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
--               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ DAC_Driver_sim_netlist.vhdl
-- Design      : DAC_Driver
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xc7z020clg484-2
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz is
  port (
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
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz : entity is 32;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz : entity is 8;
  attribute num_serial_bits : integer;
  attribute num_serial_bits of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz : entity is 4;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz is
  signal \^clk_div_out\ : STD_LOGIC;
  signal clk_fwd_out : STD_LOGIC;
  signal clk_in_int : STD_LOGIC;
  signal clk_in_int_buf : STD_LOGIC;
  signal data_out_to_pins_int : STD_LOGIC_VECTOR ( 7 downto 0 );
  signal NLW_clk_fwd_OFB_UNCONNECTED : STD_LOGIC;
  signal NLW_clk_fwd_SHIFTOUT1_UNCONNECTED : STD_LOGIC;
  signal NLW_clk_fwd_SHIFTOUT2_UNCONNECTED : STD_LOGIC;
  signal NLW_clk_fwd_TBYTEOUT_UNCONNECTED : STD_LOGIC;
  signal NLW_clk_fwd_TFB_UNCONNECTED : STD_LOGIC;
  signal NLW_clk_fwd_TQ_UNCONNECTED : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[0].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[1].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[2].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[3].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[4].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[5].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[6].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_OFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_SHIFTOUT1_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_SHIFTOUT2_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_TBYTEOUT_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_TFB_UNCONNECTED\ : STD_LOGIC;
  signal \NLW_pins[7].oserdese2_master_TQ_UNCONNECTED\ : STD_LOGIC;
  attribute BOX_TYPE : string;
  attribute BOX_TYPE of bufio_inst : label is "PRIMITIVE";
  attribute BOX_TYPE of clk_fwd : label is "PRIMITIVE";
  attribute BOX_TYPE of clkout_buf_inst : label is "PRIMITIVE";
  attribute BOX_TYPE of ibufds_clk_inst : label is "PRIMITIVE";
  attribute CAPACITANCE : string;
  attribute CAPACITANCE of ibufds_clk_inst : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE : string;
  attribute IBUF_DELAY_VALUE of ibufds_clk_inst : label is "0";
  attribute IFD_DELAY_VALUE : string;
  attribute IFD_DELAY_VALUE of ibufds_clk_inst : label is "AUTO";
  attribute BOX_TYPE of obufds_inst : label is "PRIMITIVE";
  attribute CAPACITANCE of obufds_inst : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM : string;
  attribute XILINX_LEGACY_PRIM of obufds_inst : label is "OBUFDS";
  attribute BOX_TYPE of \pins[0].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[0].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[0].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[0].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[1].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[1].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[1].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[1].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[2].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[2].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[2].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[2].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[3].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[3].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[3].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[3].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[4].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[4].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[4].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[4].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[5].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[5].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[5].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[5].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[6].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[6].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[6].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[6].oserdese2_master\ : label is "PRIMITIVE";
  attribute BOX_TYPE of \pins[7].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[7].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[7].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[7].oserdese2_master\ : label is "PRIMITIVE";
begin
  clk_div_out <= \^clk_div_out\;
bufio_inst: unisim.vcomponents.BUFIO
     port map (
      I => clk_in_int,
      O => clk_in_int_buf
    );
clk_fwd: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "SDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 1
    )
        port map (
      CLK => \^clk_div_out\,
      CLKDIV => \^clk_div_out\,
      D1 => '1',
      D2 => '0',
      D3 => '1',
      D4 => '0',
      D5 => '1',
      D6 => '0',
      D7 => '1',
      D8 => '0',
      OCE => '1',
      OFB => NLW_clk_fwd_OFB_UNCONNECTED,
      OQ => clk_fwd_out,
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => NLW_clk_fwd_SHIFTOUT1_UNCONNECTED,
      SHIFTOUT2 => NLW_clk_fwd_SHIFTOUT2_UNCONNECTED,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => NLW_clk_fwd_TBYTEOUT_UNCONNECTED,
      TCE => '0',
      TFB => NLW_clk_fwd_TFB_UNCONNECTED,
      TQ => NLW_clk_fwd_TQ_UNCONNECTED
    );
clkout_buf_inst: unisim.vcomponents.BUFR
    generic map(
      BUFR_DIVIDE => "2",
      SIM_DEVICE => "7SERIES"
    )
        port map (
      CE => '1',
      CLR => clk_reset,
      I => clk_in_int,
      O => \^clk_div_out\
    );
ibufds_clk_inst: unisim.vcomponents.IBUFDS
     port map (
      I => clk_in_p,
      IB => clk_in_n,
      O => clk_in_int
    );
obufds_inst: unisim.vcomponents.OBUFDS
     port map (
      I => clk_fwd_out,
      O => clk_to_pins_p,
      OB => clk_to_pins_n
    );
\pins[0].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(0),
      O => data_out_to_pins_p(0),
      OB => data_out_to_pins_n(0)
    );
\pins[0].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(0),
      D2 => data_out_from_device(8),
      D3 => data_out_from_device(16),
      D4 => data_out_from_device(24),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[0].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(0),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[0].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[0].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[0].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[0].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[0].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[1].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(1),
      O => data_out_to_pins_p(1),
      OB => data_out_to_pins_n(1)
    );
\pins[1].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(1),
      D2 => data_out_from_device(9),
      D3 => data_out_from_device(17),
      D4 => data_out_from_device(25),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[1].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(1),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[1].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[1].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[1].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[1].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[1].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[2].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(2),
      O => data_out_to_pins_p(2),
      OB => data_out_to_pins_n(2)
    );
\pins[2].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(2),
      D2 => data_out_from_device(10),
      D3 => data_out_from_device(18),
      D4 => data_out_from_device(26),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[2].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(2),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[2].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[2].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[2].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[2].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[2].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[3].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(3),
      O => data_out_to_pins_p(3),
      OB => data_out_to_pins_n(3)
    );
\pins[3].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(3),
      D2 => data_out_from_device(11),
      D3 => data_out_from_device(19),
      D4 => data_out_from_device(27),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[3].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(3),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[3].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[3].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[3].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[3].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[3].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[4].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(4),
      O => data_out_to_pins_p(4),
      OB => data_out_to_pins_n(4)
    );
\pins[4].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(4),
      D2 => data_out_from_device(12),
      D3 => data_out_from_device(20),
      D4 => data_out_from_device(28),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[4].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(4),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[4].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[4].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[4].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[4].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[4].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[5].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(5),
      O => data_out_to_pins_p(5),
      OB => data_out_to_pins_n(5)
    );
\pins[5].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(5),
      D2 => data_out_from_device(13),
      D3 => data_out_from_device(21),
      D4 => data_out_from_device(29),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[5].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(5),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[5].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[5].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[5].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[5].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[5].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[6].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(6),
      O => data_out_to_pins_p(6),
      OB => data_out_to_pins_n(6)
    );
\pins[6].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(6),
      D2 => data_out_from_device(14),
      D3 => data_out_from_device(22),
      D4 => data_out_from_device(30),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[6].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(6),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[6].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[6].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[6].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[6].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[6].oserdese2_master_TQ_UNCONNECTED\
    );
\pins[7].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => data_out_to_pins_int(7),
      O => data_out_to_pins_p(7),
      OB => data_out_to_pins_n(7)
    );
\pins[7].oserdese2_master\: unisim.vcomponents.OSERDESE2
    generic map(
      DATA_RATE_OQ => "DDR",
      DATA_RATE_TQ => "DDR",
      DATA_WIDTH => 4,
      INIT_OQ => '0',
      INIT_TQ => '0',
      IS_CLKDIV_INVERTED => '0',
      IS_CLK_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      IS_D3_INVERTED => '0',
      IS_D4_INVERTED => '0',
      IS_D5_INVERTED => '0',
      IS_D6_INVERTED => '0',
      IS_D7_INVERTED => '0',
      IS_D8_INVERTED => '0',
      IS_T1_INVERTED => '0',
      IS_T2_INVERTED => '0',
      IS_T3_INVERTED => '0',
      IS_T4_INVERTED => '0',
      SERDES_MODE => "MASTER",
      SRVAL_OQ => '0',
      SRVAL_TQ => '0',
      TBYTE_CTL => "FALSE",
      TBYTE_SRC => "FALSE",
      TRISTATE_WIDTH => 4
    )
        port map (
      CLK => clk_in_int_buf,
      CLKDIV => \^clk_div_out\,
      D1 => data_out_from_device(7),
      D2 => data_out_from_device(15),
      D3 => data_out_from_device(23),
      D4 => data_out_from_device(31),
      D5 => '0',
      D6 => '0',
      D7 => '0',
      D8 => '0',
      OCE => '1',
      OFB => \NLW_pins[7].oserdese2_master_OFB_UNCONNECTED\,
      OQ => data_out_to_pins_int(7),
      RST => io_reset,
      SHIFTIN1 => '0',
      SHIFTIN2 => '0',
      SHIFTOUT1 => \NLW_pins[7].oserdese2_master_SHIFTOUT1_UNCONNECTED\,
      SHIFTOUT2 => \NLW_pins[7].oserdese2_master_SHIFTOUT2_UNCONNECTED\,
      T1 => '0',
      T2 => '0',
      T3 => '0',
      T4 => '0',
      TBYTEIN => '0',
      TBYTEOUT => \NLW_pins[7].oserdese2_master_TBYTEOUT_UNCONNECTED\,
      TCE => '0',
      TFB => \NLW_pins[7].oserdese2_master_TFB_UNCONNECTED\,
      TQ => \NLW_pins[7].oserdese2_master_TQ_UNCONNECTED\
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  port (
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
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is true;
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 32;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 8;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  attribute DEV_W of inst : label is 32;
  attribute SYS_W of inst : label is 8;
  attribute num_serial_bits : integer;
  attribute num_serial_bits of inst : label is 4;
begin
inst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_DAC_Driver_selectio_wiz
     port map (
      clk_div_out => clk_div_out,
      clk_in_n => clk_in_n,
      clk_in_p => clk_in_p,
      clk_reset => clk_reset,
      clk_to_pins_n => clk_to_pins_n,
      clk_to_pins_p => clk_to_pins_p,
      data_out_from_device(31 downto 0) => data_out_from_device(31 downto 0),
      data_out_to_pins_n(7 downto 0) => data_out_to_pins_n(7 downto 0),
      data_out_to_pins_p(7 downto 0) => data_out_to_pins_p(7 downto 0),
      io_reset => io_reset
    );
end STRUCTURE;
