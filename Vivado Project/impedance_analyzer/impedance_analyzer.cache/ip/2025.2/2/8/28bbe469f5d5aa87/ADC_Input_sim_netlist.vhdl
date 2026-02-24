-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
-- Date        : Mon Feb 16 14:06:23 2026
-- Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
-- Command     : write_vhdl -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
--               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ ADC_Input_sim_netlist.vhdl
-- Design      : ADC_Input
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xc7z020clg484-2
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz is
  port (
    data_in_from_pins_p : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_in_from_pins_n : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_in_to_device : out STD_LOGIC_VECTOR ( 31 downto 0 );
    clk_in_p : in STD_LOGIC;
    clk_in_n : in STD_LOGIC;
    clk_out : out STD_LOGIC;
    io_reset : in STD_LOGIC
  );
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz : entity is 32;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz : entity is 16;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz is
  signal clk_in_int : STD_LOGIC;
  signal \^clk_out\ : STD_LOGIC;
  signal data_in_from_pins_int : STD_LOGIC_VECTOR ( 15 downto 0 );
  attribute BOX_TYPE : string;
  attribute BOX_TYPE of clkout_buf_inst : label is "PRIMITIVE";
  attribute BOX_TYPE of ibufds_clk_inst : label is "PRIMITIVE";
  attribute CAPACITANCE : string;
  attribute CAPACITANCE of ibufds_clk_inst : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE : string;
  attribute IBUF_DELAY_VALUE of ibufds_clk_inst : label is "0";
  attribute IFD_DELAY_VALUE : string;
  attribute IFD_DELAY_VALUE of ibufds_clk_inst : label is "AUTO";
  attribute BOX_TYPE of \pins[0].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[0].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[0].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[0].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[0].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ : string;
  attribute \__SRVAL\ of \pins[0].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[10].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[10].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[10].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[10].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[10].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[10].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[11].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[11].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[11].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[11].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[11].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[11].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[12].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[12].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[12].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[12].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[12].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[12].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[13].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[13].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[13].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[13].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[13].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[13].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[14].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[14].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[14].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[14].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[14].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[14].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[15].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[15].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[15].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[15].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[15].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[15].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[1].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[1].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[1].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[1].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[1].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[1].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[2].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[2].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[2].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[2].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[2].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[2].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[3].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[3].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[3].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[3].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[3].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[3].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[4].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[4].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[4].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[4].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[4].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[4].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[5].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[5].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[5].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[5].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[5].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[5].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[6].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[6].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[6].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[6].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[6].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[6].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[7].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[7].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[7].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[7].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[7].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[7].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[8].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[8].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[8].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[8].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[8].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[8].iddr_inst\ : label is "FALSE";
  attribute BOX_TYPE of \pins[9].ibufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[9].ibufds_inst\ : label is "DONT_CARE";
  attribute IBUF_DELAY_VALUE of \pins[9].ibufds_inst\ : label is "0";
  attribute IFD_DELAY_VALUE of \pins[9].ibufds_inst\ : label is "AUTO";
  attribute BOX_TYPE of \pins[9].iddr_inst\ : label is "PRIMITIVE";
  attribute \__SRVAL\ of \pins[9].iddr_inst\ : label is "FALSE";
begin
  clk_out <= \^clk_out\;
clkout_buf_inst: unisim.vcomponents.BUFR
    generic map(
      BUFR_DIVIDE => "BYPASS",
      SIM_DEVICE => "7SERIES"
    )
        port map (
      CE => '1',
      CLR => '0',
      I => clk_in_int,
      O => \^clk_out\
    );
ibufds_clk_inst: unisim.vcomponents.IBUFDS
     port map (
      I => clk_in_p,
      IB => clk_in_n,
      O => clk_in_int
    );
\pins[0].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(0),
      IB => data_in_from_pins_n(0),
      O => data_in_from_pins_int(0)
    );
\pins[0].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(0),
      Q1 => data_in_to_device(0),
      Q2 => data_in_to_device(16),
      R => io_reset,
      S => '0'
    );
\pins[10].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(10),
      IB => data_in_from_pins_n(10),
      O => data_in_from_pins_int(10)
    );
\pins[10].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(10),
      Q1 => data_in_to_device(10),
      Q2 => data_in_to_device(26),
      R => io_reset,
      S => '0'
    );
\pins[11].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(11),
      IB => data_in_from_pins_n(11),
      O => data_in_from_pins_int(11)
    );
\pins[11].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(11),
      Q1 => data_in_to_device(11),
      Q2 => data_in_to_device(27),
      R => io_reset,
      S => '0'
    );
\pins[12].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(12),
      IB => data_in_from_pins_n(12),
      O => data_in_from_pins_int(12)
    );
