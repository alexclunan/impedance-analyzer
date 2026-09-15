# Archive Manifest

Each archived copy under `legacy-plans/` and where it came from (path relative to
the repo root, unless marked EXTERNAL). Status reflects how much of the document
still matches the current system.

| Archived file (`legacy-plans/…`) | Original location | Status |
|---|---|---|
| `verification_plans__00_README_master_plan.md` | `verification_plans/00_README_master_plan.md` | Historical — master plan index |
| `verification_plans__01_petalinux_ethernet.md` | `verification_plans/01_petalinux_ethernet.md` | Superseded by `guides/firmware-guide.md`, `guides/build-and-deploy.md` |
| `verification_plans__02_datapath_dma_ethernet.md` | `verification_plans/02_datapath_dma_ethernet.md` | Superseded by TRM ch. 3 (Protocol) + `guides/firmware-guide.md` |
| `verification_plans__03_pipeline_validation.md` | `verification_plans/03_pipeline_validation.md` | Partly current — replay/validation flow (`iza_sender`/`iza_validate`) |
| `verification_plans__04_reconfigurable_fir_coefficients.md` | `verification_plans/04_reconfigurable_fir_coefficients.md` | Historical — FIR reconfig experiment |
| `verification_plans__05_triggering_TODO.md` | `verification_plans/05_triggering_TODO.md` | Superseded by `guides/triggering-guide.md` + TRM ch. 3 (triggering is implemented) |
| `verification_plans__06_pcb_power_bringup.md` | `verification_plans/06_pcb_power_bringup.md` | Reference — PCB power bring-up |
| `verification_plans__07_pcb_config_clocking_selectio.md` | `verification_plans/07_pcb_config_clocking_selectio.md` | Reference — config/clocking/SelectIO |
| `verification_plans__08_pcb_analog_validation.md` | `verification_plans/08_pcb_analog_validation.md` | Reference — analog validation |
| `Reference__WEBSITES.md` | `Reference/WEBSITES.md` | Reference — external links |
| `memory__MEMORY.md` | `memory/MEMORY.md` | AI working notes — index |
| `memory__full-design-bd-known-nonissues.md` | `memory/full-design-bd-known-nonissues.md` | AI working notes — BD known non-issues |
| `petalinux_overlay__README_BRINGUP.md` | `petalinux_overlay/README_BRINGUP.md` | Superseded by `guides/firmware-guide.md` (doc-02 bring-up) |
| `EXTERNAL__PLAN-05-multifreq-refactor.md` | **EXTERNAL:** `C:\impedance_linux\PLAN-05-multifreq-refactor.md` | Historical — multi-frequency refactor plan (outside the repo tree) |

**Not archived** (kept live, not planning docs): `README.md` (repo root — overhauled separately),
the `docs/` set itself, and source code. `Testing/ERROR_MODELS.md` was listed in the plan but not
found at copy time — verify its path if you want it archived too.
