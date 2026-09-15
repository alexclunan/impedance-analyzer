transcript off
onbreak {quit -force}
onerror {quit -force}
transcript on

asim +access +r +m+tb_phase_accumulator  -L xil_defaultlib -L xilinx_vip -L xpm -L xilinx_vip -L unisims_ver -L unimacro_ver -L secureip -O5 xil_defaultlib.tb_phase_accumulator xil_defaultlib.glbl

do {tb_phase_accumulator.udo}

run 1000ns

endsim

quit -force
