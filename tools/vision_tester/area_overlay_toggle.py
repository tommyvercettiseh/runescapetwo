from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import enhanced_ui


_original_source_init = enhanced_ui.SearchableSourceControls.__init__
_original_capture = enhanced_ui.modern_ui.ColourPage._capture


def _source_init_with_overlay_toggle(self, parent, *, default_area=enhanced_ui.modern_ui.DEFAULT_AREA):
    _original_source_init(self, parent, default_area=default_area)
    self.show_area_overlay = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        self,
        text="Show area overlay",
        variable=self.show_area_overlay,
    ).grid(row=0, column=6, sticky="w", padx=(14, 0))


def _capture_with_optional_overlay(self) -> None:
    show_overlay = True
    try:
        show_overlay = bool(self.source.show_area_overlay.get())
    except (AttributeError, tk.TclError):
        pass

    overlay = getattr(self, "_screen_area_overlay", None)
    if not show_overlay and overlay is not None:
        overlay.hide()

    _original_capture(self)

    overlay = getattr(self, "_screen_area_overlay", None)
    if overlay is None:
        return

    if show_overlay and self.capture is not None:
        overlay.show_region(self.capture_region)
    else:
        overlay.hide()


def install_area_overlay_toggle() -> None:
    if enhanced_ui.SearchableSourceControls.__init__ is not _source_init_with_overlay_toggle:
        enhanced_ui.SearchableSourceControls.__init__ = _source_init_with_overlay_toggle
        enhanced_ui.preset_ui.BasicSourceControls = enhanced_ui.SearchableSourceControls
    if enhanced_ui.modern_ui.ColourPage._capture is not _capture_with_optional_overlay:
        enhanced_ui.modern_ui.ColourPage._capture = _capture_with_optional_overlay


__all__ = ["install_area_overlay_toggle"]
