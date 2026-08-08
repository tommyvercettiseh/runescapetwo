from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.hp_stoplight import classify_hp_frame

from . import unified_plus


STATE_COLOURS = {
    "green": "#55d66b",
    "yellow": "#e6d95c",
    "orange": "#f2a64a",
    "red": "#ff6b6b",
    "unknown": "#b8b8b8",
}


class HpStoplightMonitorPage(unified_plus.ToleranceColourPage):
    """Compact preset-free HP stoplight classification on the current frame."""

    def __init__(self, parent):
        self.hp_stoplight_state = tk.StringVar(value="STOPLIGHT: UNKNOWN")
        self.hp_stoplight_px = tk.StringVar(value="PX: 0")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_hp_stoplight_monitor()

    def _add_hp_stoplight_monitor(self) -> None:
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        box = ttk.LabelFrame(toolbar, text="HP", padding=(10, 7))
        box.grid(row=5, column=0, columnspan=7, sticky="ew", padx=8, pady=(5, 0))

        self.hp_stoplight_label = ttk.Label(
            box,
            textvariable=self.hp_stoplight_state,
            font=("Segoe UI", 11, "bold"),
        )
        self.hp_stoplight_label.pack(side="left")

        ttk.Label(
            box,
            textvariable=self.hp_stoplight_px,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(18, 0))

    def _update_hp_stoplight(self) -> None:
        if self.capture is None:
            state = "unknown"
            pixels = 0
        else:
            reading = classify_hp_frame(self.capture)
            state = reading.state
            pixels = reading.pixels.get(state, 0) if state != "unknown" else reading.coloured_pixels

        self.hp_stoplight_state.set(f"STOPLIGHT: {state.upper()}")
        self.hp_stoplight_px.set(f"PX: {pixels}")

        label = getattr(self, "hp_stoplight_label", None)
        if label is not None:
            try:
                label.configure(foreground=STATE_COLOURS.get(state, STATE_COLOURS["unknown"]))
            except tk.TclError:
                pass

    def _render(self, started=None) -> None:
        super()._render(started)
        if hasattr(self, "hp_stoplight_state"):
            self._update_hp_stoplight()


def install_hp_stoplight_monitor() -> None:
    unified_plus.ToleranceColourPage = HpStoplightMonitorPage


__all__ = ["HpStoplightMonitorPage", "install_hp_stoplight_monitor"]
