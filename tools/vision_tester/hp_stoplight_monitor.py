from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.hp_stoplight import classify_hp_frame

from . import unified_plus


class HpStoplightMonitorPage(unified_plus.ToleranceColourPage):
    """Show preset-free HP stoplight classification on the current frame."""

    def __init__(self, parent):
        self.hp_stoplight_state = tk.StringVar(value="HP STOPLIGHT: UNKNOWN")
        self.hp_stoplight_detail = tk.StringVar(value="Green 0 · Yellow 0 · Orange 0 · Red 0")
        self.hp_stoplight_help = tk.StringVar(value="Geen frame beschikbaar.")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_hp_stoplight_monitor()

    def _add_hp_stoplight_monitor(self) -> None:
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        box = ttk.LabelFrame(toolbar, text="HP stoplight detector", padding=(8, 6))
        box.grid(row=5, column=0, columnspan=7, sticky="ew", padx=8, pady=(5, 0))
        box.columnconfigure(1, weight=1)

        self.hp_stoplight_label = ttk.Label(
            box,
            textvariable=self.hp_stoplight_state,
            font=("Segoe UI", 10, "bold"),
        )
        self.hp_stoplight_label.grid(row=0, column=0, sticky="w")
        ttk.Label(box, textvariable=self.hp_stoplight_detail).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Label(box, textvariable=self.hp_stoplight_help).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

    def _update_hp_stoplight(self) -> None:
        if self.capture is None:
            self.hp_stoplight_state.set("HP STOPLIGHT: UNKNOWN")
            self.hp_stoplight_detail.set("Green 0 · Yellow 0 · Orange 0 · Red 0")
            self.hp_stoplight_help.set("Geen frame beschikbaar.")
            self._set_hp_warning(True)
            return

        reading = classify_hp_frame(self.capture)
        pixels = reading.pixels
        state = reading.state.upper()
        self.hp_stoplight_state.set(f"HP STOPLIGHT: {state}")
        self.hp_stoplight_detail.set(
            f"Green {pixels['green']} · Yellow {pixels['yellow']} · "
            f"Orange {pixels['orange']} · Red {pixels['red']} · "
            f"confidence {reading.confidence:.0%}"
        )

        if reading.state == "unknown":
            self.hp_stoplight_help.set(
                "UNKNOWN = te weinig duidelijke cijferpixels of grensgeval. Dit wordt nooit als veilig behandeld."
            )
            self._set_hp_warning(True)
        elif reading.state in ("orange", "red"):
            self.hp_stoplight_help.set("LOW = hp_low() retourneert True.")
            self._set_hp_warning(True)
        else:
            self.hp_stoplight_help.set("SAFE = hp_low() retourneert False.")
            self._set_hp_warning(False)

    def _set_hp_warning(self, warning: bool) -> None:
        label = getattr(self, "hp_stoplight_label", None)
        if label is None:
            return
        try:
            label.configure(foreground="#ff6b6b" if warning else "")
        except tk.TclError:
            pass

    def _render(self, started=None) -> None:
        super()._render(started)
        if hasattr(self, "hp_stoplight_state"):
            self._update_hp_stoplight()


def install_hp_stoplight_monitor() -> None:
    unified_plus.ToleranceColourPage = HpStoplightMonitorPage


__all__ = ["HpStoplightMonitorPage", "install_hp_stoplight_monitor"]
