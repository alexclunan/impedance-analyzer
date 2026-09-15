# 02 — PL→PS→Ethernet Data Path (DMA → Packets → PC)

**Objective:** Move demod samples from PL to PS over the **reused** AXI DMA design, packetize them in PS userspace, and stream to the PC over Ethernet. Prove the path with a synthetic loopback before trusting real data.

**Prerequisites:** Doc 01 (network link up). Reused block design: AXI DMA (MM2S + S2MM), AXI4-Stream Data FIFO (stream-only, no AXI-Lite control), sample-hold, AM modulator, output packetizer, three interrupts via Concat → IRQ_F2P.

**Effort:** 1–2 days.

## Steps

1. **Linux DMA access.** Expose the S2MM (PL→PS) path to userspace. Add the AXI DMA node to the device tree and bring up a userspace path (e.g., Xilinx `dma-proxy` kernel module + app). Build the driver into the PetaLinux image.

2. **DMA buffers + coherency.** Allocate the receive buffers through the driver's coherent mapping, or do explicit cache invalidate before reading. Cache coherency on DMA buffers is the same hazard as the bare-metal design — here the driver manages it, but verify (stale-cache reads look like intermittent corruption).

3. **Userspace streamer.** App that pre-arms S2MM, blocks for completed buffers, frames them into packets, and sends over a UDP socket to the PC. Pre-arm S2MM *before* the PL produces data (S2MM pre-arming gotcha). Raise socket send buffer (`SO_SNDBUF`) to absorb bursts.

4. **Packet format.** Define and document a fixed header, e.g.:
   ```
   magic/version | seq_num (u32) | sample_index_or_timestamp | freq_channel_id | payload_len | <I/Q payload>
   ```
   `seq_num` gives drop detection on the (lossy) UDP stream. Keep payloads ≤ MTU or fragment deliberately.

5. **Data-rate budget (do this before real data).**
   ```
   stream_rate = num_frequencies × 2 (I/Q) × output_sample_rate × bytes_per_sample
   ```
   Confirm `stream_rate` is well under the iperf3 figure from doc 01 (Z-7020 Linux UDP is realistically a few hundred Mbps, not the full 1 Gbps). **Never stream raw ADC** (200 MSPS × 16 b = 3.2 Gbps — will not fit); stream only decimated demod output.

6. **Synthetic loopback test.** Inject a known PL-generated pattern (counter/ramp) at the sample-hold or packetizer input. Stream to PC; verify the bytes arrive **exactly** and that `seq_num` is monotonic with a known/zero drop rate at the target rate.

7. **PC receiver.** Minimal UDP sink: checks sequence continuity, logs drop rate, dumps to file for offline comparison.

## Acceptance criteria
- Synthetic pattern arrives byte-exact at the PC.
- Sustains the target stream rate; drop rate within the budgeted tolerance.
- `seq_num` monotonic; gaps detected and counted.

## Risks & gotchas
- DMA buffer **cache coherency** (stale reads).
- **S2MM pre-arming** (arm before data flows).
- Level-triggered interrupt handling (driver-side; confirm no missed/lost IRQs).
- UDP loss / undersized socket buffers — raise `rmem_max`/`SO_RCVBUF` on the PC.
- MTU / fragmentation of large frames.

## Open decisions
- DMA userspace path: `dma-proxy` vs UIO+mmap vs custom module.
- UDP vs TCP for the validation phase (UDP + seq numbers assumed; TCP if you want guaranteed delivery while debugging).
- PC OS and socket tuning.
