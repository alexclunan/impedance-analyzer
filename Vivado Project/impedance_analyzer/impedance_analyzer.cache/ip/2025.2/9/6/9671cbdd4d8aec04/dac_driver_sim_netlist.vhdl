-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025
-- Date        : Tue Feb 24 12:54:11 2026
-- Host        : DESKTOP-F1EP304 running 64-bit major release  (build 9200)
-- Command     : write_vhdl -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
--               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ dac_driver_sim_netlist.vhdl
-- Design      : dac_driver
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xc7z020clg484-2
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz is
  port (
    data_out_from_device : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_out_to_pins_p : out STD_LOGIC_VECTOR ( 15 downto 0 );
    data_out_to_pins_n : out STD_LOGIC_VECTOR ( 15 downto 0 );
    clk_to_pins_p : out STD_LOGIC;
    clk_to_pins_n : out STD_LOGIC;
    clk_in_p : in STD_LOGIC;
    clk_in_n : in STD_LOGIC;
    clk_out : out STD_LOGIC;
    clk_reset : in STD_LOGIC;
    io_reset : in STD_LOGIC
  );
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz : entity is 16;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz : entity is 16;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz is
  signal clk_fwd_out : STD_LOGIC;
  signal clk_in_int : STD_LOGIC;
  signal \^clk_out\ : STD_LOGIC;
  signal \pins[0].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[10].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[11].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[12].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[13].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[14].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[15].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[1].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[2].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[3].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[4].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[5].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[6].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[7].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[8].data_out_from_device_q\ : STD_LOGIC;
  signal \pins[9].data_out_from_device_q\ : STD_LOGIC;
  signal NLW_oddr_inst_S_UNCONNECTED : STD_LOGIC;
  attribute BOX_TYPE : string;
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
  attribute BOX_TYPE of oddr_inst : label is "PRIMITIVE";
  attribute OPT_MODIFIED : string;
  attribute OPT_MODIFIED of oddr_inst : label is "MLO";
  attribute \__SRVAL\ : string;
  attribute \__SRVAL\ of oddr_inst : label is "FALSE";
  attribute BOX_TYPE of \pins[0].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB : string;
  attribute IOB of \pins[0].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[0].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[0].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[0].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[10].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[10].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[10].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[10].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[10].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[11].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[11].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[11].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[11].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[11].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[12].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[12].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[12].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[12].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[12].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[13].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[13].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[13].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[13].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[13].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[14].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[14].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[14].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[14].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[14].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[15].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[15].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[15].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[15].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[15].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[1].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[1].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[1].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[1].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[1].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[2].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[2].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[2].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[2].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[2].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[3].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[3].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[3].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[3].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[3].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[4].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[4].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[4].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[4].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[4].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[5].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[5].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[5].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[5].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[5].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[6].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[6].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[6].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[6].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[6].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[7].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[7].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[7].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[7].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[7].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[8].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[8].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[8].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[8].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[8].obufds_inst\ : label is "OBUFDS";
  attribute BOX_TYPE of \pins[9].fdre_out_inst\ : label is "PRIMITIVE";
  attribute IOB of \pins[9].fdre_out_inst\ : label is "TRUE";
  attribute BOX_TYPE of \pins[9].obufds_inst\ : label is "PRIMITIVE";
  attribute CAPACITANCE of \pins[9].obufds_inst\ : label is "DONT_CARE";
  attribute XILINX_LEGACY_PRIM of \pins[9].obufds_inst\ : label is "OBUFDS";
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
obufds_inst: unisim.vcomponents.OBUFDS
     port map (
      I => clk_fwd_out,
      O => clk_to_pins_p,
      OB => clk_to_pins_n
    );
oddr_inst: unisim.vcomponents.ODDR
    generic map(
      DDR_CLK_EDGE => "SAME_EDGE",
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D1_INVERTED => '0',
      IS_D2_INVERTED => '0',
      SRTYPE => "ASYNC"
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D1 => '1',
      D2 => '0',
      Q => clk_fwd_out,
      R => clk_reset,
      S => NLW_oddr_inst_S_UNCONNECTED
    );
\pins[0].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(0),
      Q => \pins[0].data_out_from_device_q\,
      R => io_reset
    );
\pins[0].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[0].data_out_from_device_q\,
      O => data_out_to_pins_p(0),
      OB => data_out_to_pins_n(0)
    );
\pins[10].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(10),
      Q => \pins[10].data_out_from_device_q\,
      R => io_reset
    );
\pins[10].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[10].data_out_from_device_q\,
      O => data_out_to_pins_p(10),
      OB => data_out_to_pins_n(10)
    );
\pins[11].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(11),
      Q => \pins[11].data_out_from_device_q\,
      R => io_reset
    );
\pins[11].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[11].data_out_from_device_q\,
      O => data_out_to_pins_p(11),
      OB => data_out_to_pins_n(11)
    );
\pins[12].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(12),
      Q => \pins[12].data_out_from_device_q\,
      R => io_reset
    );
\pins[12].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[12].data_out_from_device_q\,
      O => data_out_to_pins_p(12),
      OB => data_out_to_pins_n(12)
    );
