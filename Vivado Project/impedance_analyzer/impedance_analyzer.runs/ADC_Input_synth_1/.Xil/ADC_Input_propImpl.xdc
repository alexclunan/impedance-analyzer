set_property SRC_FILE_INFO {cfile:{c:/Users/Alex/Documents/GitHub/impedance-analyzer/Vivado Project/impedance_analyzer/impedance_analyzer.gen/sources_1/ip/adc_input/adc_input_ooc.xdc} rfile:../../../impedance_analyzer.gen/sources_1/ip/adc_input/adc_input_ooc.xdc id:1 order:EARLY scoped_inst:inst} [current_design]
current_instance inst
set_property src_info {type:SCOPED_XDC file:1 line:55 export:INPUT save:INPUT read:FILTER_OUT_OF_CONTEXT} [current_design]
set_input_jitter [get_clocks -of_objects [get_ports clk_in_p]] 0.1
