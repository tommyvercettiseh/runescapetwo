from __future__ import annotations

import ctypes
import sys
import tkinter as tk

from .enhanced_config import (
    AREA_BORDER_HEX,
    PIPETTE_EDGE_PADDING,
    SAFE_BORDER_HEX,
    TRANSPARENT_KEY,
)


class ScreenAreaOverlay:
    """Click-through desktop area guide excluded from capture when supported."""

    def __init__(self, master: tk.Misc) -> None:
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_KEY)
        self.window.attributes("-topmost", True)
        if sys.platform == "win32":
            self.window.attributes("-transparentcolor", TRANSPARENT_KEY)

        self.canvas = tk.Canvas(
            self.window,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._capture_excluded = False
        self._configure_windows_overlay()

    def _window_handle(self) -> int:
        user32 = ctypes.windll.user32
        handle = int(self.window.winfo_id())
        parent = int(user32.GetParent(handle))
        return parent or handle

    def _configure_windows_overlay(self) -> None:
        if sys.platform != "win32":
            return

        self.window.update_idletasks()
        user32 = ctypes.windll.user32
        handle = self._window_handle()
        extended_style = int(user32.GetWindowLongW(handle, -20))
        user32.SetWindowLongW(
            handle,
            -20,
            extended_style | 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000,
        )
        try:
            self._capture_excluded = bool(
                user32.SetWindowDisplayAffinity(handle, 0x00000011)
            )
        except Exception:
            self._capture_excluded = False

    @property
    def capture_excluded(self) -> bool:
        return self._capture_excluded

    def hide(self) -> None:
        try:
            self.window.withdraw()
        except tk.TclError:
            pass

    def show_region(self, region: tuple[int, int, int, int]) -> None:
        left, top, width, height = map(int, region)
        if width <= 1 or height <= 1:
            self.hide()
            return

        self.window.geometry(f"{width}x{height}{left:+d}{top:+d}")
        self.canvas.configure(width=width, height=height)
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            1,
            1,
            width - 2,
            height - 2,
            outline=AREA_BORDER_HEX,
            width=2,
        )

        pad = PIPETTE_EDGE_PADDING
        if width > pad * 2 + 2 and height > pad * 2 + 2:
            self.canvas.create_rectangle(
                pad,
                pad,
                width - pad - 1,
                height - pad - 1,
                outline=SAFE_BORDER_HEX,
                width=1,
            )
        self.window.deiconify()
        self.window.lift()


__all__ = ["ScreenAreaOverlay"]
