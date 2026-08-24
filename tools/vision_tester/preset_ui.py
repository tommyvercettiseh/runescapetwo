from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import customtkinter as ctk

from core.vision.areas import load_areas
from core.vision.colour_presets import (
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    normalize_colour_name,
    save_colour_preset,
)
from . import ui
from .app_shell import VisionTesterShell
from .colour_base import ColourBasePage


DEFAULT_PRESET_NAME = "cyan"
PRESETS_PATH_LABEL = "Saved to config/colour_presets.json."

BASIC_BG = "#f0f0f0"
BASIC_PANEL = "#f7f7f7"
BASIC_CONTROL = "#ffffff"
BASIC_BORDER = "#a8a8a8"
BASIC_TEXT = "#111111"
BASIC_MUTED = "#555555"
BASIC_BLUE = "#2563eb"
BASIC_BLUE_HOVER = "#1d4ed8"
BASIC_GREEN = "#15803d"
BASIC_RED = "#b91c1c"
BASIC_VIEW = "#202020"


def filter_preset_names(names: list[str], query: str) -> list[str]:
    terms = [term for term in query.strip().lower().split() if term]
    if not terms:
        return list(names)
    return [
        name
        for name in names
        if all(term in name.lower() for term in terms)
    ]


def format_ranges(ranges) -> str:
    if not ranges:
        return "No colour selected."
    values = []
    for lower, upper in ranges:
        values.append(
            f"H {lower[0]}-{upper[0]}  "
            f"S {lower[1]}-{upper[1]}  "
            f"V {lower[2]}-{upper[2]}"
        )
    return " | ".join(values)


def apply_basic_theme() -> None:
    """Apply the light tester palette through the shared UI foundation."""
    ctk.set_appearance_mode("light")
    ui.set_palette(
        background=BASIC_BG,
        card=BASIC_PANEL,
        card_alt=BASIC_CONTROL,
        border=BASIC_BORDER,
        control_hover="#e6e6e6",
        text=BASIC_TEXT,
        muted=BASIC_MUTED,
        accent=BASIC_BLUE,
        accent_hover=BASIC_BLUE_HOVER,
        accent_soft="#dbeafe",
        gold=BASIC_TEXT,
        danger=BASIC_RED,
        success=BASIC_GREEN,
        view_background=BASIC_VIEW,
    )


class BasicSourceControls(ttk.Frame):
    def __init__(self, parent, *, default_area: str = ui.DEFAULT_AREA):
        super().__init__(parent)
        areas = sorted(load_areas())
        selected_area = default_area if default_area in areas else (
            areas[0] if areas else "game"
        )
        self.bot_id = tk.StringVar(value="1")
        self.area = tk.StringVar(value=selected_area)

        ttk.Label(self, text="Bot ID").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            self,
            from_=1,
            to=4,
            textvariable=self.bot_id,
            width=5,
        ).grid(row=0, column=1, sticky="w", padx=(7, 18))

        ttk.Label(self, text="Area").grid(row=0, column=2, sticky="w")
        self.area_box = ttk.Combobox(
            self,
            values=areas,
            textvariable=self.area,
            width=30,
        )
        self.area_box.grid(row=0, column=3, sticky="ew", padx=(7, 0))
        self.columnconfigure(3, weight=1)

    def bot(self) -> int:
        return int(self.bot_id.get())


class BasicProgressbar(ttk.Progressbar):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, maximum=100, mode="determinate", **kwargs)

    def set(self, value: float) -> None:
        self["value"] = min(100.0, max(0.0, float(value) * 100.0))


