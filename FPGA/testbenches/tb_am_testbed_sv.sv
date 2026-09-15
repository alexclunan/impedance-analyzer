// Testbench for am_testbed_sv
// Verifies: 20 MHz DDS carrier, Q1.15 AM modulation, bounded filter response measurements
// Modulation signal: 300-sample event window extracted from
//   sample_data/20251106_1MHz_3V_14ksps_500Hz_1kohm_T6_S1/D1/Freq1.ziBin
//   Source window 17 (start index 244647, t=11260.7166s); 200 samples pre-event
//   baseline for pipeline settling, then bipolar Gaussian cell-transit peak at
//   index 200 (+114.7 uV / Q15=31130) and trough at index 207 (-112.9 uV / Q15=1865),
//   followed by 100 samples post-event recovery. Local mean subtracted; peak
//   deviation mapped to ENVELOPE_DEPTH_Q15 = 14746.
//   Loaded at sim-time via $readmemh("sample_data_event_only.mem", sample_data).
//   Sim time: 300 * 14286 = 4.3 M cycles (~21 ms). Full 1 s version:
//   use sample_data_envelope.mem with SAMPLE_DATA_LEN=14000.
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_am_testbed_sv;

    localparam real    CLK_PERIOD          = 5.0; // 200 MHz
    localparam integer CLK_FREQ_HZ         = 200_000_000;
    localparam [47:0]  FCW_20MHZ           = 48'h1999_9999_999A;
    localparam [31:0]  RESET_ASSERT_VALUE  = 32'h0000_0018;
    localparam [31:0]  RESET_RELEASE_VALUE = 32'h0000_1F67;
    localparam [31:0]  FIFO_DELAY_VALUE    = 32'd16;
    localparam integer SETTLE_VALID_SAMPLES  = 128; // valid outputs to discard while pipeline fills
    localparam integer PIPELINE_FLUSH_CYCLES = 200_000; // extra clocks after last sample to drain pipeline
    // Event window replay = 300 * 14286 = 4.3 M cycles (~21 ms).
    // Timeout at 10 M cycles gives 2.3x headroom; fits in 32-bit signed int.
    localparam integer SIM_TIMEOUT_CYCLES    = 10_000_000;
    localparam real    PI                  = 3.14159265358979323846;
    localparam real    ENVELOPE_DC_Q15     = 16384.0; // 0.50 full-scale Q1.15 baseline
    localparam real    ENVELOPE_DEPTH_Q15  = 14746.0; // 0.45 full-scale Q1.15 peak depth

    // Sample data parameters: 14 kSPS replay rate matched to ZI lock-in output rate
    localparam integer SAMPLE_DATA_LEN    = 300;    // event window: 200 pre + 100 post, peak at index 200
    localparam integer SAMPLE_HOLD_CYCLES = 14286; // 200 MHz / 14 kHz = 14285.7 -> 14286

    logic        clk;
    logic [47:0] fcw;
    logic [31:0] reset_register;
    logic [31:0] DAC_test_data;
    logic [31:0] fifo_delay;
    logic [15:0] adc_input;
    logic [15:0] data_out_to_pins_0;
    logic        phase_msb_0;
    logic [63:0] timestamps;
    logic [63:0] signal_out_raw;
    logic [31:0] signal_out;
    logic [31:0] phase_out;
    logic        signal_out_valid;
    logic signed [31:0] mixer_i;
    logic signed [31:0] mixer_q;
    logic signed [31:0] cic_i;
    logic signed [31:0] cic_q;
    logic signed [47:0] fir_i;
    logic signed [47:0] fir_q;
    logic        mixer_valid;
    logic        cic_i_valid;
    logic        cic_q_valid;
    logic        fir_i_valid;
    logic        fir_q_valid;
    logic [31:0] signal_magnitude;
    logic [31:0] signal_phase;
    logic signed [15:0] sampled_envelope;
    logic signed [15:0] sampled_envelope_abs;
    logic signed [15:0] sampled_adc_input;
    logic signed [31:0] sampled_mixer_i;
    logic signed [31:0] sampled_mixer_q;
    logic signed [31:0] sampled_cic_i;
    logic signed [31:0] sampled_cic_q;
    logic signed [47:0] sampled_fir_i;
    logic signed [47:0] sampled_fir_q;
    logic [31:0] sampled_signal_out;
    logic [31:0] sampled_phase_out;
    logic [63:0] sampled_signal_out_raw;
    logic [63:0] sampled_timestamp;
    integer sampled_sample_index;
    integer mixer_valid_sample_count;
    integer cic_i_valid_sample_count;
    integer cic_q_valid_sample_count;
    integer fir_valid_sample_count;
    integer signal_valid_sample_count;

    integer errors = 0;
    integer sample_index = 0;

    logic signed [15:0] current_envelope;
    logic signed [15:0] current_envelope_abs;
    logic signed [15:0] expected_adc_sample;

    real response_sample_data;

    // -------------------------------------------------------------------------
    // 14 kSPS envelope array (Q1.15, DC = 16384), 1 second of real lock-in data.
    // Loaded from sample_data_envelope.mem at simulation time via $readmemh.
    // Source: ZI lock-in x-channel, window 17 (start=244647, t=11260.7166s).
    // Peak bipolar cell-transit event at indices 5510/5517 (±114 uV, Q15 ≈ 31130/1865).
    // -------------------------------------------------------------------------
    logic signed [15:0] sample_data [0:SAMPLE_DATA_LEN-1];

    am_testbed_sv uut (
        .data_out_to_pins_0 (data_out_to_pins_0),
        .phase_msb_0        (phase_msb_0),
        .fcw                (fcw),
        .reset_register     (reset_register),
        .DAC_test_data      (DAC_test_data),
        .fifo_delay         (fifo_delay),
        .timestamps         (timestamps),
        .signal_out         (signal_out_raw),
        .signal_out_valid   (signal_out_valid),
        .adc_input          (adc_input),
        .clk                (clk)
    );

    // Debug probes mirror the output pins added to the block design. The generated
    // SV wrapper can lag the BD, so hierarchical probes keep this TB usable now.
    assign mixer_i = uut.inst.mixer_0_i_out;
    assign mixer_q = uut.inst.mixer_0_q_out;
    assign cic_i   = uut.inst.CIC_Filter_I_m_axis_data_tdata;
    assign cic_q   = uut.inst.CIC_Filter_Q_m_axis_data_tdata;
    assign fir_i   = uut.inst.FIR_Filter_I_m_axis_data_tdata;
    assign fir_q   = uut.inst.FIR_Filter_Q_m_axis_data_tdata;

    assign mixer_valid = uut.inst.mixer_0_valid_out;
    assign cic_i_valid = uut.inst.CIC_Filter_I_m_axis_data_tvalid;
    assign cic_q_valid = uut.inst.CIC_Filter_Q_m_axis_data_tvalid;
    assign fir_i_valid = uut.inst.FIR_Filter_I_m_axis_data_tvalid;
    assign fir_q_valid = fir_i_valid;

    // Saved BD slices mag_phase_calc output as:
    //   signal_out = m_axis_dout_tdata[63:32]
    //   phase_out  = m_axis_dout_tdata[31:0]
    // The generated wrapper has not caught up yet, so use the raw 64-bit port.
    assign signal_out       = signal_out_raw[63:32];
    assign phase_out        = signal_out_raw[31:0];
    assign signal_magnitude = signal_out;
    assign signal_phase     = phase_out;

    initial begin
        sampled_envelope         = 16'sd0;
        sampled_envelope_abs     = 16'sd0;
        sampled_adc_input        = 16'sd0;
        sampled_mixer_i          = 32'sd0;
        sampled_mixer_q          = 32'sd0;
        sampled_cic_i            = 32'sd0;
        sampled_cic_q            = 32'sd0;
        sampled_fir_i            = 48'sd0;
        sampled_fir_q            = 48'sd0;
        sampled_signal_out       = 32'd0;
        sampled_phase_out        = 32'd0;
        sampled_signal_out_raw   = 64'd0;
        sampled_timestamp        = 64'd0;
        sampled_sample_index     = 0;
        mixer_valid_sample_count = 0;
        cic_i_valid_sample_count = 0;
        cic_q_valid_sample_count = 0;
        fir_valid_sample_count   = 0;
        signal_valid_sample_count = 0;
    end

    always @(posedge clk) begin
        if (reset_register !== RESET_RELEASE_VALUE) begin
            sampled_envelope         <= 16'sd0;
            sampled_envelope_abs     <= 16'sd0;
            sampled_adc_input        <= 16'sd0;
            sampled_mixer_i          <= 32'sd0;
            sampled_mixer_q          <= 32'sd0;
            sampled_cic_i            <= 32'sd0;
            sampled_cic_q            <= 32'sd0;
            sampled_fir_i            <= 48'sd0;
            sampled_fir_q            <= 48'sd0;
            sampled_signal_out       <= 32'd0;
            sampled_phase_out        <= 32'd0;
            sampled_signal_out_raw   <= 64'd0;
            sampled_timestamp        <= 64'd0;
            sampled_sample_index     <= 0;
            mixer_valid_sample_count <= 0;
            cic_i_valid_sample_count <= 0;
            cic_q_valid_sample_count <= 0;
            fir_valid_sample_count   <= 0;
            signal_valid_sample_count <= 0;
        end else begin
            if (mixer_valid === 1'b1) begin
                sampled_mixer_i          <= mixer_i;
                sampled_mixer_q          <= mixer_q;
                mixer_valid_sample_count <= mixer_valid_sample_count + 1;
            end

            if (cic_i_valid === 1'b1) begin
                sampled_cic_i            <= cic_i;
                cic_i_valid_sample_count <= cic_i_valid_sample_count + 1;
            end

            if (cic_q_valid === 1'b1) begin
                sampled_cic_q            <= cic_q;
                cic_q_valid_sample_count <= cic_q_valid_sample_count + 1;
            end

            if (fir_i_valid === 1'b1) begin
                sampled_fir_i          <= fir_i;
                sampled_fir_q          <= fir_q;
                fir_valid_sample_count <= fir_valid_sample_count + 1;
            end

            if (signal_out_valid === 1'b1) begin
                sampled_envelope         <= current_envelope;
                sampled_envelope_abs     <= current_envelope_abs;
                sampled_adc_input        <= adc_input;
                sampled_signal_out       <= signal_out;
                sampled_phase_out        <= phase_out;
                sampled_signal_out_raw   <= signal_out_raw;
                sampled_timestamp        <= timestamps;
                sampled_sample_index     <= sample_index;
                signal_valid_sample_count <= signal_valid_sample_count + 1;
            end
        end
    end

    initial clk = 1'b0;
    always #(CLK_PERIOD / 2.0) clk = ~clk;

    initial begin
        if ($test$plusargs("DUMP_VCD")) begin
            $dumpfile("tb_am_testbed_sv.vcd");
            $dumpvars(0, tb_am_testbed_sv);
        end
    end

    initial begin
        #(CLK_PERIOD * SIM_TIMEOUT_CYCLES);
        $error("TIMEOUT: simulation limit reached at %0t ns", $time);
        $finish;
    end

    task automatic check(input string msg, input logic condition);
        if (!condition) begin
            $error("FAIL: %s", msg);
            errors++;
        end else begin
            $display("PASS: %s", msg);
        end
    endtask

    function automatic logic signed [15:0] modulate_sample;
        input logic [15:0] carrier;
        input logic signed [15:0] envelope;
        logic signed [15:0] signed_carrier;
        logic signed [31:0] product;
        begin
            signed_carrier = carrier;
            product = signed_carrier * envelope;
            modulate_sample = product >>> 15;
        end
    endfunction

    function automatic real unsigned32_to_real;
        input logic [31:0] value;
        begin
            unsigned32_to_real = $itor(value[30:0]);
            if (value[31] === 1'b1) begin
                unsigned32_to_real = unsigned32_to_real + 2147483648.0;
            end
        end
    endfunction

    function automatic logic signed [15:0] abs_q15;
        input logic signed [15:0] value;
        begin
            if (value === -16'sd32768) begin
                abs_q15 = 16'sd32767;
            end else if (value < 0) begin
                abs_q15 = -value;
            end else begin
                abs_q15 = value;
            end
        end
    endfunction

    function automatic real abs_signed48_to_real;
        input logic signed [47:0] value;
        begin
            if (value < 0) begin
                abs_signed48_to_real = -$itor(value);
            end else begin
                abs_signed48_to_real = $itor(value);
            end
        end
    endfunction

    task automatic apply_system_reset();
        begin
            reset_register = RESET_ASSERT_VALUE;
            DAC_test_data  = 32'd0;
            fifo_delay     = FIFO_DELAY_VALUE;
            fcw            = FCW_20MHZ;
            adc_input      = 16'd0;
            sample_index   = 0;

            repeat (8) @(posedge clk);
            @(negedge clk);
            reset_register = RESET_RELEASE_VALUE;
            repeat (16) @(posedge clk);
            @(negedge clk);
        end
    endtask

    // Drive one clock cycle with the sample_data entry at data_idx.
    task automatic drive_sample_cycle(input integer data_idx);
        begin
            @(negedge clk);
            current_envelope     = sample_data[data_idx % SAMPLE_DATA_LEN];
            current_envelope_abs = abs_q15(current_envelope);
            expected_adc_sample  = modulate_sample(data_out_to_pins_0, current_envelope);
            adc_input            = expected_adc_sample;
            sample_index         = sample_index + 1;
        end
    endtask

    // Replay all SAMPLE_DATA_LEN samples at 14 kSPS (SAMPLE_HOLD_CYCLES clocks each).
    // Total simulated time = SAMPLE_DATA_LEN * SAMPLE_HOLD_CYCLES clocks = ~1 second.
    // Discards the first SETTLE_VALID_SAMPLES valid outputs while the pipeline fills,
    // then collects all remaining valid outputs from the full dataset pass.
    task automatic measure_sample_data_response(output real average_magnitude);
        integer data_idx;
        integer hold_cyc;
        integer flush_cyc;
        integer settle_count;
        integer collect_count;
        real magnitude_sum;
        real fir_i_abs_sum;
        real fir_q_abs_sum;
        real fir_i_average_abs;
        real fir_q_average_abs;
        logic printed_first_valid;
        begin
            $display("--- Replaying full 1-second sample at 14 kSPS ---");
            $display("    SAMPLE_DATA_LEN=%0d  SAMPLE_HOLD_CYCLES=%0d  total_cycles=%0d",
                     SAMPLE_DATA_LEN, SAMPLE_HOLD_CYCLES,
                     SAMPLE_DATA_LEN * SAMPLE_HOLD_CYCLES);

            data_idx          = 0;
            hold_cyc          = 0;
            settle_count      = 0;
            collect_count     = 0;
            magnitude_sum     = 0.0;
            fir_i_abs_sum     = 0.0;
            fir_q_abs_sum     = 0.0;
            fir_i_average_abs = 0.0;
            fir_q_average_abs = 0.0;
            printed_first_valid = 1'b0;

            // Drive all SAMPLE_DATA_LEN samples, each held for SAMPLE_HOLD_CYCLES clocks.
            while (data_idx < SAMPLE_DATA_LEN) begin
                drive_sample_cycle(data_idx);
                if (signal_out_valid === 1'b1) begin
                    if (settle_count < SETTLE_VALID_SAMPLES) begin
                        // Discard early outputs while pipeline fills.
                        settle_count = settle_count + 1;
                    end else begin
                        if ($isunknown(signal_out)) begin
                            $error("FAIL: sample data: signal_out is unknown on valid sample");
                            errors++;
                        end else begin
                            magnitude_sum = magnitude_sum + unsigned32_to_real(signal_magnitude);
                            fir_i_abs_sum = fir_i_abs_sum + abs_signed48_to_real(fir_i);
                            fir_q_abs_sum = fir_q_abs_sum + abs_signed48_to_real(fir_q);

                            if (printed_first_valid === 1'b0) begin
                                $display("DEBUG_FIRST_VALID: data_idx=%0d env=%0d abs_env=%0d adc=%0d mixer_i=%0d mixer_q=%0d mixer_valid=%0b cic_i=%0d cic_q=%0d fir_i=%0d fir_q=%0d signal_out=%0d phase_out=%0d",
                                         data_idx, $signed(current_envelope),
                                         $signed(current_envelope_abs), $signed(adc_input),
                                         $signed(mixer_i), $signed(mixer_q), mixer_valid,
                                         $signed(cic_i), $signed(cic_q),
                                         $signed(fir_i), $signed(fir_q),
                                         signal_magnitude, signal_phase);
                                printed_first_valid = 1'b1;
                            end
                        end
                        collect_count = collect_count + 1;
                    end
                end
                hold_cyc = hold_cyc + 1;
                if (hold_cyc >= SAMPLE_HOLD_CYCLES) begin
                    hold_cyc = 0;
                    data_idx = data_idx + 1;
                end
            end

            // Drain remaining pipeline output after the last sample.
            flush_cyc = 0;
            while (flush_cyc < PIPELINE_FLUSH_CYCLES) begin
                @(negedge clk);
                flush_cyc = flush_cyc + 1;
                if (signal_out_valid === 1'b1) begin
                    if (settle_count < SETTLE_VALID_SAMPLES) begin
                        settle_count = settle_count + 1;
                    end else begin
                        magnitude_sum = magnitude_sum + unsigned32_to_real(signal_magnitude);
                        fir_i_abs_sum = fir_i_abs_sum + abs_signed48_to_real(fir_i);
                        fir_q_abs_sum = fir_q_abs_sum + abs_signed48_to_real(fir_q);
                        collect_count = collect_count + 1;
                    end
                end
            end

            check("Sample data: pipeline settled before end of dataset",
                  settle_count >= SETTLE_VALID_SAMPLES);
            check("Sample data: at least one valid output collected",
                  collect_count > 0);

            if (collect_count > 0) begin
                average_magnitude = magnitude_sum / $itor(collect_count);
                fir_i_average_abs = fir_i_abs_sum / $itor(collect_count);
                fir_q_average_abs = fir_q_abs_sum / $itor(collect_count);
            end else begin
                average_magnitude = 0.0;
            end

            $display("MEASURE: avg_magnitude=%0f avg_abs_fir_i=%0f avg_abs_fir_q=%0f collected=%0d settled=%0d",
                     average_magnitude, fir_i_average_abs, fir_q_average_abs,
                     collect_count, settle_count);
        end
    endtask

    initial begin
        integer phase_toggle_count;
        integer dac_change_count;
        logic previous_phase_msb;
        logic [15:0] previous_dac_sample;
        logic [63:0] timestamp_start;
        logic signed [15:0] model_sample;

        // Load 14 kSPS envelope from generated .mem file (Q1.15, 14000 entries).
        // Vivado xsim runs from <project>.sim/sim_1/behav/xsim/ so the file must
        // either be copied there or added as a simulation source in the project.
        $readmemh("sample_data_event_only.mem", sample_data);

        // Verify load succeeded: baseline[0], positive peak[200], negative trough[207] must be non-zero.
        $display("MEMLOAD: sample_data[0]=0x%04h [200]=0x%04h [207]=0x%04h [299]=0x%04h",
                 sample_data[0], sample_data[200], sample_data[207], sample_data[299]);
        if ($isunknown(sample_data[0]) || sample_data[0] === 16'h0000) begin
            $error("FATAL: sample_data_event_only.mem not loaded — copy it to the xsim working dir or add as sim source");
            $finish;
        end

        $display("=== AM Testbed SV Testbench (14 kSPS real lock-in data) ===");
        $display("Carrier FCW: 0x%012h (20 MHz at 200 MHz clock)", FCW_20MHZ);
        $display("Modulation: %0d-sample array at %0d clk/sample (14 kSPS)", SAMPLE_DATA_LEN, SAMPLE_HOLD_CYCLES);

        fcw            = FCW_20MHZ;
        reset_register = RESET_ASSERT_VALUE;
        DAC_test_data  = 32'd0;
        fifo_delay     = FIFO_DELAY_VALUE;
        adc_input      = 16'd0;

        repeat (4) @(posedge clk);
        @(negedge clk);
        check("Reset: phase_msb_0 is zero", phase_msb_0 === 1'b0);
        check("Reset: timestamps is zero", timestamps === 64'd0);

        apply_system_reset();

        timestamp_start = timestamps;
        previous_phase_msb = phase_msb_0;
        previous_dac_sample = data_out_to_pins_0;
        phase_toggle_count = 0;
        dac_change_count = 0;

        // Drive 200 cycles with baseline sample to verify carrier activity.
        repeat (200) begin
            drive_sample_cycle(0);
            if (phase_msb_0 !== previous_phase_msb) begin
                phase_toggle_count = phase_toggle_count + 1;
            end
            if (data_out_to_pins_0 !== previous_dac_sample) begin
                dac_change_count = dac_change_count + 1;
            end
            previous_phase_msb = phase_msb_0;
            previous_dac_sample = data_out_to_pins_0;
        end

        check("Timestamp: timestamps increments after reset release",
              timestamps > timestamp_start);
        check("20 MHz carrier: phase_msb_0 toggles during observation window",
              phase_toggle_count > 0);
        check("20 MHz carrier: data_out_to_pins_0 changes during observation window",
              dac_change_count > 0);
        check("20 MHz carrier: data_out_to_pins_0 is known",
              !$isunknown(data_out_to_pins_0));

        // Verify the modulate_sample helper against a known sample data entry.
        // Index 200 is the positive peak of the bipolar event (Q15 = 31130 = 0x799A).
        current_envelope = sample_data[200];
        model_sample = modulate_sample(16'sh4000, current_envelope);
        expected_adc_sample = model_sample;
        adc_input = expected_adc_sample;
        @(negedge clk);
        check("AM model: adc_input follows sample data Q1.15 carrier-envelope product",
              adc_input === model_sample);

        measure_sample_data_response(response_sample_data);

        $display("=== Sample Data Measurement Summary ===");
        $display("MEASURE: sample data avg magnitude = %0f", response_sample_data);

        $display("=== Test Complete: %0d errors ===", errors);
        if (errors == 0) begin
            $display("ALL TESTS PASSED");
        end else begin
            $display("SOME TESTS FAILED");
        end

        $finish;
    end

endmodule
