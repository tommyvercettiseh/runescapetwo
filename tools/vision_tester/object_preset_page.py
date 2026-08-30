from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from core.vision.areas import load_areas
from core.vision.colour_detection import find_colour_blobs
from core.vision.colour_presets import list_colour_presets
from core.vision.object_presets import (
    delete_object_preset,
    list_object_presets,
    load_object_preset,
    normalize_object_name,
    save_object_preset,
)

from . import modern_ui


POLL_MS = 200
AUTO_MARGIN = 0.10


class ObjectPresetPage(ctk.CTkFrame):
    """Minimal colour-object calibrator backed by object_presets.json."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=modern_ui.BG)
        self.name = tk.StringVar(master=self, value="")
        self.colour = tk.StringVar(master=self, value="")
        self.area = tk.StringVar(master=self, value="Bot_Area")
        self.bot_id = tk.IntVar(master=self, value=1)
        self.observed_min = tk.StringVar(master=self, value="0")
        self.observed_max = tk.StringVar(master=self, value="0")
        self.saved_min = tk.StringVar(master=self, value="0")
        self.saved_max = tk.StringVar(master=self, value="0")
        self.auto_margin = tk.BooleanVar(master=self, value=True)
        self.status = tk.StringVar(master=self, value="Reset en kies een colour om te meten.")
        self._observed_min: int | None = None
        self._observed_max: int | None = None
        self._active = False
        self._poll_job: str | None = None
        self._preset_list: tk.Listbox | None = None
        self._json_preview: tk.Text | None = None
        self._build()
        self._refresh_presets()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        detection = modern_ui._card(self)
        detection.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        detection.grid_columnconfigure(1, weight=1)
        modern_ui._label(detection, "DETECTION", size=12, bold=True).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 12)
        )

        self._combo_row(
            detection,
            1,
            "Colour",
            self.colour,
            list(list_colour_presets()),
        )
        self._combo_row(
            detection,
            2,
            "Area",
            self.area,
            sorted(load_areas()),
        )

        ttk.Label(detection, text="Bot ID").grid(row=3, column=0, sticky="w", padx=16, pady=8)
        ttk.Spinbox(detection, from_=1, to=4, textvariable=self.bot_id, width=6).grid(
            row=3, column=1, sticky="ew", padx=(6, 16), pady=8
        )

        self._value_row(detection, 4, "Observed min px", self.observed_min)
        self._value_row(detection, 5, "Observed max px", self.observed_max)
        self._entry_row(detection, 6, "Saved min px", self.saved_min)
        self._entry_row(detection, 7, "Saved max px", self.saved_max)

        ttk.Checkbutton(
            detection,
            text="Auto margin 10%",
            variable=self.auto_margin,
            command=self._apply_observed_to_saved,
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 5))

        controls = ttk.Frame(detection)
        controls.grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 10))
        ttk.Button(controls, text="Reset", command=self.reset_measurement).pack(side="left")
        ttk.Button(controls, text="Measure now", command=self._measure_once).pack(
            side="left", padx=(7, 0)
        )

        ttk.Label(
            detection,
            text="Draai camera/object. Min en max blijven automatisch meelopen.",
            wraplength=320,
            foreground=modern_ui.MUTED,
        ).grid(row=10, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 16))

        preset = modern_ui._card(self)
        preset.grid(row=0, column=1, sticky="nsew", padx=6, pady=12)
        preset.grid_columnconfigure(0, weight=1)
        preset.grid_rowconfigure(5, weight=1)
        modern_ui._label(preset, "OBJECT PRESET", size=12, bold=True).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 12)
        )

        ctk.CTkEntry(
            preset,
            textvariable=self.name,
            placeholder_text="furnace",
            height=38,
            corner_radius=8,
            fg_color=modern_ui.CARD_ALT,
            border_color=modern_ui.BORDER,
            text_color=modern_ui.TEXT,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        modern_ui._button(
            preset,
            "Save / Update",
            self.save_current,
            primary=True,
            width=210,
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 7))
        modern_ui._button(
            preset,
            "Delete",
            self.delete_current,
            primary=False,
            width=210,
        ).grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))

        ttk.Label(preset, text="Saved objects").grid(row=4, column=0, sticky="w", padx=16)
        self._preset_list = tk.Listbox(
            preset,
            activestyle="none",
            exportselection=False,
            relief="flat",
            height=12,
        )
        self._preset_list.grid(row=5, column=0, sticky="nsew", padx=16, pady=(6, 16))
        self._preset_list.bind("<<ListboxSelect>>", self._preset_selected)

        preview = modern_ui._card(self)
        preview.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=12)
        preview.grid_columnconfigure(0, weight=1)
        preview.grid_rowconfigure(1, weight=1)
        modern_ui._label(preview, "JSON PREVIEW", size=12, bold=True).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 12)
        )
        self._json_preview = tk.Text(
            preview,
            wrap="none",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self._json_preview.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 10))
        ttk.Label(preview, textvariable=self.status, wraplength=320).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 16)
        )
        self._update_json_preview()

    def _combo_row(self, parent, row: int, label: str, variable, values) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        box = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        box.grid(row=row, column=1, sticky="ew", padx=(6, 16), pady=8)
        box.bind("<<ComboboxSelected>>", lambda _event: self.reset_measurement())

    def _value_row(self, parent, row: int, label: str, variable) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Label(parent, textvariable=variable, font=("Segoe UI", 14, "bold")).grid(
            row=row, column=1, sticky="e", padx=16, pady=8
        )

    def _entry_row(self, parent, row: int, label: str, variable) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=(6, 16), pady=8
        )

    def _refresh_presets(self, select: str | None = None) -> None:
        if self._preset_list is None:
            return
        names = list(list_object_presets())
        self._preset_list.delete(0, "end")
        for name in names:
            self._preset_list.insert("end", name)
        if select in names:
            index = names.index(select)
            self._preset_list.selection_set(index)
            self._preset_list.see(index)

    def _preset_selected(self, _event=None) -> None:
        if self._preset_list is None or not self._preset_list.curselection():
            return
        name = str(self._preset_list.get(self._preset_list.curselection()[0]))
        preset = load_object_preset(name)
        self.name.set(preset.name)
        self.colour.set(preset.colour)
        self.area.set(preset.area)
        self.saved_min.set(str(preset.min_pixels))
        self.saved_max.set("0" if preset.max_pixels is None else str(preset.max_pixels))
        self.reset_measurement(clear_saved=False)
        self.status.set(f"'{name}' geladen. Reset en meet opnieuw om hem te kalibreren.")
        self._update_json_preview()

    def reset_measurement(self, clear_saved: bool = True) -> None:
        self._observed_min = None
        self._observed_max = None
        self.observed_min.set("0")
        self.observed_max.set("0")
        if clear_saved:
            self.saved_min.set("0")
            self.saved_max.set("0")
        self.status.set("Metingen gereset. Draai camera/object om bereik op te bouwen.")
        self._update_json_preview()

    def _measure_once(self) -> None:
        colour = self.colour.get().strip()
        area = self.area.get().strip()
        if not colour or not area:
            return
        try:
            blobs = find_colour_blobs(
                colour,
                area=area,
                bot_id=int(self.bot_id.get()),
                minimum_area_px=1,
                maximum_area_px=None,
            )
        except (KeyError, ValueError, OSError) as exc:
            self.status.set(f"Meten mislukt: {exc}")
            return
        if not blobs:
            self.status.set("Geen blob gevonden voor deze colour/area.")
            return

        pixels = int(blobs[0].area_px)
        self._observed_min = pixels if self._observed_min is None else min(self._observed_min, pixels)
        self._observed_max = pixels if self._observed_max is None else max(self._observed_max, pixels)
        self.observed_min.set(str(self._observed_min))
        self.observed_max.set(str(self._observed_max))
        self._apply_observed_to_saved()
        self.status.set(f"Tracking {colour} · laatste blob {pixels} px")

    def _apply_observed_to_saved(self) -> None:
        if self._observed_min is None or self._observed_max is None:
            self._update_json_preview()
            return
        if self.auto_margin.get():
            minimum = max(1, int(self._observed_min * (1.0 - AUTO_MARGIN)))
            maximum = max(minimum, int(self._observed_max * (1.0 + AUTO_MARGIN)))
        else:
            minimum = self._observed_min
            maximum = self._observed_max
        self.saved_min.set(str(minimum))
        self.saved_max.set(str(maximum))
        self._update_json_preview()

    def save_current(self) -> None:
        try:
            name = normalize_object_name(self.name.get())
            minimum = int(self.saved_min.get())
            maximum = int(self.saved_max.get())
            preset = save_object_preset(
                name,
                colour=self.colour.get(),
                min_pixels=minimum,
                max_pixels=maximum,
                area=self.area.get(),
            )
        except (KeyError, ValueError, OSError) as exc:
            self.status.set(f"Niet opgeslagen: {exc}")
            return
        self.name.set(preset.name)
        self._refresh_presets(select=preset.name)
        self.status.set(f"Object '{preset.name}' opgeslagen / bijgewerkt.")
        self._update_json_preview()

    def delete_current(self) -> None:
        name = self.name.get().strip()
        if not name:
            return
        try:
            deleted = delete_object_preset(name)
        except (ValueError, OSError) as exc:
            self.status.set(f"Verwijderen mislukt: {exc}")
            return
        if deleted:
            self.status.set(f"Object '{name}' verwijderd.")
            self.name.set("")
            self._refresh_presets()
            self._update_json_preview()

    def _update_json_preview(self) -> None:
        if self._json_preview is None:
            return
        name = self.name.get().strip() or "object_name"
        payload = {
            name: {
                "colour": self.colour.get().strip(),
                "min_pixels": self._safe_int(self.saved_min.get()),
                "max_pixels": self._safe_int(self.saved_max.get()),
                "area": self.area.get().strip(),
            }
        }
        self._json_preview.configure(state="normal")
        self._json_preview.delete("1.0", "end")
        self._json_preview.insert("1.0", json.dumps(payload, indent=2))
        self._json_preview.configure(state="disabled")

    @staticmethod
    def _safe_int(value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return 0

    def _poll(self) -> None:
        self._poll_job = None
        if not self._active:
            return
        self._measure_once()
        self._poll_job = self.after(POLL_MS, self._poll)

    def activate(self) -> None:
        if self._active:
            return
        self._active = True
        self._poll()

    def deactivate(self) -> None:
        self._active = False
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except tk.TclError:
                pass
            self._poll_job = None

    def capture_hotkey(self) -> None:
        self._measure_once()


__all__ = ["ObjectPresetPage"]
