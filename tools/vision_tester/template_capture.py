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
START_GUIDE = "#ffb6c8"
SELECTION_PREVIEW_MAX = (320, 210)


def normalize_capture_name(value: str) -> str:
    name = Path(value.strip()).name
    if not name:
        raise ValueError("Geef een naam voor de template")
    return name if name.lower().endswith(".png") else f"{name}.png"


class TemplateCaptureOverlay(tk.Toplevel):
    """Fullscreen drag-to-crop tool with loupe and full selection preview."""

    def __init__(self, parent: tk.Misc, on_saved: Callable[[str], None]):
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.on_saved = on_saved
        self.screen: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.loupe_photo: ImageTk.PhotoImage | None = None
        self.selection_photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.offset = (0, 0)
        self.start: tuple[int, int] | None = None
        self.selection: tuple[int, int, int, int] | None = None
        self.rectangle: int | None = None
        self.start_vertical: int | None = None
        self.start_horizontal: int | None = None
        self.loupe_image_id: int | None = None
        self.loupe_box_id: int | None = None
        self.loupe_text_id: int | None = None
        self.selection_image_id: int | None = None
        self.selection_box_id: int | None = None
        self.selection_text_id: int | None = None

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
        self.bind("<F2>", lambda _event: self._save())
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
            870,
            58,
            fill="#07101f",
            outline=LOUPE_BORDER,
            width=1,
        )
        self.canvas.create_text(
            30,
            36,
            anchor="w",
            text="Sleep om template te kiezen  •  Loupe + volledige selectie rechts  •  ENTER/F2 opslaan  •  ESC annuleren",
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

    def _selection_from_cursor(self, event) -> tuple[int, int, int, int] | None:
        if self.start is None:
            return self.selection
        x1, y1 = self._image_point(*self.start)
        x2, y2 = self._image_point(event.x, event.y)
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        if right <= left or bottom <= top:
            return None
        return left, top, right, bottom

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
                x - 3, y - 3, x + loupe_w + 3, y + loupe_h + 27,
                fill="#07101f", outline=LOUPE_BORDER, width=2,
            )
            self.loupe_image_id = self.canvas.create_image(x, y, image=self.loupe_photo, anchor="nw")
            self.loupe_text_id = self.canvas.create_text(
                x, y + loupe_h + 15, anchor="w", text="", fill="#ffffff",
                font=("Consolas", 10, "bold"),
            )
        else:
            self.canvas.coords(self.loupe_box_id, x - 3, y - 3, x + loupe_w + 3, y + loupe_h + 27)
            self.canvas.coords(self.loupe_image_id, x, y)
            self.canvas.itemconfigure(self.loupe_image_id, image=self.loupe_photo)
            self.canvas.coords(self.loupe_text_id, x, y + loupe_h + 15)

        selection_now = self._selection_from_cursor(event)
        selection_text = ""
        if selection_now is not None:
            sx1, sy1, sx2, sy2 = selection_now
            selection_text = f"  •  selectie {sx2 - sx1}×{sy2 - sy1} px"
            self._update_selection_preview(selection_now, x, y + loupe_h + 46, loupe_w)

        self.canvas.itemconfigure(
            self.loupe_text_id,
            text=f"Pixel {source_x}, {source_y}  •  zoom {LOUPE_SCALE}×{selection_text}",
        )

        for item in (
            self.loupe_box_id,
            self.loupe_image_id,
            self.loupe_text_id,
            self.selection_box_id,
            self.selection_image_id,
            self.selection_text_id,
        ):
            if item is not None:
                self.canvas.tag_raise(item)

    def _update_selection_preview(
        self,
        selection: tuple[int, int, int, int],
        x: int,
        y: int,
        width_hint: int,
    ) -> None:
        if self.screen is None:
            return
        x1, y1, x2, y2 = selection
        crop = self.screen.crop((x1, y1, x2, y2))
        if crop.width < 1 or crop.height < 1:
            return

        max_w = max(width_hint, SELECTION_PREVIEW_MAX[0])
        max_h = SELECTION_PREVIEW_MAX[1]
        factor = min(max_w / crop.width, max_h / crop.height)
        factor = max(1.0, factor) if crop.width <= max_w and crop.height <= max_h else factor
        display_w = max(1, int(crop.width * factor))
        display_h = max(1, int(crop.height * factor))
        resampling = Image.Resampling.NEAREST if factor >= 1.0 else Image.Resampling.LANCZOS
        preview = crop.resize((display_w, display_h), resampling)
        self.selection_photo = ImageTk.PhotoImage(preview)

        box_right = x + display_w + 3
        box_bottom = y + display_h + 30
        if self.selection_image_id is None:
            self.selection_box_id = self.canvas.create_rectangle(
                x - 3, y - 3, box_right, box_bottom,
                fill="#07101f", outline=START_GUIDE, width=2,
            )
            self.selection_image_id = self.canvas.create_image(
                x, y, image=self.selection_photo, anchor="nw"
            )
            self.selection_text_id = self.canvas.create_text(
                x, y + display_h + 16, anchor="w",
                text="", fill="#ffffff", font=("Consolas", 10, "bold"),
            )
        else:
            self.canvas.coords(self.selection_box_id, x - 3, y - 3, box_right, box_bottom)
            self.canvas.coords(self.selection_image_id, x, y)
            self.canvas.itemconfigure(self.selection_image_id, image=self.selection_photo)
            self.canvas.coords(self.selection_text_id, x, y + display_h + 16)

        self.canvas.itemconfigure(
            self.selection_text_id,
            text=f"VOLLEDIGE TEMPLATE  •  {crop.width}×{crop.height} px",
        )

    def _start_selection(self, event) -> None:
        self.start = (event.x, event.y)
        self.selection = None
        if self.rectangle is not None:
            self.canvas.delete(self.rectangle)
        for item in (self.start_vertical, self.start_horizontal):
            if item is not None:
                self.canvas.delete(item)

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        self.start_vertical = self.canvas.create_line(
            event.x, 0, event.x, canvas_h,
            fill=START_GUIDE, width=1, dash=(3, 4),
        )
        self.start_horizontal = self.canvas.create_line(
            0, event.y, canvas_w, event.y,
            fill=START_GUIDE, width=1, dash=(3, 4),
        )
        self.rectangle = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=LOUPE_BORDER, width=3,
        )

    def _drag_selection(self, event) -> None:
        if self.start is None or self.rectangle is None:
            return
        self.canvas.coords(self.rectangle, *self.start, event.x, event.y)
        self._update_loupe(event)

    def _finish_selection(self, event) -> None:
        selection = self._selection_from_cursor(event)
        if selection is None:
            return
        self.selection = selection
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
