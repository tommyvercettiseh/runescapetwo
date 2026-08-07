from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

import pyautogui
from PIL import Image, ImageDraw, ImageTk

from core.vision.templates import IMAGES_DIR, clear_template_cache


LOUPE_SOURCE_SIZE = 31
LOUPE_SCALE = 7
LOUPE_MARGIN = 18
LOUPE_BORDER = "#42cfe8"


def normalize_capture_name(value: str) -> str:
    name = Path(value.strip()).name
    if not name:
        raise ValueError("Geef een naam voor de template")
    return name if name.lower().endswith(".png") else f"{name}.png"


class TemplateCaptureOverlay(tk.Toplevel):
    """Fullscreen drag-to-crop tool with a pixel loupe for precise templates."""

    def __init__(self, parent: tk.Misc, on_saved: Callable[[str], None]):
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.on_saved = on_saved
        self.screen: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.loupe_photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.offset = (0, 0)
        self.start: tuple[int, int] | None = None
        self.selection: tuple[int, int, int, int] | None = None
        self.rectangle: int | None = None
        self.loupe_image_id: int | None = None
        self.loupe_box_id: int | None = None
        self.loupe_text_id: int | None = None

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
        self.canvas.bind("<Motion>", self._update_loupe)

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
            760,
            58,
            fill="#07101f",
            outline=LOUPE_BORDER,
            width=1,
        )
        self.canvas.create_text(
            30,
            36,
            anchor="w",
            text="Sleep om template te kiezen  •  Loupe volgt cursor  •  ENTER opslaan  •  ESC annuleren",
            fill="#ffffff",
            font=("Segoe UI Semibold", 12),
        )
        self.deiconify()
        self.focus_force()

    def _image_point(self, x: int, y: int) -> tuple[int, int]:
        assert self.screen is not None
        offset_x, offset_y = self.offset
        return (
            min(self.screen.width - 1, max(0, int((x - offset_x) / self.scale))),
            min(self.screen.height - 1, max(0, int((y - offset_y) / self.scale))),
        )

    def _update_loupe(self, event) -> None:
        if self.screen is None:
            return

        source_x, source_y = self._image_point(event.x, event.y)
        half = LOUPE_SOURCE_SIZE // 2
        left = max(0, source_x - half)
        top = max(0, source_y - half)
        right = min(self.screen.width, left + LOUPE_SOURCE_SIZE)
        bottom = min(self.screen.height, top + LOUPE_SOURCE_SIZE)
        left = max(0, right - LOUPE_SOURCE_SIZE)
        top = max(0, bottom - LOUPE_SOURCE_SIZE)

        crop = self.screen.crop((left, top, right, bottom))
        zoomed = crop.resize(
            (crop.width * LOUPE_SCALE, crop.height * LOUPE_SCALE),
            Image.Resampling.NEAREST,
        )

        # Crosshair marks the exact source pixel below the cursor.
        draw = ImageDraw.Draw(zoomed)
        local_x = source_x - left
        local_y = source_y - top
        x0 = local_x * LOUPE_SCALE
        y0 = local_y * LOUPE_SCALE
        x1 = x0 + LOUPE_SCALE - 1
        y1 = y0 + LOUPE_SCALE - 1
        draw.rectangle((x0, y0, x1, y1), outline=(255, 255, 255), width=1)

        self.loupe_photo = ImageTk.PhotoImage(zoomed)
        loupe_w, loupe_h = zoomed.size
        canvas_w = max(1, self.canvas.winfo_width())
        x = canvas_w - loupe_w - LOUPE_MARGIN
        y = 78

        if self.loupe_image_id is None:
            self.loupe_box_id = self.canvas.create_rectangle(
                x - 3,
                y - 3,
                x + loupe_w + 3,
                y + loupe_h + 27,
                fill="#07101f",
                outline=LOUPE_BORDER,
                width=2,
            )
            self.loupe_image_id = self.canvas.create_image(
                x,
                y,
                image=self.loupe_photo,
                anchor="nw",
            )
            self.loupe_text_id = self.canvas.create_text(
                x,
                y + loupe_h + 15,
                anchor="w",
                text="",
                fill="#ffffff",
                font=("Consolas", 10, "bold"),
            )
        else:
            self.canvas.coords(self.loupe_box_id, x - 3, y - 3, x + loupe_w + 3, y + loupe_h + 27)
            self.canvas.coords(self.loupe_image_id, x, y)
            self.canvas.itemconfigure(self.loupe_image_id, image=self.loupe_photo)
            self.canvas.coords(self.loupe_text_id, x, y + loupe_h + 15)

        selection_text = ""
        if self.start is not None:
            start_x, start_y = self._image_point(*self.start)
            selection_text = f"  •  selectie {abs(source_x - start_x)}×{abs(source_y - start_y)} px"
        self.canvas.itemconfigure(
            self.loupe_text_id,
            text=f"Pixel {source_x}, {source_y}  •  zoom {LOUPE_SCALE}×{selection_text}",
        )

        # Keep loupe above the screenshot and selection rectangle.
        for item in (self.loupe_box_id, self.loupe_image_id, self.loupe_text_id):
            if item is not None:
                self.canvas.tag_raise(item)

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
            outline=LOUPE_BORDER,
            width=3,
        )

    def _drag_selection(self, event) -> None:
        if self.start is None or self.rectangle is None:
            return
        self.canvas.coords(self.rectangle, *self.start, event.x, event.y)
        self._update_loupe(event)

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
        self._update_loupe(event)

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
