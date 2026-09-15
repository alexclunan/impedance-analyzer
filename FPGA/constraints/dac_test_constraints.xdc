


set_property PACKAGE_PIN AA9 [get_ports dac_diff_clk_clk_p]
set_property IOSTANDARD LVCMOS25 [get_ports adc_sdio]
set_property IOSTANDARD LVCMOS25 [get_ports dac_sdi]
set_property PACKAGE_PIN F18 [get_ports {adc_inputp[0]}]
set_property PACKAGE_PIN E15 [get_ports {adc_inputp[1]}]
set_property PACKAGE_PIN F16 [get_ports {adc_inputp[2]}]
set_property PACKAGE_PIN A21 [get_ports {adc_inputp[3]}]
set_property PACKAGE_PIN E21 [get_ports {adc_inputp[4]}]
set_property PACKAGE_PIN G15 [get_ports {adc_inputp[5]}]
set_property PACKAGE_PIN G19 [get_ports {adc_inputp[6]}]
set_property PACKAGE_PIN G20 [get_ports {adc_inputp[7]}]
set_property PACKAGE_PIN D18 [get_ports {adc_inputp[8]}]
set_property PACKAGE_PIN AA11 [get_ports {dac_data_p[0]}]
set_property PACKAGE_PIN T4 [get_ports {dac_data_p[1]}]
set_property PACKAGE_PIN AB10 [get_ports {dac_data_p[2]}]
set_property PACKAGE_PIN AB7 [get_ports {dac_data_p[3]}]
set_property PACKAGE_PIN AB2 [get_ports {dac_data_p[4]}]
set_property PACKAGE_PIN V5 [get_ports {dac_data_p[5]}]
set_property PACKAGE_PIN U6 [get_ports {dac_data_p[6]}]
set_property PACKAGE_PIN W6 [get_ports {dac_data_p[7]}]
set_property PACKAGE_PIN C15 [get_ports {PCB_control_signals[0]}]
set_property PACKAGE_PIN D17 [get_ports {PCB_control_signals[1]}]
set_property PACKAGE_PIN B17 [get_ports {PCB_control_signals[2]}]
set_property PACKAGE_PIN B16 [get_ports {PCB_control_signals[3]}]
set_property PACKAGE_PIN D16 [get_ports {PCB_control_signals[4]}]
set_property PACKAGE_PIN F22 [get_ports {PCB_control_signals[5]}]
set_property PACKAGE_PIN A16 [get_ports {PCB_control_signals[6]}]
set_property PACKAGE_PIN A17 [get_ports {PCB_control_signals[7]}]
set_property PACKAGE_PIN A18 [get_ports {PCB_control_signals[8]}]
set_property PACKAGE_PIN A19 [get_ports {PCB_control_signals[9]}]
set_property PACKAGE_PIN F21 [get_ports adc_sdio]

set_property IOSTANDARD LVDS_25 [get_ports CLKin_clk_p]
set_property IOSTANDARD LVDS_25 [get_ports CLKin_clk_n]
set_property PACKAGE_PIN Y6 [get_ports CLKin_clk_p]



# NOTE: DIFF_TERM (internal 100 ohm LVDS termination) for the AD9467 inputs is
# NOT set here. It cannot be set on a cell via XDC (Netlist 29-75), and a port-
# level property is overridden by the SelectIO wizard's explicit IBUFDS, which
# hardcodes DIFF_TERM="FALSE". Termination is provided by forking the wizard HDL
# with DIFF_TERM="TRUE" (see adc_lvds_capture.v) -- not by a constraint.

set_property PACKAGE_PIN B15 [get_ports dac_sdi]

set_property PACKAGE_PIN V7 [get_ports {framep[0]}]

# Plan 07 trigger-engine actuation outputs (2.5 V CMOS).
# The BD's Make-External named the [1:0] bus port "trigger_out_0".
#   trigger_out_0[0] = main / output 0      -> AA7
#   trigger_out_0[1] = secondary / output 1 -> AA6
set_property PACKAGE_PIN AA7 [get_ports {trigger_out_0[0]}]
set_property PACKAGE_PIN AA6 [get_ports {trigger_out_0[1]}]
set_property IOSTANDARD LVCMOS25 [get_ports {trigger_out_0[*]}]


create_clock -period 5.000 -name adc_clk_p -waveform {0.000 2.500} [get_ports adc_clk_p]

set_property PACKAGE_PIN D20 [get_ports adc_clk_p]




set_max_delay -datapath_only -from [get_cells -hier -filter {NAME =~ *AXI_register_file*slv_reg*_reg[*]}] 10.000
