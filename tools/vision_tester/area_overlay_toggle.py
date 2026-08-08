from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .enhanced_colour_page import EnhancedColourPage
from .source_controls import SearchableSourceControls


class OverlayColourPage(EnhancedColourPage):
    """Colour page with explicit optional desktop area overlay behavior."""

    def _build_capture_toolbar(self) -> None:
        toolbar = ttk.LabelFrame(self, text="Capture", padding=(10, 7))
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 5))
        toolbar.columnconfigure(0, weight=1)

        self.source = SearchableSourceControls(
            toolbar,
            require_selection=True,
            overlay_changed=self._overlay_toggle_changed,
        )
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

    def _overlay_toggle_changed(self) -> None:
        overlay = self._screen_area_overlay
        if overlay is None:
            return
        if not self.source.show_area_overlay.get():
            overlay.hide()
            return
        if self.source.area.get().strip() and self.capture is not None:
            overlay.show_region(self.capture_region)

    def _capture(self) -> None:
        if not self.source.area.get().strip():
            if self._screen_area_overlay is not None:
                self._screen_area_overlay.hide()
            self.capture = None
            self.status.set("Selecteer eerst een area.")
            return

        super()._capture()
        if (
            self._screen_area_overlay is not None
            and not self.source.show_area_overlay.get()
        ):
            self._screen_area_overlay.hide()


def install_area_overlay_toggle() -> None:
    """Compatibility no-op; the feature is now implemented by OverlayColourPage."""


__all__ = ["OverlayColourPage", "install_area_overlay_toggle"]
