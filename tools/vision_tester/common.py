from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import load_areas


class PreviewLabel(ttk.Label):
    def __init__(self, parent, *, fallback_width: int = 620, fallback_height: int = 360):
        super().__init__(parent, anchor="center")
        self.fallback_width = fallback_width
        self.fallback_height = fallback_height
        self.scale = 1.0
        self._photo: ImageTk.PhotoImage | None = None

    def show(self, rgb: np.ndarray) -> None:
        height, width = rgb.shape[:2]
        target_width = max(300, self.winfo_width() or self.fallback_width)
        target_height = max(180, self.winfo_height() or self.fallback_height)
        self.scale = min(1.0, target_width / width, target_height / height)
        resized = cv2.resize(
            rgb,
            (max(1, int(width * self.scale)), max(1, int(height * self.scale))),
            interpolation=cv2.INTER_AREA if self.scale < 1.0 else cv2.INTER_NEAREST,
        )
        self._photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self.configure(image=self._photo)


class SourceBar(ttk.Frame):
    def __init__(self, parent, *, default_area: str = "game"):
        super().__init__(parent, padding=8)
        self.bot_id = tk.IntVar(value=1)
        self.area = tk.StringVar(value=default_area)

        ttk.Label(self, text="Bot").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=6,
        ).grid(row=1, column=0, sticky="w", padx=(0, 8))

        ttk.Label(self, text="Area").grid(row=0, column=1, sticky="w")
        self.area_box = ttk.Combobox(
            self,
            textvariable=self.area,
            state="readonly",
            width=34,
        )
        self.area_box.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.columnconfigure(1, weight=1)
        self.refresh_areas()

    def refresh_areas(self) -> None:
        areas = sorted(load_areas())
        self.area_box["values"] = areas
        if areas and self.area.get() not in areas:
            self.area.set("game" if "game" in areas else areas[0])