class PresetColourPage(ColourBasePage):
    """Compact colour tester with persistent, searchable HSV presets."""

    def __init__(self, parent):
        self.preset_search = tk.StringVar()
        self.current_preset = tk.StringVar(value=DEFAULT_PRESET_NAME)
        self.preset_summary = tk.StringVar(value="No colour selected.")
        self._preset_names: list[str] = []
        self.preset_box: ttk.Combobox | None = None
        super().__init__(parent)
        self.preset_search.trace_add("write", self._preset_search_changed)
        self._reload_presets()

    def _build(self) -> None:
        self.configure(fg_color=BASIC_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        toolbar = ttk.LabelFrame(self, text="Capture", padding=(10, 7))
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 5))
        toolbar.columnconfigure(0, weight=1)

        self.source = BasicSourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew")

        ttk.Checkbutton(
            toolbar,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
        ).grid(row=0, column=1, padx=(18, 7))
        ttk.Button(toolbar, text="Capture", command=self._once).grid(
            row=0,
            column=2,
        )

        presetbar = ttk.LabelFrame(self, text="Colour preset", padding=(10, 7))
        presetbar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        presetbar.columnconfigure(1, weight=1)
        presetbar.columnconfigure(3, weight=1)

        ttk.Label(presetbar, text="Search").grid(row=0, column=0, sticky="w")
        ttk.Entry(presetbar, textvariable=self.preset_search).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(7, 14),
        )
        ttk.Label(presetbar, text="Current preset").grid(
            row=0,
            column=2,
            sticky="w",
        )
        self.preset_box = ttk.Combobox(
            presetbar,
            values=[DEFAULT_PRESET_NAME],
            textvariable=self.current_preset,
            width=24,
        )
        self.preset_box.grid(row=0, column=3, sticky="ew", padx=(7, 14))
        self.preset_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._preset_selected(self.current_preset.get()),
        )

        ttk.Button(
            presetbar,
            text="Load",
            command=self._load_current_preset,
        ).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(
            presetbar,
            text="New",
            command=self._new_preset,
        ).grid(row=0, column=5, padx=5)
        ttk.Button(
            presetbar,
            text="Save current preset",
            command=self._save_current_preset,
        ).grid(row=0, column=6, padx=5)
        ttk.Button(
            presetbar,
            text="Delete",
            command=self._delete_current_preset,
        ).grid(row=0, column=7, padx=(5, 0))

        ttk.Label(
            presetbar,
            textvariable=self.preset_summary,
            foreground=BASIC_MUTED,
        ).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            presetbar,
            text=PRESETS_PATH_LABEL,
            foreground=BASIC_MUTED,
        ).grid(
            row=1,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(6, 0),
        )

        controls = ttk.LabelFrame(self, text="Detection", padding=(10, 7))
        controls.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        controls.columnconfigure(13, weight=1)

        ttk.Label(controls, text="Min blob px").grid(row=0, column=0)
        minimum_entry = ttk.Entry(
            controls,
            textvariable=self.minimum,
            width=7,
        )
        minimum_entry.grid(row=0, column=1, padx=(5, 10))
        minimum_entry.bind("<KeyRelease>", lambda _event: self._render())

        ttk.Label(controls, text="Max blob px").grid(row=0, column=2)
        maximum_entry = ttk.Entry(
            controls,
            textvariable=self.maximum,
            width=7,
        )
        maximum_entry.grid(row=0, column=3, padx=(5, 12))
        maximum_entry.bind("<KeyRelease>", lambda _event: self._render())

        self.pipette_button = ttk.Button(
            controls,
            text="Pipette",
            command=self._toggle_pipette,
        )
        self.pipette_button.grid(row=0, column=4, padx=(0, 5))
        self.move_colour_button = ttk.Button(
            controls,
            text="Move colour",
            command=lambda: self._start_colour_mouse_action(click=False),
        )
        self.move_colour_button.grid(row=0, column=5, padx=5)
        self.click_colour_button = ttk.Button(
            controls,
            text="Click colour",
            command=lambda: self._start_colour_mouse_action(click=True),
        )
        self.click_colour_button.grid(row=0, column=6, padx=5)

        self.trace_switch = ttk.Checkbutton(
            controls,
            text="Trace",
            variable=self.mouse_trace,
            command=self._trace_changed,
        )
        self.trace_switch.grid(row=0, column=7, padx=(10, 5))
        self.auto_switch = ttk.Checkbutton(
            controls,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
        )
        self.auto_switch.grid(row=0, column=8, padx=5)

        self.zoom_label = ttk.Label(
            controls,
            text=f"Zoom {self.zoom.get()}%",
        )
        self.zoom_label.grid(row=0, column=9, padx=(10, 4))
        self.zoom_slider = ttk.Scale(
            controls,
            from_=10,
            to=100,
            variable=self.zoom,
            command=self._zoom_changed,
            length=105,
        )
        self.zoom_slider.grid(row=0, column=10, padx=(0, 12))

        ttk.Label(controls, text="Live blob").grid(row=0, column=11)
        ttk.Label(
            controls,
            textvariable=self.blob_live_text,
            foreground=BASIC_GREEN,
        ).grid(row=0, column=12, padx=(5, 8))
        ttk.Label(
            controls,
            textvariable=self.blob_range_text,
            foreground=BASIC_MUTED,
        ).grid(row=0, column=13, sticky="e")
        ttk.Button(
            controls,
            text="Reset range",
            command=self._reset_blob_history,
        ).grid(row=0, column=14, padx=(8, 0))

        self.blob_meter = BasicProgressbar(controls)
        self.blob_meter.grid(
            row=1,
            column=0,
            columnspan=15,
            sticky="ew",
            pady=(7, 0),
        )
        self.blob_meter.set(0)
        self._sync_zoom_state()

        previews = ttk.Frame(self)
        previews.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 6))
        previews.rowconfigure(0, weight=1)
        previews.columnconfigure(0, weight=3, uniform="preview")
        previews.columnconfigure(1, weight=2, uniform="preview")
        previews.columnconfigure(2, weight=2, uniform="preview")

        specs = (
            ("Live area", "Pick a colour here with the pipette."),
            ("Binary mask", "Valid matching pixels are white."),
            ("Isolated colour", "Only matching colour pixels remain."),
        )
        for column, (title, subtitle) in enumerate(specs):
            frame = ttk.LabelFrame(previews, text=title, padding=5)
            frame.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 4, 0),
            )
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)
            ttk.Label(
                frame,
                text=subtitle,
                foreground=BASIC_MUTED,
            ).grid(row=0, column=0, sticky="w", pady=(0, 4))
            view = ui.ImageView(
                frame,
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
            view.grid(row=1, column=0, sticky="nsew")
            self.views.append(view)

        self.capture_view, self.mask_view, self.isolated_view = self.views
        self.capture_view.bind("<Button-1>", self._pick)

        ttk.Label(
            self,
            textvariable=self.status,
            anchor="w",
            relief="sunken",
            padding=(7, 3),
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

    def _toggle_pipette(self) -> None:
        self.pipette = not self.pipette
        self.pipette_button.configure(
            text="Pipette ON" if self.pipette else "Pipette"
        )
        self.capture_view.configure(cursor="crosshair" if self.pipette else "")
        self.status.set(
            "Pipette active. Click in Live area."
            if self.pipette
            else "Pipette disabled."
        )

    def _preset_search_changed(self, *_args) -> None:
        self._refresh_preset_box()

    def _refresh_preset_box(self) -> None:
        if self.preset_box is None:
            return
        matches = filter_preset_names(
            self._preset_names,
            self.preset_search.get(),
        )
        values = matches or self._preset_names or [DEFAULT_PRESET_NAME]
        self.preset_box.configure(values=values)

    def _reload_presets(self, *, selected: str | None = None) -> None:
        self._preset_names = list(list_colour_presets())
        if selected:
            self.current_preset.set(selected)
        elif self.current_preset.get() not in self._preset_names:
            self.current_preset.set(
                self._preset_names[0]
                if self._preset_names
                else DEFAULT_PRESET_NAME
            )
        self._refresh_preset_box()
        if not self._preset_names:
            self.status.set(
                "No presets saved. Pick a colour, keep 'cyan', then save it."
            )

    def _preset_selected(self, value: str) -> None:
        self.current_preset.set(value)
        self._load_current_preset()

    def _load_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        if not name:
            messagebox.showerror("Preset", "Preset name is required.")
            return
        try:
            preset = load_colour_preset(name)
        except (KeyError, ValueError) as exc:
            self.status.set(str(exc))
            return

        self.ranges = preset.ranges
        self.current_preset.set(preset.name)
        self._reset_blob_history()
        self._update_preset_summary()
        self._render()
        self.status.set(f"Preset loaded: {preset.name}.")

    def _new_preset(self) -> None:
        name = simpledialog.askstring(
            "New preset",
            "Preset name:",
            parent=self.winfo_toplevel(),
        )
        if name is None:
            return
        try:
            normalized = normalize_colour_name(name)
        except ValueError as exc:
            messagebox.showerror("Preset", str(exc))
            return

        self.current_preset.set(normalized)
        self.preset_search.set("")
        self._refresh_preset_box()
        self.status.set(
            f"New preset ready: {normalized}. Pick a colour and save it."
        )

    def _save_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        if not name:
            messagebox.showerror("Preset", "Preset name is required.")
            return
        if not self.ranges:
            messagebox.showerror(
                "Preset",
                "Pick a colour with the pipette before saving.",
            )
            return

        try:
            normalized = normalize_colour_name(name)
            save_colour_preset(normalized, self.ranges)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preset", str(exc))
            return

        self._reload_presets(selected=normalized)
        self._update_preset_summary()
        self.status.set(f"Preset saved: {normalized}.")

    def _delete_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        if not name:
            return
        if not messagebox.askyesno(
            "Delete preset",
            f"Delete preset '{name}'?",
            parent=self.winfo_toplevel(),
        ):
            return

        try:
            deleted = delete_colour_preset(name)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preset", str(exc))
            return

        if not deleted:
            self.status.set(f"Preset not found: {name}.")
            return

        self.ranges = ()
        self.preset_summary.set("No colour selected.")
        self._reload_presets()
        self._render()
        self.status.set(f"Preset deleted: {name}.")

    def _update_preset_summary(self) -> None:
        self.preset_summary.set(
            f"{self.current_preset.get()}: {format_ranges(self.ranges)}"
        )

    def _pick(self, event) -> None:
        super()._pick(event)
        if self.ranges:
            self._update_preset_summary()
            self.status.set(
                f"Colour sampled for preset: {self.current_preset.get()}."
            )


class VisionTester(VisionTesterShell):
    def __init__(self) -> None:
        super().__init__(
            colour_page_type=PresetColourPage,
            background=BASIC_BG,
            muted_text=BASIC_MUTED,
            theme_setup=apply_basic_theme,
        )


def main() -> None:
    VisionTester().mainloop()


__all__ = [
    "BASIC_BG",
    "BASIC_BLUE",
    "BASIC_BLUE_HOVER",
    "BASIC_BORDER",
    "BASIC_CONTROL",
    "BASIC_GREEN",
    "BASIC_MUTED",
    "BASIC_PANEL",
    "BASIC_RED",
    "BASIC_TEXT",
    "BASIC_VIEW",
    "BasicProgressbar",
    "BasicSourceControls",
    "DEFAULT_PRESET_NAME",
    "PRESETS_PATH_LABEL",
    "PresetColourPage",
    "VisionTester",
    "apply_basic_theme",
    "filter_preset_names",
    "format_ranges",
    "main",
]
