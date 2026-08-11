from __future__ import annotations

import ctypes
import sys
import tkinter as tk

from PIL import Image, ImageTk

from core.vision.screenshots import register_capture_hooks
from .preview_contract import PreviewSnapshot


TRANSPARENT_KEY = "#010203"


class DesktopPreviewOverlay:
    """Click-through desktop preview rendered over the selected game area.

    Full processed frames are used for colour/sensor modes. Annotation-only
    snapshots use a transparent chroma-key canvas, so template boxes are drawn
    physically over the real RuneLite pixels instead of over a copied preview.

    Native Windows capture exclusion is preferred. If Windows rejects that
    flag, the explicit screenshot hook API briefly withdraws this overlay while
    ImageGrab runs. No page methods are replaced or monkey-patched.
    """

    def __init__(self, master: tk.Misc) -> None:
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=TRANSPARENT_KEY)
        if sys.platform == "win32":
            self.window.attributes("-transparentcolor", TRANSPARENT_KEY)

        self.canvas = tk.Canvas(
            self.window,
            background=TRANSPARENT_KEY,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._photo: ImageTk.PhotoImage | None = None
        self._native_capture_exclusion = False
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
        self._native_capture_exclusion = False
        for handle in self._window_handles():
            if self._configure_handle(handle):
                self._native_capture_exclusion = True
                break

    @property
    def uses_capture_fallback(self) -> bool:
        return not self._native_capture_exclusion

    def _before_capture(self) -> None:
        if self._native_capture_exclusion or not self._visible:
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
        self._unregister_capture_hooks()
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def show_snapshot(self, snapshot: PreviewSnapshot) -> None:
        left, top, width, height = map(int, snapshot.region)
        if width <= 1 or height <= 1:
            self.hide()
            return

        self.canvas.delete("all")
        self._photo = None

        if snapshot.frame is not None:
            rgb = snapshot.frame
            if rgb.ndim != 3 or rgb.shape[2] != 3:
                self.hide()
                return
            if rgb.shape[1] != width or rgb.shape[0] != height:
                image = Image.fromarray(rgb).resize((width, height), Image.Resampling.NEAREST)
            else:
                image = Image.fromarray(rgb)
            self._photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

        for box in snapshot.boxes:
            x1, y1, x2, y2 = map(int, box.bounds)
            x1 = max(0, min(width - 1, x1))
            y1 = max(0, min(height - 1, y1))
            x2 = max(0, min(width - 1, x2))
            y2 = max(0, min(height - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue
            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=box.colour,
                width=max(1, int(box.width)),
            )
            if box.label:
                text_y = y1 - 6 if y1 >= 18 else y1 + 14
                self.canvas.create_text(
                    x1 + 4,
                    text_y,
                    text=box.label,
                    fill=box.colour,
                    anchor="w",
                    font=("Segoe UI", 9, "bold"),
                )

        self.window.geometry(f"{width}x{height}{left:+d}{top:+d}")
        self.canvas.configure(width=width, height=height)
        self.window.deiconify()
        self.window.update_idletasks()
        self._visible = True

        self._configure_windows_overlay()
        self.window.lift()


__all__ = ["DesktopPreviewOverlay"]