\pins[12].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(12),
      Q1 => data_in_to_device(12),
      Q2 => data_in_to_device(28),
      R => io_reset,
      S => '0'
    );
\pins[13].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(13),
      IB => data_in_from_pins_n(13),
      O => data_in_from_pins_int(13)
    );
\pins[13].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(13),
      Q1 => data_in_to_device(13),
      Q2 => data_in_to_device(29),
      R => io_reset,
      S => '0'
    );
\pins[14].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(14),
      IB => data_in_from_pins_n(14),
      O => data_in_from_pins_int(14)
    );
\pins[14].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(14),
      Q1 => data_in_to_device(14),
      Q2 => data_in_to_device(30),
      R => io_reset,
      S => '0'
    );
\pins[15].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(15),
      IB => data_in_from_pins_n(15),
      O => data_in_from_pins_int(15)
    );
\pins[15].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(15),
      Q1 => data_in_to_device(15),
      Q2 => data_in_to_device(31),
      R => io_reset,
      S => '0'
    );
\pins[1].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(1),
      IB => data_in_from_pins_n(1),
      O => data_in_from_pins_int(1)
    );
\pins[1].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(1),
      Q1 => data_in_to_device(1),
      Q2 => data_in_to_device(17),
      R => io_reset,
      S => '0'
    );
\pins[2].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(2),
      IB => data_in_from_pins_n(2),
      O => data_in_from_pins_int(2)
    );
\pins[2].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(2),
      Q1 => data_in_to_device(2),
      Q2 => data_in_to_device(18),
      R => io_reset,
      S => '0'
    );
\pins[3].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(3),
      IB => data_in_from_pins_n(3),
      O => data_in_from_pins_int(3)
    );
\pins[3].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(3),
      Q1 => data_in_to_device(3),
      Q2 => data_in_to_device(19),
      R => io_reset,
      S => '0'
    );
\pins[4].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(4),
      IB => data_in_from_pins_n(4),
      O => data_in_from_pins_int(4)
    );
\pins[4].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(4),
      Q1 => data_in_to_device(4),
      Q2 => data_in_to_device(20),
      R => io_reset,
      S => '0'
    );
\pins[5].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(5),
      IB => data_in_from_pins_n(5),
      O => data_in_from_pins_int(5)
    );
\pins[5].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(5),
      Q1 => data_in_to_device(5),
      Q2 => data_in_to_device(21),
      R => io_reset,
      S => '0'
    );
\pins[6].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(6),
      IB => data_in_from_pins_n(6),
      O => data_in_from_pins_int(6)
    );
\pins[6].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(6),
      Q1 => data_in_to_device(6),
      Q2 => data_in_to_device(22),
      R => io_reset,
      S => '0'
    );
\pins[7].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(7),
      IB => data_in_from_pins_n(7),
      O => data_in_from_pins_int(7)
    );
\pins[7].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(7),
      Q1 => data_in_to_device(7),
      Q2 => data_in_to_device(23),
      R => io_reset,
      S => '0'
    );
\pins[8].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(8),
      IB => data_in_from_pins_n(8),
      O => data_in_from_pins_int(8)
    );
\pins[8].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(8),
      Q1 => data_in_to_device(8),
      Q2 => data_in_to_device(24),
      R => io_reset,
      S => '0'
    );
\pins[9].ibufds_inst\: unisim.vcomponents.IBUFDS
     port map (
      I => data_in_from_pins_p(9),
      IB => data_in_from_pins_n(9),
      O => data_in_from_pins_int(9)
    );
\pins[9].iddr_inst\: unisim.vcomponents.IDDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE_PIPELINED",
      INIT_Q1 => '0',
      INIT_Q2 => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_in_from_pins_int(9),
      Q1 => data_in_to_device(9),
      Q2 => data_in_to_device(25),
      R => io_reset,
      S => '0'
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  port (
    data_in_from_pins_p : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_in_from_pins_n : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_in_to_device : out STD_LOGIC_VECTOR ( 31 downto 0 );
    clk_in_p : in STD_LOGIC;
    clk_in_n : in STD_LOGIC;
    clk_out : out STD_LOGIC;
    io_reset : in STD_LOGIC
  );
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is true;
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 32;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 16;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  attribute DEV_W of inst : label is 32;
  attribute SYS_W of inst : label is 16;
begin
inst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ADC_Input_selectio_wiz
     port map (
      clk_in_n => clk_in_n,
      clk_in_p => clk_in_p,
      clk_out => clk_out,
      data_in_from_pins_n(15 downto 0) => data_in_from_pins_n(15 downto 0),
      data_in_from_pins_p(15 downto 0) => data_in_from_pins_p(15 downto 0),
      data_in_to_device(31 downto 0) => data_in_to_device(31 downto 0),
      io_reset => io_reset
    );
end STRUCTURE;
