from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog

import customtkinter as ctk

from . import colour_browser, unified_plus


_BROWSER_CLASS = colour_browser.BrowserToleranceColourPage
_BASE_COLOUR_CLASS = _BROWSER_CLASS.__mro__[1]


def _find_new_colour_button(widget):
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkButton):
            try:
                if str(child.cget("text")).strip().casefold() == "new colour":
                    return child
            except tk.TclError:
                pass
        found = _find_new_colour_button(child)
        if found is not None:
            return found
    return None


def _build_colour_browser_manual(self) -> None:
    _ORIGINAL_BUILD_COLOUR_BROWSER(self)

    button = _find_new_colour_button(self)
    if button is None:
        return

    button.configure(text="Add new colour", command=self._new_colour_from_browser)
    sidebar = button.master

    # Move the browser list/help one row down to make room for explicit saving.
    for child in list(sidebar.grid_slaves()):
        if child is button:
            continue
        info = child.grid_info()
        row = int(info.get("row", 0))
        if row >= 3:
            child.grid_configure(row=row + 1)

    sidebar.grid_rowconfigure(3, weight=0)
    sidebar.grid_rowconfigure(4, weight=1)

    save = ctk.CTkButton(
        sidebar,
        text="Save updated colour",
        command=self._save_colour_from_browser,
        height=34,
        corner_radius=7,
        fg_color=unified_plus.enhanced_ui.modern_ui.CARD_ALT,
        hover_color=unified_plus.enhanced_ui.modern_ui.ACCENT_SOFT,
        text_color=unified_plus.enhanced_ui.modern_ui.TEXT,
    )
    save.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 9))


def _new_colour_from_browser_manual(self) -> None:
    name = simpledialog.askstring(
        "Add new colour",
        "Naam van de colour:",
        parent=self.winfo_toplevel(),
    )
    if name is None:
        return

    name = name.strip()
    if not name:
        self.status.set("Colour niet aangemaakt: naam ontbreekt.")
        return

    self.current_preset.set(name)
    self.base_colours = []
    self.colour_tolerance.set(unified_plus.DEFAULT_TOLERANCE)
    self._active_colour_names = {name}
    self._rebuild_ranges()
    self._draw_colour_browser()
    self.status.set(
        f"Nieuwe colour '{name}'. Pipet kleur(en), stel tolerance in en klik Save updated colour."
    )


def _pick_manual(self, event) -> None:
    # Pick only. Deliberately do NOT autosave; the user decides when to save.
    _BASE_COLOUR_CLASS._pick(self, event)


def _save_colour_from_browser(self) -> None:
    active = set(getattr(self, "_active_colour_names", set()))
    if len(active) != 1:
        if not active:
            self.status.set("Selecteer eerst één colour om op te slaan of te updaten.")
        else:
            self.status.set("Selecteer precies één colour om te updaten.")
        return

    name = next(iter(active))
    if not self.base_colours:
        self.status.set(f"Colour '{name}' heeft nog geen gepipette kleur; niets opgeslagen.")
        return

    self.current_preset.set(name)

    # Base save persists both generated HSV ranges and metadata containing
    # the exact base colours + the current tolerance value.
    _BASE_COLOUR_CLASS._save_current_preset(self)
    self._active_colour_names = {name}
    self._draw_colour_browser()
    self.status.set(
        f"Colour '{name}' bijgewerkt · {len(self.base_colours)} kleur(en) · "
        f"tolerance {self.colour_tolerance.get()}%."
    )


def install_manual_colour_save() -> None:
    global _ORIGINAL_BUILD_COLOUR_BROWSER
    _ORIGINAL_BUILD_COLOUR_BROWSER = _BROWSER_CLASS._build_colour_browser
    _BROWSER_CLASS._build_colour_browser = _build_colour_browser_manual
    _BROWSER_CLASS._new_colour_from_browser = _new_colour_from_browser_manual
    _BROWSER_CLASS._pick = _pick_manual
    _BROWSER_CLASS._save_colour_from_browser = _save_colour_from_browser


__all__ = ["install_manual_colour_save"]
