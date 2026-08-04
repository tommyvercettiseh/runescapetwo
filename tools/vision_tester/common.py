from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Iterable
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import load_areas


COLOURS = {
    "background": "#0b1020",
    "surface": "#111827",
    "surface_raised": "#182235",
    "border": "#26344d",
    "text": "#e8eef9",
    "muted": "#91a0b8",
    "accent": "#5eead4",
    "accent_dark": "#153f43",
    "blue": "#60a5fa",
    "danger": "#fb7185",
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
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground="#f8fafc")
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
        padding=(12, 8),
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", "#22304a"), ("pressed", COLOURS["accent_dark"])],
        bordercolor=[("focus", COLOURS["accent"])],
    )
    style.configure(
        "Accent.TButton",
        background=COLOURS["accent"],
        foreground="#071a1d",
        bordercolor=COLOURS["accent"],
        font=("Segoe UI Semibold", 10),
    )
    style.map("Accent.TButton", background=[("active", "#99f6e4"), ("pressed", "#2dd4bf")])
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
        background=[("selected", COLOURS["accent_dark"]), ("active", "#22304a")],
        foreground=[("selected", COLOURS["accent"]), ("active", COLOURS["text"])],
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
    style.configure("TNotebook", background=COLOURS["background"], borderwidth=0, tabmargins=(18, 0, 0, 0))
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
        foreground=[("selected", COLOURS["accent"]), ("active", COLOURS["text"])],
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
    def __init__(self, parent, *, fallback_width: int = 620, fallback_height: int = 360):
        super().__init__(parent, anchor="center", style="Surface.TLabel")
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
        super().__init__(parent, padding=(0, 0), style="Surface.TFrame")
        self.bot_id = tk.IntVar(value=1)
        self.area = tk.StringVar(value=default_area)

        ttk.Label(self, text="BOT", style="SurfaceMuted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=6,
        ).grid(row=1, column=0, sticky="w", padx=(0, 10))

        ttk.Label(self, text="AREA ZOEKEN", style="SurfaceMuted.TLabel").grid(row=0, column=1, sticky="w")
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
