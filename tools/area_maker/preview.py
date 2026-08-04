from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import pyautogui
from PIL import Image, ImageDraw, ImageTk

from .store import EditableArea

PREVIEW_WIDTH = 380
PREVIEW_HEIGHT = 260
MARGIN_PX = 8


@dataclass(frozen=True)
class PreviewRegion:
    x: int
    y: int
    width: int
    height: int


def calculate_crop(
    selected: PreviewRegion,
    *,
    desktop_size: tuple[int, int],
    margin: int = MARGIN_PX,
) -> PreviewRegion:
    desktop_width, desktop_height = desktop_size
    x1 = max(0, selected.x - margin)
    y1 = max(0, selected.y - margin)
    x2 = min(desktop_width, selected.x + selected.width + margin)
    y2 = min(desktop_height, selected.y + selected.height + margin)
    return PreviewRegion(x1, y1, max(1, x2 - x1), max(1, y2 - y1))


def calculate_scale(
    region: PreviewRegion,
    *,
    preview_size: tuple[int, int] = (PREVIEW_WIDTH, PREVIEW_HEIGHT),
) -> int:
    preview_width, preview_height = preview_size
    return max(
        1,
        min(
            preview_width // max(1, region.width),
            preview_height // max(1, region.height),
        ),
    )


class AreaPreview(ttk.LabelFrame):
    """Magnified, nearest-neighbour preview of one selected area."""

    def __init__(self, parent) -> None:
        super().__init__(parent, text="Uitvergrote preview", padding=6)
        self._desktop: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None

        self.canvas = tk.Canvas(
            self,
            width=PREVIEW_WIDTH,
            height=PREVIEW_HEIGHT,
            bg="#111111",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.info = tk.StringVar(value="Selecteer een area.")
        ttk.Label(self, textvariable=self.info).pack(fill="x", pady=(5, 0))

    def capture_desktop(self) -> None:
        self._desktop = pyautogui.screenshot().convert("RGB")

    def clear(self) -> None:
        self.canvas.delete("all")
        self.info.set("Selecteer een area.")
        self._photo = None

    def show_area(self, area: EditableArea, *, offset: tuple[int, int]) -> None:
        if self._desktop is None:
            self.info.set("Klik op 'Preview verversen'.")
            return

        ox, oy = offset
        selected = PreviewRegion(
            x=area.x + ox,
            y=area.y + oy,
            width=area.width,
            height=area.height,
        )
        crop = calculate_crop(selected, desktop_size=self._desktop.size)
        image = self._desktop.crop((crop.x, crop.y, crop.x + crop.width, crop.y + crop.height))

        scale = calculate_scale(crop)
        rendered = image.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)

        draw = ImageDraw.Draw(rendered)
        left = (selected.x - crop.x) * scale
        top = (selected.y - crop.y) * scale
        right = (selected.x + selected.width - crop.x) * scale - 1
        bottom = (selected.y + selected.height - crop.y) * scale - 1
        line_width = max(2, min(5, scale))
        draw.rectangle((left, top, right, bottom), outline=(0, 229, 255), width=line_width)

        self._photo = ImageTk.PhotoImage(rendered)
        self.canvas.delete("all")
        x = max(0, (PREVIEW_WIDTH - rendered.width) // 2)
        y = max(0, (PREVIEW_HEIGHT - rendered.height) // 2)
        self.canvas.create_image(x, y, image=self._photo, anchor="nw")
        self.info.set(
            f"x={area.x}  y={area.y}  breedte={area.width}  hoogte={area.height}  |  zoom {scale}×"
        )
