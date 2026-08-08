from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.colour_detection import build_mask_from_ranges, count_mask_pixels
from core.vision.colour_presets import load_colour_preset

from . import unified_plus


FIRE_MIN_PIXELS = 3


class ColourFireMonitorPage(unified_plus.ToleranceColourPage):
    """Show which selected saved colour presets fire on the current frame."""

    def __init__(self, parent):
        self.fire_state_text = tk.StringVar(value="FIRING: none")
        self.fire_detail_text = tk.StringVar(value="Selecteer colours met Ctrl+klik om overlap te controleren.")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_fire_monitor()

    def _add_fire_monitor(self) -> None:
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        monitor = ttk.LabelFrame(toolbar, text="Live colour firing", padding=(8, 5))
        monitor.grid(row=2, column=0, columnspan=6, sticky="ew", padx=8, pady=(5, 0))
        monitor.columnconfigure(1, weight=1)

        self.fire_state_label = ttk.Label(
            monitor,
            textvariable=self.fire_state_text,
            font=("Segoe UI", 10, "bold"),
        )
        self.fire_state_label.grid(row=0, column=0, sticky="w")

        ttk.Label(
            monitor,
            textvariable=self.fire_detail_text,
        ).grid(row=0, column=1, sticky="w", padx=(14, 0))

        ttk.Label(
            monitor,
            text=f"FIRE = minimaal {FIRE_MIN_PIXELS} matchende pixels per opgeslagen colour preset.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))

    def _update_fire_monitor(self) -> None:
        if self.capture is None:
            self.fire_state_text.set("FIRING: none")
            self.fire_detail_text.set("Geen frame beschikbaar.")
            return

        names = sorted(getattr(self, "_active_colour_names", set()), key=str.casefold)
        if not names:
            self.fire_state_text.set("FIRING: none")
            self.fire_detail_text.set("Selecteer colours met Ctrl+klik om overlap te controleren.")
            self._set_fire_label_warning(False)
            return

        scores: list[tuple[str, int]] = []
        for name in names:
            try:
                preset = load_colour_preset(name)
                mask = build_mask_from_ranges(self.capture, preset.ranges)
                pixels = count_mask_pixels(mask)
            except (KeyError, ValueError, OSError):
                pixels = 0
            scores.append((name, pixels))

        firing = [(name, pixels) for name, pixels in scores if pixels >= FIRE_MIN_PIXELS]
        details = "  |  ".join(
            f"{name}: {pixels}px{' FIRE' if pixels >= FIRE_MIN_PIXELS else ''}"
            for name, pixels in scores
        )
        self.fire_detail_text.set(details)

        if not firing:
            self.fire_state_text.set("FIRING: NONE / UNKNOWN")
            self._set_fire_label_warning(True)
        elif len(firing) == 1:
            self.fire_state_text.set(f"FIRING: {firing[0][0]}")
            self._set_fire_label_warning(False)
        else:
            names_text = " + ".join(name for name, _pixels in firing)
            self.fire_state_text.set(f"OVERLAP: {names_text}")
            self._set_fire_label_warning(True)

    def _set_fire_label_warning(self, warning: bool) -> None:
        label = getattr(self, "fire_state_label", None)
        if label is None:
            return
        try:
            label.configure(foreground="#ff6b6b" if warning else "")
        except tk.TclError:
            pass

    def _render(self, started=None) -> None:
        super()._render(started)
        if hasattr(self, "fire_state_text"):
            self._update_fire_monitor()


def install_colour_fire_monitor() -> None:
    unified_plus.ToleranceColourPage = ColourFireMonitorPage


__all__ = ["ColourFireMonitorPage", "install_colour_fire_monitor"]
