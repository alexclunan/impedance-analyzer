# Summer Research — System Bring-Up Implementation Plan

Master index for getting the impedance analyzer + triggering system ready for experiments.
Restructured from capstone to summer research; PetaLinux now handles Ethernet and host I/O.

## Two parallel tracks

The FPGA/PetaLinux track and the custom-PCB track are largely independent until the
end-to-end analog test. Run them in parallel where bench/attention allows.

### Track A — FPGA / PetaLinux
| Doc | Theme | Effort |
|-----|-------|--------|
| 01 | PetaLinux bring-up + Ethernet link to PC | 1–2 d |
| 02 | PL→PS→Ethernet data path (DMA → packets → PC, synthetic loopback) | 1–2 d |
| 03 | Demod pipeline validation with real lab data + PC plotting | 1–2 d |
| 04 | Runtime-reconfigurable FIR coefficients (FIR Compiler reload) | 1–2 d |
| 05 | Triggering RTL block | **Deferred** (stub) |

### Track B — Custom PCB
| Doc | Theme | Effort |
|-----|-------|--------|
| 06 | Power bring-up + mezzanine integration | 1 d |
| 07 | Device config (ADC/DAC/PGA SPI) + clocking + SelectIO/XDC | 1–2 d |
| 08 | Analog signal-chain validation (DAC→load→ADC, real samples) | 1–2 d |

## Dependency graph

```
A:  01 ──> 02 ──> 03 ──┐
                  └─> 04 (needs PS access path from 01/02)
         05 (deferred)

B:  06 ──> 07 ──> 08
                       │
Convergence:  03 (readout) + 07 (PCB configured) ──> 08 (DAC→load→ADC)
              03 + 04 + 08  ──>  end-to-end real-sample measurement
```

## Suggested serial order (if not parallelizing)
`01 → 06 → 02 → 07 → 03 → 08 → 04`, triggering (05) last.
Rationale: get a network link and a powered, non-bricked PCB early; the analog test (08)
is the convergence point and needs both a configured PCB (07) and a working readout pipeline (03).

## Conventions
- Repo: `C:/Users/Alex/Documents/GitHub/impedance-analyzer/`. One branch per doc.
- **Commit the PetaLinux config and device tree** (and any `marvell,reg-init` PHY fixups) — these are the easiest things to lose and the hardest to reconstruct.
- Prefer Trenz reference designs as the base for the platform/XSA over building from scratch.
- Each doc has: Objective · Prerequisites · Steps · Acceptance criteria · Risks/gotchas · Open decisions.
