// Testbench for decimator_lpf_wrapper
// Verifies: AXI-Stream plumbing, config loading, enable gating, FIR reload
// CIC and FIR IP ports are exposed, so the testbench drives/monitors them directly
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_decimator_lpf_wrapper;

    localparam DATA_WIDTH   = 32;
    localparam CONFIG_WIDTH = 16;
    localparam RELOAD_WIDTH = 24;
    localparam CLK_PERIOD   = 5.0; // 200 MHz

    logic                       clock;
    logic                       aresetn;
    logic [DATA_WIDTH-1:0]      data_in;
    logic                       data_valid;
    logic                       processing_enable;
    logic [CONFIG_WIDTH-1:0]    decimation_ratio;
    logic                       config_load;
    logic [RELOAD_WIDTH-1:0]    fir_reload_data;
    logic                       fir_reload_valid;
    logic                       fir_reload_last;
    logic [DATA_WIDTH-1:0]      data_out;
    logic                       data_valid_out;

    // CIC IP interface (driven/monitored by testbench)
    logic [DATA_WIDTH-1:0]      cic_s_axis_data_tdata;
    logic                       cic_s_axis_data_tvalid;
    logic [CONFIG_WIDTH-1:0]    cic_s_axis_config_tdata;
    logic                       cic_s_axis_config_tvalid;
    logic [DATA_WIDTH-1:0]      cic_m_axis_data_tdata;
    logic                       cic_m_axis_data_tvalid;

    // FIR IP interface (driven/monitored by testbench)
    logic [DATA_WIDTH-1:0]      fir_s_axis_data_tdata;
    logic                       fir_s_axis_data_tvalid;
    logic [RELOAD_WIDTH-1:0]    fir_s_axis_reload_tdata;
    logic                       fir_s_axis_reload_tvalid;
    logic                       fir_s_axis_reload_tlast;
    logic [DATA_WIDTH-1:0]      fir_m_axis_data_tdata;
    logic                       fir_m_axis_data_tvalid;

    decimator_lpf_wrapper #(
        .DATA_WIDTH   (DATA_WIDTH),
        .CONFIG_WIDTH (CONFIG_WIDTH),
        .RELOAD_WIDTH (RELOAD_WIDTH)
    ) uut (
        .clock                   (clock),
        .aresetn                 (aresetn),
        .data_in                 (data_in),
        .data_valid              (data_valid),
        .processing_enable       (processing_enable),
        .decimation_ratio        (decimation_ratio),
        .config_load             (config_load),
        .fir_reload_data         (fir_reload_data),
        .fir_reload_valid        (fir_reload_valid),
        .fir_reload_last         (fir_reload_last),
        .data_out                (data_out),
        .data_valid_out          (data_valid_out),
        .cic_s_axis_data_tdata   (cic_s_axis_data_tdata),
        .cic_s_axis_data_tvalid  (cic_s_axis_data_tvalid),
        .cic_s_axis_config_tdata (cic_s_axis_config_tdata),
        .cic_s_axis_config_tvalid(cic_s_axis_config_tvalid),
        .cic_m_axis_data_tdata   (cic_m_axis_data_tdata),
        .cic_m_axis_data_tvalid  (cic_m_axis_data_tvalid),
        .fir_s_axis_data_tdata   (fir_s_axis_data_tdata),
        .fir_s_axis_data_tvalid  (fir_s_axis_data_tvalid),
        .fir_s_axis_reload_tdata (fir_s_axis_reload_tdata),
        .fir_s_axis_reload_tvalid(fir_s_axis_reload_tvalid),
        .fir_s_axis_reload_tlast (fir_s_axis_reload_tlast),
        .fir_m_axis_data_tdata   (fir_m_axis_data_tdata),
        .fir_m_axis_data_tvalid  (fir_m_axis_data_tvalid)
    );

    // Clock generation
    initial clock = 1'b0;
    always #(CLK_PERIOD / 2.0) clock = ~clock;

    integer errors = 0;

    task automatic check(input string msg, input logic condition);
        if (!condition) begin
            $error("FAIL: %s", msg);
            errors++;
        end else begin
            $display("PASS: %s", msg);
        end
    endtask

    initial begin
        $display("=== Decimator LPF Wrapper Testbench ===");
        $display("DATA_WIDTH: %0d, CONFIG_WIDTH: %0d, RELOAD_WIDTH: %0d",
                 DATA_WIDTH, CONFIG_WIDTH, RELOAD_WIDTH);

        // initialize
        aresetn           = 1'b0;
        data_in           = '0;
        data_valid        = 1'b0;
        processing_enable = 1'b0;
        decimation_ratio  = '0;
        config_load       = 1'b0;
        fir_reload_data   = '0;
        fir_reload_valid  = 1'b0;
        fir_reload_last   = 1'b0;
        cic_m_axis_data_tdata  = '0;
        cic_m_axis_data_tvalid = 1'b0;
        fir_m_axis_data_tdata  = '0;
        fir_m_axis_data_tvalid = 1'b0;

        repeat (4) @(posedge clock);

        // -------------------------------------------------------
        // Test 1: Reset state
        // -------------------------------------------------------
        check("Reset: cic_s_axis_data_tvalid is low",
              cic_s_axis_data_tvalid === 1'b0);
        check("Reset: cic_s_axis_config_tvalid is low",
              cic_s_axis_config_tvalid === 1'b0);

        // -------------------------------------------------------
        // Test 2: Processing enable gates CIC data input
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);
        aresetn = 1'b1;

        data_in    = 32'hDEADBEEF;
        data_valid = 1'b1;
        processing_enable = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("Enable gate: cic_s_axis_data_tvalid low when disabled",
              cic_s_axis_data_tvalid === 1'b0);
        check("Enable gate: cic_s_axis_data_tdata passes data",
              cic_s_axis_data_tdata === 32'hDEADBEEF);

        processing_enable = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Enable gate: cic_s_axis_data_tvalid high when enabled",
              cic_s_axis_data_tvalid === 1'b1);

        // -------------------------------------------------------
        // Test 3: Data passes through to CIC input
        // -------------------------------------------------------
        data_in = 32'h12345678;
        @(posedge clock);
        @(negedge clock);
        check("Data passthrough: cic_s_axis_data_tdata == 0x12345678",
              cic_s_axis_data_tdata === 32'h12345678);

        // -------------------------------------------------------
        // Test 4: CIC config loading -- single pulse
        // -------------------------------------------------------
        data_valid        = 1'b0;
        processing_enable = 1'b0;

        decimation_ratio = 16'd500;
        config_load      = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Config load: cic_s_axis_config_tvalid pulsed high",
              cic_s_axis_config_tvalid === 1'b1);
        check("Config load: cic_s_axis_config_tdata == 500",
              cic_s_axis_config_tdata === 16'd500);

        @(posedge clock);
        @(negedge clock);
        check("Config load: tvalid returns low after one cycle",
              cic_s_axis_config_tvalid === 1'b0);

        // verify holding config_load high does not re-pulse
        @(posedge clock);
        @(negedge clock);
        check("Config load: no re-pulse while held high",
              cic_s_axis_config_tvalid === 1'b0);

        config_load = 1'b0;

        // -------------------------------------------------------
        // Test 5: Config re-load after deasserting config_load
        // -------------------------------------------------------
        @(posedge clock);
        @(negedge clock);

        decimation_ratio = 16'd1000;
        config_load      = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Config re-load: tvalid pulsed for new ratio",
              cic_s_axis_config_tvalid === 1'b1);
        check("Config re-load: tdata == 1000",
              cic_s_axis_config_tdata === 16'd1000);

        config_load = 1'b0;

        // -------------------------------------------------------
        // Test 6: CIC output to FIR input plumbing
        // -------------------------------------------------------
        cic_m_axis_data_tdata  = 32'hCAFEBABE;
        cic_m_axis_data_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("CIC->FIR: fir_s_axis_data_tdata == 0xCAFEBABE",
              fir_s_axis_data_tdata === 32'hCAFEBABE);
        check("CIC->FIR: fir_s_axis_data_tvalid high",
              fir_s_axis_data_tvalid === 1'b1);

        cic_m_axis_data_tvalid = 1'b0;
        @(posedge clock);
        @(negedge clock);
        check("CIC->FIR: fir_s_axis_data_tvalid low when CIC invalid",
              fir_s_axis_data_tvalid === 1'b0);

        // -------------------------------------------------------
        // Test 7: FIR reload passthrough
        // -------------------------------------------------------
        fir_reload_data  = 24'hABCDEF;
        fir_reload_valid = 1'b1;
        fir_reload_last  = 1'b0;

        @(posedge clock);
        @(negedge clock);
        check("FIR reload: tdata == 0xABCDEF",
              fir_s_axis_reload_tdata === 24'hABCDEF);
        check("FIR reload: tvalid high",
              fir_s_axis_reload_tvalid === 1'b1);
        check("FIR reload: tlast low",
              fir_s_axis_reload_tlast === 1'b0);

        fir_reload_data  = 24'h123456;
        fir_reload_last  = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("FIR reload last: tdata == 0x123456",
              fir_s_axis_reload_tdata === 24'h123456);
        check("FIR reload last: tlast high",
              fir_s_axis_reload_tlast === 1'b1);

        fir_reload_valid = 1'b0;
        fir_reload_last  = 1'b0;

        // -------------------------------------------------------
        // Test 8: FIR output to wrapper output
        // -------------------------------------------------------
        fir_m_axis_data_tdata  = 32'h0000FACE;
        fir_m_axis_data_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("FIR output: data_out == 0x0000FACE",
              data_out === 32'h0000FACE);
        check("FIR output: data_valid_out high",
              data_valid_out === 1'b1);

        fir_m_axis_data_tvalid = 1'b0;
        @(posedge clock);
        @(negedge clock);
        check("FIR output: data_valid_out low when FIR invalid",
              data_valid_out === 1'b0);

        // -------------------------------------------------------
        // Test 9: Full pipeline loopback
        // -------------------------------------------------------
        processing_enable = 1'b1;
        data_in    = 32'h55AA55AA;
        data_valid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Full pipeline: CIC input valid with data",
              cic_s_axis_data_tvalid === 1'b1 &&
              cic_s_axis_data_tdata === 32'h55AA55AA);

        // simulate CIC producing output
        cic_m_axis_data_tdata  = 32'h11223344;
        cic_m_axis_data_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Full pipeline: FIR receives CIC output",
              fir_s_axis_data_tdata === 32'h11223344 &&
              fir_s_axis_data_tvalid === 1'b1);

        // simulate FIR producing output
        fir_m_axis_data_tdata  = 32'hAABBCCDD;
        fir_m_axis_data_tvalid = 1'b1;

        @(posedge clock);
        @(negedge clock);
        check("Full pipeline: wrapper output from FIR",
              data_out === 32'hAABBCCDD &&
              data_valid_out === 1'b1);

        data_valid = 1'b0;
        cic_m_axis_data_tvalid = 1'b0;
        fir_m_axis_data_tvalid = 1'b0;

        // -------------------------------------------------------
        // Summary
        // -------------------------------------------------------
        $display("=== Test Complete: %0d errors ===", errors);
        if (errors == 0)
            $display("ALL TESTS PASSED");
        else
            $display("SOME TESTS FAILED");

        $finish;
    end

endmodule
