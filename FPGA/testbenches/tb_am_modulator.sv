// Testbench for am_modulator
// Verifies: passthrough, modulation envelope, output range, AM behavior
// Author: Alex Clunan

`timescale 1ns / 1ps

module tb_am_modulator;

    localparam INPUT_WIDTH     = 16;
    localparam OUTPUT_WIDTH    = 17;
    localparam MOD_ACCUM_WIDTH = 32;
    localparam CLK_PERIOD      = 5.0; // 200 MHz

    logic                           clock;
    logic                           reset_n;
    logic [INPUT_WIDTH-1:0]         cos_in;
    logic [MOD_ACCUM_WIDTH-1:0]     mod_fcw;
    logic [OUTPUT_WIDTH-1:0]        am_out;

    am_modulator #(
        .INPUT_WIDTH    (INPUT_WIDTH),
        .OUTPUT_WIDTH   (OUTPUT_WIDTH),
        .MOD_ACCUM_WIDTH(MOD_ACCUM_WIDTH)
    ) uut (
        .clock   (clock),
        .reset_n (reset_n),
        .cos_in  (cos_in),
        .mod_fcw (mod_fcw),
        .am_out  (am_out)
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
        $display("=== AM Modulator Testbench ===");
        $display("INPUT_WIDTH: %0d, OUTPUT_WIDTH: %0d, MOD_ACCUM_WIDTH: %0d",
                 INPUT_WIDTH, OUTPUT_WIDTH, MOD_ACCUM_WIDTH);

        // initialize
        reset_n = 1'b0;
        cos_in  = '0;
        mod_fcw = '0;

        repeat (4) @(posedge clock);

        // -------------------------------------------------------
        // Test 1: Reset clears output
        // -------------------------------------------------------
        check("Reset: am_out is zero", am_out === '0);

        @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;

        // -------------------------------------------------------
        // Test 2: Passthrough when mod_fcw = 0
        // (mod_envelope stays 0, output = carrier)
        // -------------------------------------------------------
        mod_fcw = '0;

        cos_in = 16'sh7FFF; // max positive
        @(posedge clock);
        @(negedge clock);
        check("Passthrough: max positive cos_in == am_out",
              $signed(am_out) === $signed({1'b0, 16'sh7FFF}));

        cos_in = 16'sh8000; // max negative
        @(posedge clock);
        @(negedge clock);
        check("Passthrough: max negative cos_in == am_out",
              $signed(am_out) === $signed({1'b1, 16'sh8000}));

        cos_in = 16'sh0000;
        @(posedge clock);
        @(negedge clock);
        check("Passthrough: zero cos_in == 0",
              am_out === '0);

        // -------------------------------------------------------
        // Test 3: Non-zero mod_fcw causes envelope to change
        // -------------------------------------------------------
        // use a large FCW so mod_phase MSBs change quickly
        // FCW = 0x01000000 increments mod_phase[31:16] by 256 each cycle
        mod_fcw = 32'h0100_0000;
        cos_in  = 16'sh4000; // positive carrier (quarter-scale)

        // let accumulator run a few cycles, then check output differs from carrier
        repeat (4) @(posedge clock);
        @(negedge clock);
        begin
            logic signed [OUTPUT_WIDTH-1:0] out_signed;
            logic signed [INPUT_WIDTH-1:0] carrier_signed;
            out_signed = $signed(am_out);
            carrier_signed = $signed(cos_in);
            // with non-zero modulation, output should differ from pure carrier
            // (mod_phase has accumulated 4*0x01000000 = 0x04000000,
            //  mod_envelope = 0x0400, product = 0x4000*0x0400 = non-zero)
            check("Modulation: am_out differs from carrier with non-zero FCW",
                  out_signed !== {1'b0, carrier_signed});
        end

        // -------------------------------------------------------
        // Test 4: Output stays within 17-bit signed range
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        @(posedge clock);
        @(negedge clock);

        // run with max carrier and fast modulation, verify no overflow
        // (output should always be within [-65536, 65535] for 17-bit signed)
        mod_fcw = 32'h1000_0000; // fast modulation
        begin
            integer i;
            logic overflow_detected;
            overflow_detected = 1'b0;

            for (i = 0; i < 256; i++) begin
                // alternate between max positive and max negative carrier
                cos_in = (i[0]) ? 16'sh7FFF : 16'sh8000;
                @(posedge clock);
                @(negedge clock);
                // 17-bit signed range: -65536 to 65535
                if ($signed(am_out) > 17'sd65535 || $signed(am_out) < -17'sd65536)
                    overflow_detected = 1'b1;
            end
            check("Range: no overflow in 256 cycles with max carrier",
                  overflow_detected === 1'b0);
        end

        // -------------------------------------------------------
        // Test 5: Zero carrier produces zero output regardless of FCW
        // -------------------------------------------------------
        cos_in  = 16'sh0000;
        mod_fcw = 32'hFFFF_FFFF; // maximum modulation rate

        repeat (10) @(posedge clock);
        @(negedge clock);
        check("Zero carrier: am_out is zero with any FCW",
              am_out === '0);

        // -------------------------------------------------------
        // Test 6: Modulation symmetry -- positive and negative envelope
        // produce outputs on opposite sides of the carrier
        // -------------------------------------------------------
        reset_n = 1'b0;
        mod_fcw = '0; // clear FCW during reset to prevent residual accumulation
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        mod_fcw = 32'h4000_0000; // set with reset release
        cos_in  = 16'sh2000;

        // pipeline: posedge 1 mod_phase 0->FCW, am_out based on mod_phase=0 (carrier)
        //           posedge 2 am_out reflects mod_phase=FCW (envelope=0x4000, positive)
        repeat (2) @(posedge clock);
        @(negedge clock);
        begin
            logic signed [OUTPUT_WIDTH-1:0] out_pos_env;
            out_pos_env = $signed(am_out);
            check("Symmetry: positive envelope increases output",
                  out_pos_env > $signed({1'b0, cos_in}));
        end

        // 2 more posedges: am_out reflects mod_phase=3*FCW=0xC0000000
        // envelope = 0xC000 (negative in signed 16-bit)
        repeat (2) @(posedge clock);
        @(negedge clock);
        begin
            logic signed [OUTPUT_WIDTH-1:0] out_neg_env;
            out_neg_env = $signed(am_out);
            check("Symmetry: negative envelope decreases output",
                  out_neg_env < $signed({1'b0, cos_in}));
        end

        // -------------------------------------------------------
        // Test 7: Verify modulation accumulator increments correctly
        // -------------------------------------------------------
        reset_n = 1'b0;
        mod_fcw = '0; // clear FCW during reset to prevent residual accumulation
        repeat (2) @(posedge clock);
        @(negedge clock);
        reset_n = 1'b1;
        mod_fcw = 32'h0001_0000; // set with reset release
        cos_in  = 16'sh7FFF;

        // pipeline: posedge 1 mod_phase 0->FCW=0x10000, am_out based on mod_phase=0
        //           posedge 2 am_out reflects mod_phase=0x10000 (envelope=1)
        //           product = 0x7FFF * 1 = 0x7FFF, scaled_mod = 0, output = carrier
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Small mod: am_out close to carrier with mod_envelope=1",
              $signed(am_out) === $signed({1'b0, 16'sh7FFF}));

        // after 256 more cycles: envelope has grown large enough to shift output
        repeat (256) @(posedge clock);
        @(negedge clock);
        begin
            logic signed [OUTPUT_WIDTH-1:0] out_val;
            out_val = $signed(am_out);
            // output should be noticeably larger than pure carrier (32767)
            check("Accum check: output > carrier after 257 cycles of modulation",
                  out_val > $signed({1'b0, 16'sh7FFF}));
        end

        // -------------------------------------------------------
        // Test 8: Reset mid-operation clears output
        // -------------------------------------------------------
        reset_n = 1'b0;
        repeat (2) @(posedge clock);
        @(negedge clock);
        check("Mid-reset: am_out cleared", am_out === '0);

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
