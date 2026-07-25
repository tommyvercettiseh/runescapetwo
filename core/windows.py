from __future__ import annotations

import sys

_dpi_awareness_enabled = False


def enable_dpi_awareness() -> None:
    """Use physical screen pixels on Windows."""
    global _dpi_awareness_enabled
    if _dpi_awareness_enabled or sys.platform != "win32":
        return

    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()
    _dpi_awareness_enabled = True