\pins[13].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(13),
      Q => \pins[13].data_out_from_device_q\,
      R => io_reset
    );
\pins[13].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[13].data_out_from_device_q\,
      O => data_out_to_pins_p(13),
      OB => data_out_to_pins_n(13)
    );
\pins[14].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(14),
      Q => \pins[14].data_out_from_device_q\,
      R => io_reset
    );
\pins[14].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[14].data_out_from_device_q\,
      O => data_out_to_pins_p(14),
      OB => data_out_to_pins_n(14)
    );
\pins[15].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(15),
      Q => \pins[15].data_out_from_device_q\,
      R => io_reset
    );
\pins[15].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[15].data_out_from_device_q\,
      O => data_out_to_pins_p(15),
      OB => data_out_to_pins_n(15)
    );
\pins[1].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(1),
      Q => \pins[1].data_out_from_device_q\,
      R => io_reset
    );
\pins[1].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[1].data_out_from_device_q\,
      O => data_out_to_pins_p(1),
      OB => data_out_to_pins_n(1)
    );
\pins[2].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(2),
      Q => \pins[2].data_out_from_device_q\,
      R => io_reset
    );
\pins[2].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[2].data_out_from_device_q\,
      O => data_out_to_pins_p(2),
      OB => data_out_to_pins_n(2)
    );
\pins[3].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(3),
      Q => \pins[3].data_out_from_device_q\,
      R => io_reset
    );
\pins[3].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[3].data_out_from_device_q\,
      O => data_out_to_pins_p(3),
      OB => data_out_to_pins_n(3)
    );
\pins[4].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(4),
      Q => \pins[4].data_out_from_device_q\,
      R => io_reset
    );
\pins[4].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[4].data_out_from_device_q\,
      O => data_out_to_pins_p(4),
      OB => data_out_to_pins_n(4)
    );
\pins[5].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(5),
      Q => \pins[5].data_out_from_device_q\,
      R => io_reset
    );
\pins[5].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[5].data_out_from_device_q\,
      O => data_out_to_pins_p(5),
      OB => data_out_to_pins_n(5)
    );
\pins[6].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(6),
      Q => \pins[6].data_out_from_device_q\,
      R => io_reset
    );
\pins[6].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[6].data_out_from_device_q\,
      O => data_out_to_pins_p(6),
      OB => data_out_to_pins_n(6)
    );
\pins[7].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(7),
      Q => \pins[7].data_out_from_device_q\,
      R => io_reset
    );
\pins[7].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[7].data_out_from_device_q\,
      O => data_out_to_pins_p(7),
      OB => data_out_to_pins_n(7)
    );
\pins[8].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(8),
      Q => \pins[8].data_out_from_device_q\,
      R => io_reset
    );
\pins[8].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[8].data_out_from_device_q\,
      O => data_out_to_pins_p(8),
      OB => data_out_to_pins_n(8)
    );
\pins[9].fdre_out_inst\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0',
      IS_C_INVERTED => '0',
      IS_D_INVERTED => '0',
      IS_R_INVERTED => '0'
    )
        port map (
      C => \^clk_out\,
      CE => '1',
      D => data_out_from_device(9),
      Q => \pins[9].data_out_from_device_q\,
      R => io_reset
    );
\pins[9].obufds_inst\: unisim.vcomponents.OBUFDS
     port map (
      I => \pins[9].data_out_from_device_q\,
      O => data_out_to_pins_p(9),
      OB => data_out_to_pins_n(9)
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  port (
    data_out_from_device : in STD_LOGIC_VECTOR ( 15 downto 0 );
    data_out_to_pins_p : out STD_LOGIC_VECTOR ( 15 downto 0 );
    data_out_to_pins_n : out STD_LOGIC_VECTOR ( 15 downto 0 );
    clk_to_pins_p : out STD_LOGIC;
    clk_to_pins_n : out STD_LOGIC;
    clk_in_p : in STD_LOGIC;
    clk_in_n : in STD_LOGIC;
    clk_out : out STD_LOGIC;
    clk_reset : in STD_LOGIC;
    io_reset : in STD_LOGIC
  );
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is true;
  attribute DEV_W : integer;
  attribute DEV_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 16;
  attribute SYS_W : integer;
  attribute SYS_W of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is 16;
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  attribute DEV_W of inst : label is 16;
  attribute SYS_W of inst : label is 16;
begin
inst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_dac_driver_selectio_wiz
     port map (
      clk_in_n => clk_in_n,
      clk_in_p => clk_in_p,
      clk_out => clk_out,
      clk_reset => clk_reset,
      clk_to_pins_n => clk_to_pins_n,
      clk_to_pins_p => clk_to_pins_p,
      data_out_from_device(15 downto 0) => data_out_from_device(15 downto 0),
      data_out_to_pins_n(15 downto 0) => data_out_to_pins_n(15 downto 0),
      data_out_to_pins_p(15 downto 0) => data_out_to_pins_p(15 downto 0),
      io_reset => io_reset
    );
end STRUCTURE;
