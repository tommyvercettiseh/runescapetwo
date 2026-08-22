from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.sensors.prayer_stoplight import (
    classify_prayer_frame,
    load_prayer_stoplight_profile,
)

from .hp_stoplight_monitor import HpStoplightMonitorPage


STATE_COLOURS = {
    "green": "#53d769",
    "yellow": "#f4d03f",
    "orange": "#f39c12",
    "red": "#ff5b5b",
    "unknown": "#a7adb7",
}


class PrayerStoplightMonitorPage(HpStoplightMonitorPage):
    """Full colour operator page with live Prayer stoplight classification."""

    def __init__(self, parent) -> None:
        self.prayer_stoplight_state = tk.StringVar(master=parent, value="PRAYER: —")
        self.prayer_stoplight_px = tk.StringVar(master=parent, value="PX: 0")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_prayer_stoplight_monitor()

    def _add_prayer_stoplight_monitor(self) -> None:
        toolbar = self.source.master
        box = ttk.LabelFrame(toolbar, text="Prayer sensor", padding=(8, 6))
        box.grid(row=6, column=0, columnspan=7, sticky="ew", padx=8, pady=(5, 0))

        self.prayer_stoplight_label = ttk.Label(
            box,
            textvariable=self.prayer_stoplight_state,
            font=("Segoe UI", 11, "bold"),
        )
        self.prayer_stoplight_label.pack(side="left")
        ttk.Label(box, textvariable=self.prayer_stoplight_px).pack(
            side="left",
            padx=(14, 0),
        )

    def _update_prayer_stoplight(self) -> None:
        profile = load_prayer_stoplight_profile()
        prayer_area = str(profile.get("area", "Prayer_Area"))
        current_area = self.source.area.get().strip()

        if current_area != prayer_area:
            self.prayer_stoplight_state.set("PRAYER: —")
            self.prayer_stoplight_px.set(f"select {prayer_area}")
            self._set_prayer_colour("unknown")
            return

        if self.capture is None:
            self.prayer_stoplight_state.set("PRAYER: UNKNOWN")
            self.prayer_stoplight_px.set("PX: 0")
            self._set_prayer_colour("unknown")
            return

        reading = classify_prayer_frame(self.capture)
        winner_px = (
            reading.pixels.get(reading.state, 0)
            if reading.state != "unknown"
            else 0
        )
        self.prayer_stoplight_state.set(f"PRAYER: {reading.state.upper()}")
        self.prayer_stoplight_px.set(f"PX: {winner_px}")
        self._set_prayer_colour(reading.state)

    def _set_prayer_colour(self, state: str) -> None:
        self.prayer_stoplight_label.configure(
            foreground=STATE_COLOURS.get(state, STATE_COLOURS["unknown"])
        )

    def _render(self, started=None) -> None:
        super()._render(started)
        if hasattr(self, "prayer_stoplight_state"):
            self._update_prayer_stoplight()


def install_prayer_stoplight_monitor() -> None:
    """Compatibility no-op; use PrayerStoplightMonitorPage explicitly."""


__all__ = ["PrayerStoplightMonitorPage", "install_prayer_stoplight_monitor"]
