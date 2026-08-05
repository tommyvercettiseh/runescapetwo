from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Iterable
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import load_areas


COLOURS = {
    "background": "#f3f7fc",
    "surface": "#ffffff",
    "surface_raised": "#f7faff",
    "border": "#d9e3f0",
    "text": "#17243d",
    "muted": "#71809a",
    "accent": "#42cfe8",
    "accent_dark": "#dff7fc",
    "blue": "#2f80ed",
    "danger": "#e05267",
}


def filter_options(options: Iterable[str], query: str) -> list[str]:
    """Filter options case-insensitively by any partial match."""
    needle = query.strip().casefold()
    values = list(options)
    if not needle:
        return values
    return [value for value in values if needle in value.casefold()]


def configure_style(root: tk.Tk) -> None:
    """Apply the shared modern dark theme without external UI dependencies."""
    root.configure(background=COLOURS["background"])
    root.option_add("*Font", ("Segoe UI", 10))
    root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
    root.option_add("*TCombobox*Listbox.background", COLOURS["surface_raised"])
    root.option_add("*TCombobox*Listbox.foreground", COLOURS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLOURS["accent_dark"])

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=COLOURS["background"], foreground=COLOURS["text"])
    style.configure("TFrame", background=COLOURS["background"])
    style.configure("Surface.TFrame", background=COLOURS["surface"])
    style.configure("Raised.TFrame", background=COLOURS["surface_raised"])
    style.configure("TLabel", background=COLOURS["background"], foreground=COLOURS["text"])
    style.configure("Surface.TLabel", background=COLOURS["surface"], foreground=COLOURS["text"])
    style.configure("Muted.TLabel", background=COLOURS["background"], foreground=COLOURS["muted"])
    style.configure("SurfaceMuted.TLabel", background=COLOURS["surface"], foreground=COLOURS["muted"])
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground=COLOURS["text"])
    style.configure("Subtitle.TLabel", foreground=COLOURS["muted"], font=("Segoe UI", 10))
    style.configure(
        "Card.TLabelframe",
        background=COLOURS["surface"],
        bordercolor=COLOURS["border"],
        lightcolor=COLOURS["border"],
        darkcolor=COLOURS["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=COLOURS["surface"],
        foreground=COLOURS["text"],
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "TButton",
        background=COLOURS["surface_raised"],
        foreground=COLOURS["text"],
        bordercolor=COLOURS["border"],
        padding=(13, 9),
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", "#eaf1fa"), ("pressed", COLOURS["accent_dark"])],
        bordercolor=[("focus", COLOURS["accent"])],
    )
    style.configure(
        "Accent.TButton",
        background=COLOURS["accent"],
        foreground="#073b47",
        bordercolor=COLOURS["accent"],
        font=("Segoe UI Semibold", 10),
    )
    style.map("Accent.TButton", background=[("active", "#79dff1"), ("pressed", "#2bb9d3")])
    style.configure(
        "Icon.TButton",
        background=COLOURS["surface_raised"],
        bordercolor=COLOURS["border"],
        padding=(11, 8),
    )
    style.configure(
        "IconActive.TButton",
        background=COLOURS["accent_dark"],
        bordercolor=COLOURS["accent"],
        padding=(11, 8),
    )
    style.map("Icon.TButton", background=[("active", "#eaf1fa")])
    style.map("IconActive.TButton", background=[("active", "#c9f0f8")])
    style.configure(
        "Toggle.TCheckbutton",
        background=COLOURS["surface_raised"],
        foreground=COLOURS["muted"],
        bordercolor=COLOURS["border"],
        indicatorcolor=COLOURS["surface_raised"],
        padding=(13, 8),
        relief="solid",
        borderwidth=1,
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Toggle.TCheckbutton",
        background=[("selected", COLOURS["accent_dark"]), ("active", "#eaf1fa")],
        foreground=[("selected", "#087f95"), ("active", COLOURS["text"])],
        bordercolor=[("selected", COLOURS["accent"]), ("focus", COLOURS["accent"])],
        indicatorcolor=[("selected", COLOURS["accent"]), ("!selected", COLOURS["muted"])],
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLOURS["surface_raised"],
        background=COLOURS["surface_raised"],
        foreground=COLOURS["text"],
        arrowcolor=COLOURS["muted"],
        bordercolor=COLOURS["border"],
        padding=7,
    )
    style.map("TCombobox", fieldbackground=[("readonly", COLOURS["surface_raised"])])
    style.configure(
        "TEntry",
        fieldbackground=COLOURS["surface_raised"],
        foreground=COLOURS["text"],
        bordercolor=COLOURS["border"],
        insertcolor=COLOURS["text"],
        padding=8,
    )
    style.configure(
        "TSpinbox",
        fieldbackground=COLOURS["surface_raised"],
        foreground=COLOURS["text"],
        arrowcolor=COLOURS["muted"],
        bordercolor=COLOURS["border"],
        padding=6,
    )
    style.configure("TNotebook", background=COLOURS["background"], borderwidth=0, tabmargins=(22, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=COLOURS["background"],
        foreground=COLOURS["muted"],
        padding=(20, 11),
        borderwidth=0,
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOURS["surface"])],
        foreground=[("selected", "#087f95"), ("active", COLOURS["text"])],
    )
    style.configure("Horizontal.TPanedwindow", background=COLOURS["background"])
    style.configure("TScrollbar", background=COLOURS["surface_raised"], troughcolor=COLOURS["surface"])


