from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np

from core.sensors.hp_stoplight import classify_hp_frame
from core.sensors.prayer_stoplight import (
    classify_prayer_frame,
    load_prayer_stoplight_profile,
)


STATE_COLOURS = {
    "green": "#55d66b",
    "yellow": "#e6d95c",
    "orange": "#f2a64a",
    "red": "#ff6b6b",
    "unknown": "#b8b8b8",
}


class StoplightPanel(ttk.LabelFrame):
    """Read-only HP and Prayer sensor feedback for the colour workspace."""

    def __init__(self, parent) -> None:
        super().__init__(parent, text="Sensors", padding=(10, 7))
        self.hp_state = tk.StringVar(master=self, value="HP: UNKNOWN")
        self.hp_pixels = tk.StringVar(master=self, value="PX: 0")
        self.prayer_state = tk.StringVar(master=self, value="PRAYER: —")
        self.prayer_pixels = tk.StringVar(master=self, value="PX: 0")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        hp = ttk.Frame(self)
        hp.grid(row=0, column=0, sticky="w")
        self.hp_label = ttk.Label(
            hp,
            textvariable=self.hp_state,
            font=("Segoe UI", 11, "bold"),
        )
        self.hp_label.pack(side="left")
        ttk.Label(hp, textvariable=self.hp_pixels).pack(side="left", padx=(14, 0))

        prayer = ttk.Frame(self)
        prayer.grid(row=0, column=1, sticky="w", padx=(24, 0))
        self.prayer_label = ttk.Label(
            prayer,
            textvariable=self.prayer_state,
            font=("Segoe UI", 11, "bold"),
        )
        self.prayer_label.pack(side="left")
        ttk.Label(prayer, textvariable=self.prayer_pixels).pack(
            side="left",
            padx=(14, 0),
        )

    def update_readings(
        self,
        capture: np.ndarray | None,
        *,
        current_area: str,
    ) -> None:
        self._update_hp(capture)
        self._update_prayer(capture, current_area=current_area)

    def _update_hp(self, capture: np.ndarray | None) -> None:
        if capture is None:
            state = "unknown"
            pixels = 0
        else:
            reading = classify_hp_frame(capture)
            state = reading.state
            pixels = (
                reading.pixels.get(state, 0)
                if state != "unknown"
                else reading.coloured_pixels
            )

        self.hp_state.set(f"HP: {state.upper()}")
        self.hp_pixels.set(f"PX: {pixels}")
        self.hp_label.configure(
            foreground=STATE_COLOURS.get(state, STATE_COLOURS["unknown"])
        )

    def _update_prayer(
        self,
        capture: np.ndarray | None,
        *,
        current_area: str,
    ) -> None:
        profile = load_prayer_stoplight_profile()
        prayer_area = str(profile.get("area", "Prayer_Area"))

        if current_area != prayer_area:
            self.prayer_state.set("PRAYER: —")
            self.prayer_pixels.set(f"select {prayer_area}")
            self._set_prayer_colour("unknown")
            return

        if capture is None:
            self.prayer_state.set("PRAYER: UNKNOWN")
            self.prayer_pixels.set("PX: 0")
            self._set_prayer_colour("unknown")
            return

        reading = classify_prayer_frame(capture)
        winner_px = (
            reading.pixels.get(reading.state, 0)
            if reading.state != "unknown"
            else 0
        )
        self.prayer_state.set(f"PRAYER: {reading.state.upper()}")
        self.prayer_pixels.set(f"PX: {winner_px}")
        self._set_prayer_colour(reading.state)

    def _set_prayer_colour(self, state: str) -> None:
        self.prayer_label.configure(
            foreground=STATE_COLOURS.get(state, STATE_COLOURS["unknown"])
        )


__all__ = ["StoplightPanel"]
