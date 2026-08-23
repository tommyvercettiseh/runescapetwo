from __future__ import annotations

from tkinter import simpledialog

import customtkinter as ctk

from core.vision.colour_presets import list_colour_presets, normalize_colour_name

from . import modern_ui, unified_plus
from .colour_browser import BrowserToleranceColourPage


class ManualColourPage(BrowserToleranceColourPage):
    """Colour browser with explicit create/update persistence instead of autosave."""

    def _build_colour_browser(self) -> None:
        super()._build_colour_browser()
        self.new_colour_button.configure(
            text="Add new colour",
            command=self._new_colour_from_browser,
        )

        sidebar = self.new_colour_button.master
        for child in list(sidebar.grid_slaves()):
            if child is self.new_colour_button:
                continue
            info = child.grid_info()
            row = int(info.get("row", 0))
            if row >= 3:
                child.grid_configure(row=row + 1)

        sidebar.grid_rowconfigure(3, weight=0)
        sidebar.grid_rowconfigure(4, weight=1)
        self.save_colour_button = ctk.CTkButton(
            sidebar,
            text="Save updated colour",
            command=self._save_colour_from_browser,
            height=34,
            corner_radius=7,
            fg_color=modern_ui.CARD_ALT,
            hover_color=modern_ui.ACCENT_SOFT,
            text_color=modern_ui.TEXT,
        )
        self.save_colour_button.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 9),
        )

    def _new_colour_from_browser(self) -> None:
        name = simpledialog.askstring(
            "Add new colour",
            "Naam van de colour:",
            parent=self.winfo_toplevel(),
        )
        if name is None:
            return

        try:
            name = normalize_colour_name(name)
        except ValueError:
            self.status.set("Colour niet aangemaakt: naam ontbreekt.")
            return

        if name in set(list_colour_presets()):
            self._active_colour_names = {name}
            self.current_preset.set(name)
            self._load_current_preset()
            self._draw_colour_browser()
            self.status.set(f"Colour '{name}' bestaat al en is geselecteerd.")
            return

        self.current_preset.set(name)
        self.base_colours = []
        self.colour_tolerance.set(unified_plus.DEFAULT_TOLERANCE)
        self._active_colour_names = {name}
        self._rebuild_ranges()

        if not self.pipette:
            self._toggle_pipette()

        self.status.set(
            f"Nieuwe colour '{name}' klaar. Klik kleur(en) met het pipet en daarna Save updated colour."
        )

    def _pick(self, event) -> None:
        """Pick only; persistence remains an explicit user action."""
        unified_plus.ToleranceColourPage._pick(self, event)

    def _save_colour_from_browser(self) -> None:
        active = set(self._active_colour_names)
        if len(active) != 1:
            self.status.set(
                "Selecteer precies één colour om op te slaan of te updaten."
                if active
                else "Selecteer eerst één colour om op te slaan of te updaten."
            )
            return

        name = normalize_colour_name(next(iter(active)))
        if not self.base_colours:
            self.status.set(
                f"Colour '{name}' heeft nog geen gepipette kleur; niets opgeslagen."
            )
            return

        self.current_preset.set(name)
        unified_plus.ToleranceColourPage._save_current_preset(self)
        self._active_colour_names = {name}
        self.current_preset.set(name)
        self._draw_colour_browser()
        self.status.set(
            f"Colour '{name}' bijgewerkt · {len(self.base_colours)} kleur(en) · "
            f"tolerance {self.colour_tolerance.get()}%."
        )


def install_manual_colour_save() -> None:
    """Compatibility no-op; use ManualColourPage explicitly."""


__all__ = ["ManualColourPage", "install_manual_colour_save"]
