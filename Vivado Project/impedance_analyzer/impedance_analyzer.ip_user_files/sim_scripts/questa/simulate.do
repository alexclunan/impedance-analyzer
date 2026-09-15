onbreak {quit -f}
onerror {quit -f}

vsim  -lib xil_defaultlib tb_phase_accumulator_opt

set NumericStdNoWarnings 1
set StdArithNoWarnings 1

do {wave.do}

view wave
view structure
view signals

do {tb_phase_accumulator.udo}

run 1000ns

quit -force
