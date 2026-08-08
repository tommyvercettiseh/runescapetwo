from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import unified_plus


class SaveUpdatedColourPage(unified_plus.ToleranceColourPage):
    """Add an explicit save button for edits to an existing colour preset."""

    def _build(self) -> None:
        super()._build()
        self._add_save_updated_colour_button()

    def _add_save_updated_colour_button(self) -> None:
        colour_width = None
        for child in self.grid_slaves():
            try:
                if isinstance(child, ttk.LabelFrame) and str(child.cget("text")) == "Colour width":
                    colour_width = child
                    break
            except tk.TclError:
                continue

        if colour_width is None:
            return

        ttk.Button(
            colour_width,
            text="Save updated colour",
            command=self._save_updated_colour,
        ).grid(row=0, column=6, padx=(10, 0), sticky="e")

    def _save_updated_colour(self) -> None:
        active = set(getattr(self, "_active_colour_names", set()))
        if len(active) != 1:
            if not active:
                self.status.set("Selecteer eerst één colour om te updaten.")
            else:
                self.status.set("Selecteer precies één colour om te updaten.")
            return

        name = next(iter(active))
        if not self.base_colours:
            self.status.set(f"Colour '{name}' heeft geen basiskleuren om op te slaan.")
            return

        self.current_preset.set(name)
        self._save_current_preset()
        self.status.set(
            f"Colour '{name}' bijgewerkt · {len(self.base_colours)} base colour(s) · "
            f"tolerance {self.colour_tolerance.get()}%."
        )


def install_colour_update_button() -> None:
    unified_plus.ToleranceColourPage = SaveUpdatedColourPage


__all__ = ["SaveUpdatedColourPage", "install_colour_update_button"]
