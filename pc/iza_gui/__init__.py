"""iza_gui — LabOne-style desktop GUI for the impedance analyzer.

Reuses the existing CLI modules as libraries:
  * iza_ctrl.IzaCtrl  — control backend (AXI regs + SPI over UDP 7202)
  * iza_packet        — self-describing packet parser (UDP 7100)

Those live in the parent directory (petalinux_overlay/pc/), so make sure it is
importable regardless of the working directory, and prefer the PySide6 Qt
binding for pyqtgraph.

Run with:  python -m iza_gui
"""

import importlib.util
import os
import sys

# Target binding is PySide6 (see requirements.txt), but the code is written
# binding-agnostic via pyqtgraph.Qt, so it also runs on an existing PyQt5.
# Only force PySide6 when it is actually installed; otherwise let pyqtgraph pick.
if importlib.util.find_spec("PySide6") is not None:
    os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

# Put the parent pc/ directory on sys.path so `import iza_ctrl` / `import
# iza_packet` resolve no matter where python was launched from.
_PC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PC_DIR not in sys.path:
    sys.path.insert(0, _PC_DIR)

__all__ = ["app", "data_stream", "control_client", "control_panel",
           "scope_panel", "numeric_panel", "register_panel", "register_map",
           "console_panel", "recorder", "theme"]
