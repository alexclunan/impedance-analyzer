transcript off
onbreak {quit -force}
onerror {quit -force}
transcript on

asim +access +r +m+cordic_0  -L xil_defaultlib -L xbip_utils_v3_0_15 -L c_reg_fd_v12_0_11 -L xbip_dsp48_wrapper_v3_0_7 -L xbip_pipe_v3_0_11 -L c_addsub_v12_0_21 -L mult_gen_v12_0_24 -L axi_utils_v2_0_11 -L cordic_v6_0_25 -L secureip -O5 xil_defaultlib.cordic_0

do {cordic_0.udo}

run 1000ns

endsim

quit -force
