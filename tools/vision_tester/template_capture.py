from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

import pyautogui
from PIL import Image, ImageTk

from core.vision.templates import IMAGES_DIR, clear_template_cache


def normalize_capture_name(value: str) -> str:
    name = Path(value.strip()).name
    if not name:
        raise ValueError("Geef een naam voor de template")
    return name if name.lower().endswith(".png") else f"{name}.png"


class TemplateCaptureOverlay(tk.Toplevel):
    """Fullscreen drag-to-crop tool for creating a template PNG."""

    def __init__(self, parent: tk.Misc, on_saved: Callable[[str], None]):
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.on_saved = on_saved
        self.screen: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.offset = (0, 0)
        self.start: tuple[int, int] | None = None
        self.selection: tuple[int, int, int, int] | None = None
        self.rectangle: int | None = None

        self.withdraw()
        self.parent_window.withdraw()
        self.parent_window.update_idletasks()
        self.after(180, self._open)

    def _open(self) -> None:
        try:
            self.screen = pyautogui.screenshot().convert("RGB")
        except Exception as exc:
            self.parent_window.deiconify()
            self.destroy()
            messagebox.showerror("Template capture", str(exc), parent=self.parent_window)
            return
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(background="#07101f")

        self.canvas = tk.Canvas(self, background="#07101f", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda _event: self._close())
        self.bind("<Return>", lambda _event: self._save())
        self.canvas.bind("<Button-1>", self._start_selection)
        self.canvas.bind("<B1-Motion>", self._drag_selection)
        self.canvas.bind("<ButtonRelease-1>", self._finish_selection)

        self.update_idletasks()
        screen_width = max(1, self.winfo_screenwidth())
        screen_height = max(1, self.winfo_screenheight())
        self.scale = min(
            screen_width / self.screen.width,
            screen_height / self.screen.height,
        )
        display_size = (
            max(1, int(self.screen.width * self.scale)),
            max(1, int(self.screen.height * self.scale)),
        )
        display = self.screen.resize(display_size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(display)
        self.offset = (
            (screen_width - display_size[0]) // 2,
            (screen_height - display_size[1]) // 2,
        )
        self.canvas.create_image(*self.offset, image=self.photo, anchor="nw")
        self.canvas.create_rectangle(
            14,
            14,
            650,
            58,
            fill="#07101f",
            outline="#42cfe8",
            width=1,
        )
        self.canvas.create_text(
            30,
            36,
            anchor="w",
            text="Sleep om template te kiezen  •  ENTER opslaan  •  ESC annuleren",
            fill="#ffffff",
            font=("Segoe UI Semibold", 12),
        )
        self.deiconify()
        self.focus_force()

    def _image_point(self, x: int, y: int) -> tuple[int, int]:
        assert self.screen is not None
        offset_x, offset_y = self.offset
        return (
            min(self.screen.width, max(0, int((x - offset_x) / self.scale))),
            min(self.screen.height, max(0, int((y - offset_y) / self.scale))),
        )

    def _start_selection(self, event) -> None:
        self.start = (event.x, event.y)
        self.selection = None
        if self.rectangle is not None:
            self.canvas.delete(self.rectangle)
        self.rectangle = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#42cfe8",
            width=3,
        )

    def _drag_selection(self, event) -> None:
        if self.start is None or self.rectangle is None:
            return
        self.canvas.coords(self.rectangle, *self.start, event.x, event.y)

    def _finish_selection(self, event) -> None:
        if self.start is None:
            return
        x1, y1 = self._image_point(*self.start)
        x2, y2 = self._image_point(event.x, event.y)
        self.selection = (
            min(x1, x2),
            min(y1, y2),
            max(x1, x2),
            max(y1, y2),
        )

    def _save(self) -> None:
        if self.screen is None or self.selection is None:
            messagebox.showinfo("Template", "Sleep eerst een rechthoek om de template.", parent=self)
            return
        x1, y1, x2, y2 = self.selection
        if x2 - x1 < 3 or y2 - y1 < 3:
            messagebox.showerror("Template", "De selectie is te klein.", parent=self)
            return
        value = simpledialog.askstring(
            "Template opslaan",
            "Naam voor de nieuwe template:",
            parent=self,
        )
        if not value:
            return
        try:
            name = normalize_capture_name(value)
        except ValueError as exc:
            messagebox.showerror("Template", str(exc), parent=self)
            return

        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        target = IMAGES_DIR / name
        if target.exists() and not messagebox.askyesno(
            "Template vervangen",
            f"{name} bestaat al. Vervangen?",
            parent=self,
        ):
            return
        self.screen.crop((x1, y1, x2, y2)).save(target)
        clear_template_cache()
        self._close()
        self.on_saved(name)

    def _close(self) -> None:
        self.destroy()
        self.parent_window.deiconify()
        self.parent_window.lift()
