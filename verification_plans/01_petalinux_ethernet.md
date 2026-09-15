# 01 — PetaLinux Bring-Up + Ethernet Link to PC

**Objective:** Boot PetaLinux on the TE0720, bring up GEM0 → Marvell 88E1512, and establish a verified IP link to the PC.

**Prerequisites:** XSA exported from the PS-containing block design (`full_design.bd`). Vivado/Vitis 2025.2.

**Effort:** 1–2 days.

## Steps

1. **Platform / XSA.** Export from `full_design.bd` (PS7 present). Confirm PS config before export: GEM0 enabled, RGMII on MIO 16–27, MDIO enabled, DDR, UART console, SD boot. Start from the Trenz TE0720 reference design where possible rather than a clean PS config.

2. **Create the project.**
   ```bash
   petalinux-create -t project --template zynq -n impedance_linux
   cd impedance_linux
   petalinux-config --get-hw-description=<path-to-xsa>
   ```

3. **Device tree — Ethernet.** Confirm the generated `gem0` node, its `mdio` child, and `phy@0` (MDIO address `0x00`). Set `phy-mode = "rgmii-id"` (RGMII with internal delay) to match the prior bring-up.

4. **Critical PHY config (most likely failure point).** The 88E1512 boots in **fiber/SGMII auto-detect** mode by default; a copper-only RGMII setup can fail to link. Force copper:
   - Disable fiber auto-negotiation: **Page 18, Register 20**.
   - Verify RGMII internal delay: **Page 2, Register 21**.
   Apply via a `marvell,reg-init` property on the PHY node in the device tree (or confirm the in-kernel `marvell` PHY driver brings copper up). *This default is a strong candidate for why bare-metal Ethernet didn't link — verify it explicitly here.*

5. **MAC address.** Bare-metal pulled the MAC from the on-module EEPROM (`te_fsbl_hooks_te0720.c`). Under Linux, confirm where the MAC comes from (FSBL hook / device tree `local-mac-address`) and set it deterministically so the PC ARP cache stays stable.

6. **Build + boot media.** SD boot: `BOOT.BIN` + `image.ub`, console on UART. `petalinux-build`, `petalinux-package --boot`, write SD, boot.

7. **Bring up the link.**
   ```bash
   ethtool eth0          # expect: Link detected: yes, 1000Mb/s, Full
   ip addr add 192.168.1.10/24 dev eth0   # static, same subnet as PC
   ping <pc-ip>
   iperf3 -c <pc-ip>     # confirm throughput headroom vs planned stream rate
   ```

## Acceptance criteria
- Boots to shell over UART console.
- `eth0` enumerates; PHY link up at expected speed/duplex.
- Bidirectional ping with the PC.
- `iperf3` throughput comfortably above the data rate budgeted in doc 02.

## Risks & gotchas
- **PHY fiber/SGMII default** — top suspect for no link (copper). Page 18 Reg 20.
- RGMII delay mismatch → link reports up but traffic is garbled/absent. Page 2 Reg 21 / `rgmii-id`.
- XC7Z020 has no GTX/GTP transceivers — any SGMII would need fabric I/O (XAPP523). Not relevant for RGMII-to-copper, but don't accidentally select an SGMII mode.
- VCCO / MIO bank voltage for the GEM pins.
- Non-deterministic MAC → confusing intermittent connectivity.

## Open decisions
- PetaLinux version (assume aligned with 2025.2 toolchain).
- Static vs DHCP on the link (static recommended for a point-to-point bench link).
- Boot media (SD assumed).
