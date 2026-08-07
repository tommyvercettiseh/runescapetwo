from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import enhanced_ui


_original_source_init = enhanced_ui.SearchableSourceControls.__init__
_original_capture = enhanced_ui.modern_ui.ColourPage._capture


def _find_colour_page(widget):
    current = widget
    while current is not None:
        if hasattr(current, "_screen_area_overlay") or hasattr(current, "capture"):
            if hasattr(current, "source"):
                return current
        current = getattr(current, "master", None)
    return None


def _overlay_toggle_changed(source) -> None:
    page = _find_colour_page(source)
    if page is None:
        return

    overlay = getattr(page, "_screen_area_overlay", None)
    if not source.show_area_overlay.get():
        if overlay is not None:
            overlay.hide()
        return

    # Turning it back on should only show something when an area was
    # deliberately selected and a valid capture region already exists.
    if source.area.get().strip() and overlay is not None:
        region = getattr(page, "capture_region", None)
        if region is not None:
            overlay.show_region(region)


def _source_init_with_overlay_toggle(
    self,
    parent,
    *,
    default_area=enhanced_ui.modern_ui.DEFAULT_AREA,
):
    _original_source_init(self, parent, default_area=default_area)

    # Start intentionally blank instead of silently selecting the first area.
    areas = list(getattr(self, "_areas", []))
    self.area_box.configure(values=["", *areas])
    self.area.set("")

    self.show_area_overlay = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        self,
        text="Show area overlay",
        variable=self.show_area_overlay,
        command=lambda: _overlay_toggle_changed(self),
    ).grid(row=0, column=6, sticky="w", padx=(14, 0))


def _capture_with_optional_overlay(self) -> None:
    area_name = ""
    try:
        area_name = self.source.area.get().strip()
    except (AttributeError, tk.TclError):
        pass

    overlay = getattr(self, "_screen_area_overlay", None)

    # No implicit/default area: wait until the user deliberately selects one.
    if not area_name:
        if overlay is not None:
            overlay.hide()
        self.capture = None
        try:
            self.status.set("Selecteer eerst een area.")
        except (AttributeError, tk.TclError):
            pass
        return

    show_overlay = True
    try:
        show_overlay = bool(self.source.show_area_overlay.get())
    except (AttributeError, tk.TclError):
        pass

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
