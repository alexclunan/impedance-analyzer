# Build and Deploy

End-to-end build of all three layers, in dependency order. Details for each layer
are in `fpga-developer-guide.md` and `firmware-guide.md`.

## Layers and when to rebuild

| Change | Rebuild | Effort |
|---|---|---|
| PC / GUI (Python) | nothing — just relaunch `python -m iza_gui` | seconds |
| Firmware (`iza_replay.c`) | `iza-stream` app, `scp` the ELF | ~1 min |
| Device tree / kernel module | `petalinux-build` + repackage image | minutes |
| FPGA RTL / block design | bitstream → `.xsa` → BOOT.BIN | ~30 min |

Do the least you can: most day-to-day work is PC-only or a firmware ELF swap.

## 1. FPGA (only when RTL/BD changes)

In Vivado (`impedance_analyzer_vivado/`):
1. Edit RTL in `FPGA/Custom Hardware Source Files/` and **sync the Vivado import
   copies** (synthesis compiles `…srcs/…/imports/…`, not your edited files).
2. Generate output products → generate bitstream.
3. **File → Export → Export Hardware** with *Include bitstream* → `.xsa`.
4. Hand the `.xsa` to the PetaLinux VM (shared folder).

See `fpga-developer-guide.md` for the import-copy trap and the stale-bitstream
trap.

## 2. PetaLinux (in the VM)

Point the project at the new `.xsa` if the hardware changed
(`petalinux-config --get-hw-description`), then:

**Fast — firmware only (no hardware change):**
```bash
petalinux-build -c iza-stream -x do_compile
scp -o StrictHostKeyChecking=no <build>/.../iza_replay root@192.168.0.80:/usr/bin/
```

**Full image / new bitstream:**
```bash
petalinux-build
petalinux-package --boot --fsbl --fpga --u-boot --force
# copy BOOT.BIN + image.ub to the SD card and boot
```

Verify on boot: `dmesg | grep -i dma`, `ls /dev/dma_proxy_*`.

## 3. PC software

No build step. From `petalinux_overlay/pc/`:
```bash
python -m iza_gui          # GUI
python iza_ctrl.py ...     # CLI control
```
Dependencies: `numpy` (all), `PySide6` + `pyqtgraph` (GUI/live plot),
`matplotlib` (offline plots), `scipy` (optional, `iza_sender --hq`).

## 4. Documentation (this `docs/` tree)

The Markdown guides render on GitHub as-is (mermaid included). The Technical
Reference Manual is LaTeX:

```bash
cd docs/reference-manual
latexmk -pdf trm.tex        # or: pdflatex trm && bibtex trm && pdflatex trm && pdflatex trm
```

Needs a LaTeX distribution (MiKTeX or TeX Live) with `latexmk`. If you don't have
one, a CI job can build `trm.pdf` on push (GitHub Actions `xu-cheng/latex-action`).

## Smoke test after deploy

```bash
cd petalinux_overlay/pc
python iza_ctrl.py --board 192.168.0.80 run
python iza_ctrl.py --board 192.168.0.80 regread 0        # expect 0x3F
python iza_ctrl.py --board 192.168.0.80 dac-init && python iza_ctrl.py --board 192.168.0.80 adc-init
python iza_ctrl.py --board 192.168.0.80 channels 0x1
python iza_receiver.py --port 7100 --seconds 5 --out smoke.bin
python iza_validate.py smoke.bin
```
