# Impedance Analyzer — Documentation

FPGA-based multi-frequency impedance analyzer: a digital lock-in amplifier (DLIA)
and low-latency cell-sorting trigger, on a Xilinx Zynq-7020 (Trenz TE0720 SoM)
with an AD9122 DAC and AD9467 ADC on a custom carrier board, streamed to and
controlled from a PC over UDP.

This `docs/` tree is the maintained documentation set. It has two halves:

- **Technical Reference Manual** (`reference-manual/`, LaTeX → `trm.pdf`) — the
  typeset, archival reference: architecture, signal-chain theory, the wire
  protocol, the register maps, and the hardware. Build it with
  `latexmk -pdf trm.tex` (or `pdflatex trm` ×2).
- **Guides** (`guides/`, Markdown) — the living, task-oriented docs that sit next
  to the code: build/deploy, the GUI and CLI, firmware and FPGA developer notes.

> **Source of truth.** Everything here is transcribed from current source, not
> from the historical planning notes. Those notes are preserved verbatim under
> [`archive/`](archive/) with a manifest — treat them as history, **not** as an
> accurate description of the present system.

## Who should read what

| You are… | Start here |
|---|---|
| Inheriting the project | TRM ch. 1 (Architecture) → `guides/build-and-deploy.md` → `guides/fpga-developer-guide.md` + `guides/firmware-guide.md` |
| Running experiments | `guides/operator-quickstart.md` → `guides/gui-user-guide.md` → `guides/triggering-guide.md` |
| Modifying the code | TRM ch. 3–4 (Protocol, Registers) → `guides/firmware-guide.md` / `guides/fpga-developer-guide.md` / `guides/cli-reference.md` |

## Document index

**Reference Manual (`reference-manual/`)**
- `01-architecture.tex` — system overview, PS/PL/PC split, the shared timebase
- `02-signal-chain.tex` — analog + DSP chain, clock/reset domains, lock-in math
- `03-protocol.tex` — UDP ports, datagram/record layout, control + trigger, ziBin
- `04-register-map.tex` — FPGA AXI regs + AD9122/AD9467 SPI register maps
- `05-hardware.tex` — SoM, carrier, DAC/ADC/TIA, PCB parts and signal chains

**Guides (`guides/`)**
- `operator-quickstart.md` — power-on → init → measure → record → trigger
- `gui-user-guide.md` — the `iza_gui` PySide6 application, tab by tab
- `cli-reference.md` — every `pc/*.py` command-line tool
- `fpga-developer-guide.md` — Vivado projects, block design, module catalog, build flow, repo hygiene
- `firmware-guide.md` — PetaLinux recipes, `iza_replay.c` internals, SPI init, deploy loop
- `build-and-deploy.md` — end-to-end build+deploy for all three layers
- `triggering-guide.md` — how the trigger engine works and how to configure it

## Repository map (base = this repo root)

| Path | What |
|---|---|
| `FPGA/Custom Hardware Source Files/` | custom Verilog IP (authoritative RTL) |
| `impedance_analyzer_vivado/` | top Vivado project (`full_design.bd`) |
| `modulator_chain_vivado/` | demod sub-IP project (`modulator_chain.bd`) |
| `petalinux_overlay/meta-user/` | PetaLinux recipes: `dma-proxy` module, `iza-stream` app |
| `petalinux_overlay/pc/` | PC software: CLIs + `iza_gui/` |
| `PCB/` | schematic PDF + BOM CSV (Altium sources kept out of repo) |
| `Reference/` | AD9122/AD9467 datasheets, SoM docs, pinouts |
| `Block Diagrams/` | architecture figures |
| `docs/` | this documentation set |

> **Note on the Vivado project location.** The authoritative block design was
> historically edited in `C:\impedance_linux\impedance_analyzer`; the in-repo
> `impedance_analyzer_vivado.xpr` still references that external path for some
> sources. See `guides/fpga-developer-guide.md` → *Repository hygiene* for the
> repathing fix.

## Figures to create / refresh

Diagrams that must be supplied or refreshed by a person (the docs reference them;
they are not auto-generated). Cropping from `PCB/PCB Schematic.pdf` covers most
of the hardware ones.

- [ ] **Top-level architecture** block diagram — refresh `Block Diagrams/` (v0 is stale) → TRM ch. 1
- [ ] **DSP signal-chain** polished vector (mermaid draft is in the FPGA guide) → TRM ch. 2
- [ ] **Analog front-end / TIA** schematic excerpt (crop from PCB PDF) → TRM ch. 5
- [ ] **Carrier / trigger-output pinout** (crop from PCB PDF) → TRM ch. 5
- [ ] **Board photo** (if available) → TRM ch. 5
- [ ] **GUI screenshots**, one per tab → `guides/gui-user-guide.md`
