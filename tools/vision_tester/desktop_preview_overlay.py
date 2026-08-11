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
        self._configured_handle = 0

        # Tk creates a native wrapper window around the widget HWND.  Force the
        # native hierarchy to exist before asking Windows for the real top-level
        # handle; SetWindowDisplayAffinity only accepts a top-level HWND.
        self.window.update_idletasks()
        self._configure_windows_overlay()

    def _window_handles(self) -> tuple[int, ...]:
        if sys.platform != "win32":
            return ()

        user32 = ctypes.windll.user32
        widget_handle = int(self.window.winfo_id())
        handles: list[int] = []

        # GA_ROOT resolves the actual native top-level window, even when Tk has
        # inserted one or more wrapper HWNDs.  This is more reliable than a
        # single GetParent() call.
        try:
            root_handle = int(user32.GetAncestor(widget_handle, 2))  # GA_ROOT
        except Exception:
            root_handle = 0
        try:
            parent_handle = int(user32.GetParent(widget_handle))
        except Exception:
            parent_handle = 0

        for handle in (root_handle, parent_handle, widget_handle):
            if handle and handle not in handles:
                handles.append(handle)
        return tuple(handles)

    def _configure_handle(self, handle: int) -> bool:
        user32 = ctypes.windll.user32
        try:
            extended_style = int(user32.GetWindowLongW(handle, -20))
            user32.SetWindowLongW(
                handle,
                -20,
                extended_style
                | 0x00080000  # WS_EX_LAYERED
                | 0x00000020  # WS_EX_TRANSPARENT
                | 0x00000080  # WS_EX_TOOLWINDOW
                | 0x08000000,  # WS_EX_NOACTIVATE
            )

            # Prefer WDA_EXCLUDEFROMCAPTURE.  WDA_MONITOR is kept as a
            # compatibility fallback for older Windows builds.
            if bool(user32.SetWindowDisplayAffinity(handle, 0x00000011)):
                return True
            return bool(user32.SetWindowDisplayAffinity(handle, 0x00000001))
        except Exception:
            return False

    def _configure_windows_overlay(self) -> None:
        if sys.platform != "win32":
            return

        self.window.update_idletasks()
        self._capture_excluded = False
        for handle in self._window_handles():
            if self._configure_handle(handle):
                self._configured_handle = handle
                self._capture_excluded = True
                break

    @property
    def capture_excluded(self) -> bool:
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
        self.window.update_idletasks()

        # Deiconifying can recreate/re-parent Tk's native wrapper. Re-resolve
        # the real top-level HWND every time instead of trusting a stale one.
        self._configure_windows_overlay()
        self.window.lift()


__all__ = ["DesktopPreviewOverlay"]
