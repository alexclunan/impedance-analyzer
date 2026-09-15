# Doc 02 — PL→PS→Ethernet Data Path: Build & Bring-Up Guide

Implements `verification_plans/02_datapath_dma_ethernet.md` for the
**capstone_demo** bitstream (MM2S → AXIS FIFO → sample_hold → AM modulator →
demod → output_packetizer → S2MM).

## What's in this tree

```
meta-user/
  recipes-modules/dma-proxy/      kernel module: /dev/dma_proxy_{tx,rx}
  recipes-apps/iza-stream/        Zynq userspace streamer (DMA -> UDP)
  recipes-bsp/device-tree/files/system-user.dtsi   dma_proxy DT node
pc/
  iza_receiver.py                 PC UDP sink: seq/drop/timestamp checks
  iza_validate.py                 offline waveform validation (numpy)
```

## Design decisions (locked)

| Decision | Choice |
|---|---|
| Userspace DMA path | dma-proxy module (coherent buffers — **no manual cache management ever**) |
| Pattern injection | MM2S replay loopback (no bitstream change). Payload verified as recovered waveform; *byte-exactness* of the DMA+network path proven structurally via the 16-B record framing + uniform timestamps |
| Transport | UDP + 32-bit seq numbers, datagrams 1440 B (no IP fragmentation at MTU 1500) |
| Rate budget | 14 kSPS × 16 B = **1.8 Mbps** — orders of magnitude under the doc-01 iperf3 figure. Even sample_hold's max 625 kSPS config is only 80 Mbps |

Hardware facts baked in (from `C:\impedance_fw\impedance_fw\src\config.h` and
the SDT `pl.dtsi`):

- AXI DMA @ `0x40400000`, MM2S 16-bit / S2MM 32-bit, IRQs GIC 62/63 (level)
- Register file @ `0x43C00000`: REG0/1 = 48-bit FCW, REG2 = reset-release
  (`0x0FE7` = run), REG3 bit0 = packetizer enable
- `sample_hold` replay rate in current bitfile: **14 kHz**
- One S2MM frame (TLAST) = 1024 records × 16 B = 16 KiB = one DMA buffer

## VM-side steps (PetaLinux project from doc 01)

From the project root (created in doc 01, `petalinux-config` already pointed
at the capstone_demo XSA):

### 1. Add the kernel module

```bash
petalinux-create -t modules --name dma-proxy --enable
```

`petalinux-create` generates a skeleton including a `files/COPYING` with the
correct GPLv2 checksum. **Keep that file** — only replace the source files and
the `.bb`:

```bash
# Replace only source files (leave COPYING from the generated skeleton)
cp <overlay>/meta-user/recipes-modules/dma-proxy/files/dma-proxy.c \
   project-spec/meta-user/recipes-modules/dma-proxy/files/
cp <overlay>/meta-user/recipes-modules/dma-proxy/files/dma-proxy.h \
   project-spec/meta-user/recipes-modules/dma-proxy/files/
cp <overlay>/meta-user/recipes-modules/dma-proxy/files/Makefile \
   project-spec/meta-user/recipes-modules/dma-proxy/files/
cp <overlay>/meta-user/recipes-modules/dma-proxy/dma-proxy.bb \
   project-spec/meta-user/recipes-modules/dma-proxy/
```

### 2. Add the streamer app

```bash
petalinux-create -t apps --template c --name iza-stream --enable
cp <overlay>/meta-user/recipes-apps/iza-stream/files/* \
   project-spec/meta-user/recipes-apps/iza-stream/files/
cp <overlay>/meta-user/recipes-apps/iza-stream/iza-stream.bb \
   project-spec/meta-user/recipes-apps/iza-stream/
```

### 3. Device tree

Merge the `dma_proxy` node from
`meta-user/recipes-bsp/device-tree/files/system-user.dtsi` into
`project-spec/meta-user/recipes-bsp/device-tree/files/system-user.dtsi`
(append the node inside `/ { … }`; keep whatever PHY fixups doc 01 added).

### 4. Kernel config check

The Xilinx DMA engine driver is normally built in; verify once:

```bash
petalinux-config -c kernel
# Device Drivers -> DMA Engine support -> Xilinx AXI DMAS Engine  = y
```

### 5. Build & boot

```bash
petalinux-build
petalinux-package --boot --fsbl --fpga --u-boot --force
# copy BOOT.BIN + image.ub to SD, boot
```

## Boot-time verification (before streaming)

```bash
dmesg | grep -i 'xilinx.*dma'     # xilinx_dma probe, 2 channels
dmesg | grep dma_proxy            # "dma_proxy_tx: 16 x 16384 bytes coherent ..."
ls /dev/dma_proxy_*               # both nodes present
cat /proc/interrupts | grep -E '6[23]'   # GIC 62/63 registered (level)
```

If `dma_proxy` probes before `xilinx_dma`, it defers automatically
(`-EPROBE_DEFER`) — no action needed.

## Run the loopback test

PC side (this Windows machine), first:

```powershell
python pc\iza_receiver.py --port 7100 --out capture.bin --sample-rate 14000
```

Zynq side:

```bash
iza-stream --pc <PC_IP> --port 7100 --pattern sine --msg-freq 100 \
           --carrier 1000 --sample-rate 14000 --seconds 60
```

Ordering inside the app (do not reorder if modifying):
1. PL resets released, **packetizer still disabled**
2. all 16 S2MM buffers pre-armed   ← the pre-arming gotcha
3. MM2S feeder running, FIFO given 50 ms to fill
4. packetizer enabled (REG3 bit0) — data starts flowing

Then offline:

```powershell
python pc\iza_validate.py capture.bin --msg-freq 100 --sample-rate 14000 --plot
```

## Acceptance mapping (plan 02)

| Criterion | How it's checked |
|---|---|
| Pattern arrives byte-exact | Structural: header/len exact, 16-B framing intact, timestamp deltas uniform (±1 clock from 7142.86); waveform: recovered tone at `--msg-freq` (loopback passes through the demod pipeline, so values are DSP outputs by design) |
| Sustains target rate | receiver throughput print vs 1.8 Mbps budget |
| seq monotonic, gaps counted | receiver `gaps`/`dropped`/`reordered` counters + PASS/FAIL exit code |

## Gotchas addressed

- **Cache coherency**: buffers come from `dma_alloc_coherent` and are mmap'd
  non-cached — stale-read corruption is impossible by construction.
- **S2MM pre-arm**: enforced by app ordering (above).
- **Level-triggered IRQs**: handled inside the in-kernel `xilinx_dma` driver;
  confirm no `Spurious` / `nobody cared` lines in `dmesg` during a run.
- **UDP loss on the PC**: receiver requests 8 MiB `SO_RCVBUF` and prints the
  effective value. On Linux PCs also raise `sysctl net.core.rmem_max`.
  Windows honours the setsockopt directly.
- **MTU**: datagrams are 1440 B total payload — no fragmentation at MTU 1500.

## Known deltas vs the verification plan

- The plan's "three interrupts" includes the FIFO refill IRQ (GIC 61). Under
  Linux it is unused: MM2S pacing comes from FIFO backpressure (the TX
  `FINISH` ioctl blocks while the FIFO is full), so no refill handler is
  needed. The `request_refill` GPIO @ `0x41200000` remains readable for debug.
- `freq_channel_id` is always 0 (single-frequency capstone_demo pipeline);
  the header field exists for doc-03+ multi-frequency use.
