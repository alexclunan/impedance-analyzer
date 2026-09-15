// spi_rd_tristate.v
// Author: Alex Clunan
//
// Auto-tristate generator for a shared-SDIO (3-wire) SPI slave -- the AD9467
// ADC, whose SDIO pin is bidirectional and wired through the adc_sdio_buf IOBUF.
// The Zynq PS-SPI (cdns_spi) runs 4-wire full-duplex and NEVER releases MOSI, so
// on a register read it keeps driving the line over the ADC (master reads its
// own 0x00). The cdns-spi driver also does not support SPI_3WIRE. So we generate
// the IOBUF tristate here in the PL instead of from SPI0_MOSI_T.
//
// The module snoops CSB/SCLK/MOSI. SPI mode 0 (CPOL=0, CPHA=0), MSB first. The
// AD9467 instruction is 16 bits and bit15 (the first bit shifted) is R/W with
// 1 = READ. During a read the ADC drives SDIO starting in the data phase (after
// bit 16). So: latch the R/W bit on the first SCLK rising edge; once the 16-bit
// instruction has clocked in AND it was a read, assert the tristate to release
// MOSI so the ADC can drive back; hold until CSB deasserts. On a WRITE the
// tristate never asserts, so the master drives normally throughout.
//
// All snooped signals are synchronized/edge-detected in the fast fabric clock
// domain (SCLK ~1 MHz << clk), so SCLK is treated as data, not a clock.
//
// BD wiring: drive adc_sdio_buf/IOBUF_IO_T from mosi_tri (NOT from SPI0_MOSI_T,
// which is left unconnected). spi_csb/sclk/mosi tap the SPI0 EMIO outputs that
// go to the ADC (SPI0_SS_O, SPI0_SCLK_O, SPI0_MOSI_O). Leave IOBUF_IO_I fed by
// SPI0_MOSI_O and IOBUF_IO_O -> SPI0_MISO_I as they already are.
module spi_rd_tristate
    #(parameter INSTR_BITS = 16)   // AD9467 instruction word length
(
    input  wire clk,        // fabric clock (200 MHz)
    input  wire spi_csb,    // SPI0 chip select to the ADC (active low)
    input  wire spi_sclk,   // SPI0 serial clock
    input  wire spi_mosi,   // SPI0 MOSI (controller drive) -- carries the instr
    output wire mosi_tri    // 1 = tristate MOSI / release SDIO for the ADC
);

// --- synchronize the slow SPI signals into the fast clock domain ---
reg [2:0] csb_s;
reg [2:0] sclk_s;
reg [1:0] mosi_s;
always @(posedge clk) begin
    csb_s  <= {csb_s [1:0], spi_csb };
    sclk_s <= {sclk_s[1:0], spi_sclk};
    mosi_s <= {mosi_s[0],   spi_mosi };
end

wire csb_active = ~csb_s[2];                 // CSB is active low
wire sclk_rise  =  sclk_s[1] & ~sclk_s[2];   // rising edge of SCLK

// --- frame state ---
reg [5:0] bit_cnt;   // counts SCLK rising edges within one CSB frame
reg       rw_read;   // latched R/W bit (1 = read)
reg       tri_en;

always @(posedge clk) begin
    if (!csb_active) begin
        // frame idle: master owns the bus, reset the snooper
        bit_cnt <= 6'd0;
        rw_read <= 1'b0;
        tri_en  <= 1'b0;
    end else if (sclk_rise) begin
        // first bit of the instruction is R/W
        if (bit_cnt == 6'd0)
            rw_read <= mosi_s[1];
        // last instruction bit has now been captured by the ADC; if this was a
        // read, release MOSI before the data phase begins (next falling edge)
        if (bit_cnt == (INSTR_BITS-1) && rw_read)
            tri_en <= 1'b1;
        if (bit_cnt != 6'h3F)
            bit_cnt <= bit_cnt + 6'd1;
    end
end

// release only while the frame is active and the read data phase is reached
assign mosi_tri = tri_en & csb_active;

endmodule