class FilterCombobox(ttk.Combobox):
    """Editable combobox whose dropdown filters on partial input."""

    def __init__(self, parent, *, values: Iterable[str] = (), **kwargs):
        kwargs.pop("state", None)
        super().__init__(parent, values=tuple(values), state="normal", **kwargs)
        self._all_values = list(values)
        self.bind("<KeyRelease>", self._filter, add="+")
        self.bind("<FocusIn>", self._select_text, add="+")

    def set_options(self, values: Iterable[str]) -> None:
        self._all_values = list(values)
        self.configure(values=self._all_values)

    def _filter(self, event) -> None:
        if event.keysym in {"Up", "Down", "Return", "Escape", "Tab"}:
            return
        matches = filter_options(self._all_values, self.get())
        self.configure(values=matches)
        if matches:
            self.event_generate("<Down>")

    def _select_text(self, _event) -> None:
        self.after_idle(lambda: self.selection_range(0, "end"))


class LiveToggle(ttk.Checkbutton):
    """Persistent live on/off control with an obvious selected state."""

    def __init__(self, parent, *, variable: tk.BooleanVar, command: Callable[[], None]):
        self.variable = variable
        self.label = tk.StringVar()
        super().__init__(
            parent,
            textvariable=self.label,
            variable=variable,
            command=command,
            style="Toggle.TCheckbutton",
        )
        variable.trace_add("write", self._sync_label)
        self._sync_label()

    def _sync_label(self, *_args) -> None:
        self.label.set("● LIVE AAN" if self.variable.get() else "○ LIVE UIT")


class PreviewLabel(ttk.Label):
    def __init__(
        self,
        parent,
        *,
        fallback_width: int = 620,
        fallback_height: int = 360,
        allow_upscale: bool = False,
        maximum_upscale: float = 6.0,
    ):
        super().__init__(parent, anchor="center", style="Surface.TLabel")
        self.fallback_width = fallback_width
        self.fallback_height = fallback_height
        self.allow_upscale = allow_upscale
        self.maximum_upscale = max(1.0, float(maximum_upscale))
        self.scale = 1.0
        self.image_offset = (0, 0)
        self.display_size = (0, 0)
        self._photo: ImageTk.PhotoImage | None = None
        self._last_rgb: np.ndarray | None = None
        self._resize_job: str | None = None
        self.bind("<Configure>", self._schedule_redraw, add="+")

    def show(self, rgb: np.ndarray) -> None:
        self._last_rgb = rgb
        self._draw(rgb)

    def _draw(self, rgb: np.ndarray) -> None:
        height, width = rgb.shape[:2]
        widget_width = self.winfo_width()
        widget_height = self.winfo_height()
        target_width = self.fallback_width if widget_width <= 1 else widget_width
        target_height = self.fallback_height if widget_height <= 1 else widget_height
        scale_limit = self.maximum_upscale if self.allow_upscale else 1.0
        self.scale = min(scale_limit, target_width / width, target_height / height)
        display_width = max(1, int(width * self.scale))
        display_height = max(1, int(height * self.scale))
        self.display_size = (display_width, display_height)
        self.image_offset = (
            max(0, (target_width - display_width) // 2),
            max(0, (target_height - display_height) // 2),
        )
        resized = cv2.resize(
            rgb,
            self.display_size,
            interpolation=cv2.INTER_AREA if self.scale < 1.0 else cv2.INTER_NEAREST,
        )
        self._photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self.configure(image=self._photo)

    def _schedule_redraw(self, _event) -> None:
        if self._last_rgb is None:
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._redraw)

    def _redraw(self) -> None:
        self._resize_job = None
        if self._last_rgb is not None:
            self._draw(self._last_rgb)

    def image_coordinates(self, widget_x: int, widget_y: int) -> tuple[int, int] | None:
        """Translate a click in the centred preview back to its source pixel."""
        offset_x, offset_y = self.image_offset
        display_width, display_height = self.display_size
        relative_x = widget_x - offset_x
        relative_y = widget_y - offset_y
        if not 0 <= relative_x < display_width or not 0 <= relative_y < display_height:
            return None
        return (
            int(relative_x / max(self.scale, 1e-9)),
            int(relative_y / max(self.scale, 1e-9)),
        )


class SourceBar(ttk.Frame):
    def __init__(self, parent, *, default_area: str = "game"):
        super().__init__(parent, padding=(0, 0), style="Surface.TFrame")
        self.bot_id = tk.IntVar(value=1)
        self.area = tk.StringVar(value=default_area)

        ttk.Label(self, text="BOT ID", style="SurfaceMuted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=6,
        ).grid(row=1, column=0, sticky="w", padx=(0, 10))

        ttk.Label(self, text="AREA", style="SurfaceMuted.TLabel").grid(row=0, column=1, sticky="w")
        self.area_box = FilterCombobox(
            self,
            textvariable=self.area,
            width=34,
        )
        self.area_box.grid(row=1, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)
        self.refresh_areas()

    def refresh_areas(self) -> None:
        areas = sorted(load_areas())
        self.area_box.set_options(areas)
        if areas and self.area.get() not in areas:
            self.area.set("game" if "game" in areas else areas[0])
