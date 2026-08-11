from __future__ import annotations

import ctypes
import sys
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk


class DesktopPreviewOverlay:
    """Click-through RGB overlay rendered directly over the selected game area."""

    def __init__(self, master: tk.Misc) -> None:
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="black")

        self.label = tk.Label(
            self.window,
            background="black",
            borderwidth=0,
            highlightthickness=0,
        )
        self.label.pack(fill="both", expand=True)
        self._photo: ImageTk.PhotoImage | None = None
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
            if user32.SetWindowDisplayAffinity(handle, 0x00000011):
                self._capture_excluded = True
            else:
                self._capture_excluded = bool(
                    user32.SetWindowDisplayAffinity(handle, 0x00000001)
                )
        except Exception:
            self._capture_excluded = False

    def _prime_capture_exclusion(self) -> None:
        """Map the native window once before checking display affinity.

        Windows can reject SetWindowDisplayAffinity while a Tk Toplevel is still
        withdrawn. The previous implementation checked too early and disabled the
        feature before the overlay ever became visible.
        """
        if sys.platform != "win32" or self._capture_excluded:
            return
        try:
            self.window.geometry("2x2-32000-32000")
            self.window.deiconify()
            self.window.update_idletasks()
            self._configure_windows_overlay()
        finally:
            self.window.withdraw()

    @property
    def capture_excluded(self) -> bool:
        if not self._capture_excluded:
            self._prime_capture_exclusion()
        return self._capture_excluded

    def hide(self) -> None:
        try:
            self.window.withdraw()
        except tk.TclError:
            pass

    def show_frame(
        self,
        rgb: np.ndarray,
        region: tuple[int, int, int, int],
    ) -> None:
        if rgb is None or rgb.ndim != 3 or rgb.shape[2] != 3:
            self.hide()
            return

        left, top, width, height = map(int, region)
        if width <= 1 or height <= 1:
            self.hide()
            return

        if rgb.shape[1] != width or rgb.shape[0] != height:
            image = Image.fromarray(rgb).resize((width, height), Image.Resampling.NEAREST)
        else:
            image = Image.fromarray(rgb)

        self._photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self._photo)
        self.window.geometry(f"{width}x{height}{left:+d}{top:+d}")
        self.window.deiconify()
        self.window.lift()
        self._configure_windows_overlay()


__all__ = ["DesktopPreviewOverlay"]
