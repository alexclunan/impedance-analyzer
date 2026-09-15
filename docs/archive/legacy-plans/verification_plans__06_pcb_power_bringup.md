# 06 — Custom PCB Power Bring-Up + Mezzanine Integration

**Objective:** Bring up the custom mezzanine on the TE0701-06 without damaging it. General guardrails only — you'll verify exact rail values and tolerances yourself; the focus here is the things that *brick the board*.

**Prerequisites:** PCB in hand. TE0701-06 carrier.

**Effort:** ~1 day.

## Steps

1. **Board isolated — short check.** With the PCB disconnected, DMM-check each power rail to GND and rail-to-rail for shorts. Inspect connector and regulator pins for solder bridges.

2. **Carrier side, PCB disconnected.** Measure the TE0701-06 mezzanine connector rails. Confirm each rail you expect is present, at the right pin, at the right voltage. **Don't assume the carrier supplies a rail just because the PCB needs it** — verify the carrier actually provides what the mezzanine draws from it.

3. **Sequencing.** If the ADC/DAC/PGA have supply-sequencing requirements, confirm the rail-up order won't violate them. Bring up under current limit so a sequencing fault trips the supply, not the silicon.

4. **First power-on (mated).** Use a current-limited bench supply (or the carrier with current monitoring). Watch inrush/steady current — if it spikes past expectation, cut power immediately and recheck for shorts.

5. **Post power-on rail check.** Verify each rail at its load reaches the expected value within tolerance, stays stable under load, and regulators aren't overheating.

6. **I/O voltage gate (bridge to doc 07).** Before the FPGA drives *any* PCB I/O, confirm each FPGA bank VCCO matches the PCB I/O rail. A VCCO/I-O voltage mismatch can damage device pins.

## Major things that break the PCB — explicit call-outs
- Reverse-polarity or mis-pinned rail into the connector.
- Rail-to-GND or rail-to-rail short energized at full current (no current limit).
- FPGA bank VCCO ≠ PCB I/O rail when driving pins.
- Violated supply sequencing on ADC/DAC/PGA.
- Hot-plugging the mezzanine (mate/unmate powered).

## Acceptance criteria
- No shorts found pre-power.
- All rails within tolerance at their loads, stable, thermally OK.
- VCCO/I-O voltages confirmed compatible — safe to proceed to config.

## Open decisions
- Exact rail values/tolerances (you verify).
- Current-limit setpoints.
- Per-device sequencing specifics (from datasheets).
