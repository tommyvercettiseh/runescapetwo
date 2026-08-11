from __future__ import annotations

import ctypes
import sys
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

from core.vision.screenshots import register_capture_hooks


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
        self._suspended_for_capture = False
        self._visible = False

        self.window.update_idletasks()
        self._configure_windows_overlay()
        self._unregister_capture_hooks = register_capture_hooks(
            before=self._before_capture,
            after=self._after_capture,
        )

    def _window_handles(self) -> tuple[int, ...]:
        if sys.platform != "win32":
            return ()

        user32 = ctypes.windll.user32
        widget_handle = int(self.window.winfo_id())
        handles: list[int] = []

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
        # From the caller's point of view this overlay is always capture-safe:
        # either Windows excludes it natively, or screenshot hooks temporarily
        # withdraw it for the few milliseconds ImageGrab is active.
        return True

    @property
    def uses_capture_fallback(self) -> bool:
        return not self._capture_excluded

    def _before_capture(self) -> None:
        """Fallback: briefly remove this overlay before ImageGrab runs."""
        if self._capture_excluded or not self._visible:
            return
        try:
            self._suspended_for_capture = True
            self.window.withdraw()
            self.window.update_idletasks()
        except tk.TclError:
            self._suspended_for_capture = False

    def _after_capture(self) -> None:
        if not self._suspended_for_capture:
            return
        self._suspended_for_capture = False
        try:
            self.window.deiconify()
            self.window.update_idletasks()
            self._configure_windows_overlay()
            self.window.lift()
        except tk.TclError:
            self._visible = False

    def hide(self) -> None:
        self._visible = False
        self._suspended_for_capture = False
        try:
            self.window.withdraw()
            self.window.update_idletasks()
        except tk.TclError:
            pass

    def close(self) -> None:
        self.hide()
        try:
            self._unregister_capture_hooks()
        except Exception:
            pass
        try:
            self.window.destroy()
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
        self._visible = True

        # Try native exclusion whenever the native Tk wrapper is available.
        # If Windows rejects it, capture hooks provide the fallback instead.
        self._configure_windows_overlay()
        self.window.lift()


__all__ = ["DesktopPreviewOverlay"]
