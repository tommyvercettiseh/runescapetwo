from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk

from core.vision.colour_presets import (
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    normalize_colour_name,
    save_colour_preset,
)
from . import modern_ui


DEFAULT_PRESET_NAME = "cyan"
PRESETS_PATH_LABEL = "Saved to config/colour_presets.json."


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


class PresetColourPage(modern_ui.ColourPage):
    """Colour tester with persistent, searchable HSV presets."""

    def __init__(self, parent):
        self.preset_search = tk.StringVar()
        self.current_preset = tk.StringVar(value=DEFAULT_PRESET_NAME)
        self.preset_summary = tk.StringVar(value="No colour selected.")
        self._preset_names: list[str] = []
        self.preset_box: ctk.CTkComboBox | None = None
        super().__init__(parent)
        self.preset_search.trace_add("write", self._preset_search_changed)
        self._reload_presets()

    def _build(self) -> None:
        super()._build()

        # Keep the existing capture and preview engine, but insert one simple
        # preset row above the blob controls.
        for child in self.grid_slaves():
            info = child.grid_info()
            row = int(info.get("row", 0))
            if row >= 1:
                child.grid_configure(row=row + 1)

        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        presetbar = modern_ui._card(self)
        presetbar.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 10),
        )
        presetbar.grid_columnconfigure(0, weight=1)
        presetbar.grid_columnconfigure(1, weight=1)

        search_group = ctk.CTkFrame(presetbar, fg_color="transparent")
        search_group.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=10)
        search_group.grid_columnconfigure(0, weight=1)
        modern_ui._label(
            search_group,
            "SEARCH PRESETS",
            muted=True,
            size=10,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(
            search_group,
            textvariable=self.preset_search,
            placeholder_text="Partial search, for example: cyan or bank",
            height=34,
            corner_radius=7,
            fg_color=modern_ui.CARD_ALT,
            border_color=modern_ui.BORDER,
            text_color=modern_ui.TEXT,
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))

        current_group = ctk.CTkFrame(presetbar, fg_color="transparent")
        current_group.grid(row=0, column=1, sticky="ew", padx=8, pady=10)
        current_group.grid_columnconfigure(0, weight=1)
        modern_ui._label(
            current_group,
            "CURRENT PRESET",
            muted=True,
            size=10,
        ).grid(row=0, column=0, sticky="w")
        self.preset_box = ctk.CTkComboBox(
            current_group,
            values=[DEFAULT_PRESET_NAME],
            variable=self.current_preset,
            command=self._preset_selected,
            height=34,
            corner_radius=7,
            fg_color=modern_ui.CARD_ALT,
            border_color=modern_ui.BORDER,
            button_color=modern_ui.BORDER,
            button_hover_color=modern_ui.CONTROL_HOVER,
            text_color=modern_ui.TEXT,
        )
        self.preset_box.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        buttons = ctk.CTkFrame(presetbar, fg_color="transparent")
        buttons.grid(row=0, column=2, sticky="e", padx=(8, 14), pady=10)
        modern_ui._button(
            buttons,
            "Load preset",
            self._load_current_preset,
            width=105,
        ).grid(row=0, column=0, padx=(0, 7))
        modern_ui._button(
            buttons,
            "New preset",
            self._new_preset,
            width=105,
        ).grid(row=0, column=1, padx=(0, 7))
        modern_ui._button(
            buttons,
            "Save current preset",
            self._save_current_preset,
            primary=True,
            width=155,
        ).grid(row=0, column=2, padx=(0, 7))
        modern_ui._button(
            buttons,
            "Delete",
            self._delete_current_preset,
            danger=True,
            width=82,
        ).grid(row=0, column=3)

        summary = ctk.CTkFrame(presetbar, fg_color="transparent")
        summary.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(0, 10),
        )
        modern_ui._label(
            summary,
            "",
            textvariable=self.preset_summary,
            size=10,
        ).pack(side="left")
        modern_ui._label(
            summary,
            PRESETS_PATH_LABEL,
            muted=True,
            size=10,
        ).pack(side="right")

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


class VisionTester(modern_ui.VisionTester):
    def __init__(self):
        original_colour_page = modern_ui.ColourPage
        modern_ui.ColourPage = PresetColourPage
        try:
            super().__init__()
        finally:
            modern_ui.ColourPage = original_colour_page

        # Keep enough room for the three useful previews, but use a calmer,
        # more compact default window like the other Unified Tester.
        self.geometry("1280x820")
        self.minsize(1080, 720)


def main() -> None:
    VisionTester().mainloop()
