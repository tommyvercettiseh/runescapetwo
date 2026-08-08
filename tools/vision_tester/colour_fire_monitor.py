from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.colour_detection import build_mask_from_ranges, count_mask_pixels
from core.vision.colour_presets import load_colour_preset

from . import unified_plus


FIRE_MIN_PIXELS = 3


class ColourFireMonitorPage(unified_plus.ToleranceColourPage):
    """Explain which selected saved colour presets fire and how to fix overlap."""

    def __init__(self, parent):
        self.fire_state_text = tk.StringVar(value="Selecteer colours om te testen")
        self.fire_advice_text = tk.StringVar(
            value="Ctrl+klik meerdere colours. Ideaal firet op ieder frame exact één colour."
        )
        self.fire_table = None
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_fire_monitor()

    def _add_fire_monitor(self) -> None:
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        monitor = ttk.LabelFrame(toolbar, text="Colour overlap diagnosis", padding=(9, 7))
        monitor.grid(row=2, column=0, columnspan=6, sticky="ew", padx=8, pady=(5, 0))
        monitor.columnconfigure(0, weight=1)

        self.fire_state_label = ttk.Label(
            monitor,
            textvariable=self.fire_state_text,
            font=("Segoe UI", 11, "bold"),
        )
        self.fire_state_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        table = ttk.Treeview(
            monitor,
            columns=("colour", "pixels", "status", "advice"),
            show="headings",
            height=4,
        )
        table.heading("colour", text="Colour")
        table.heading("pixels", text="Pixels")
        table.heading("status", text="Status")
        table.heading("advice", text="Wat betekent dit?")
        table.column("colour", width=190, anchor="w")
        table.column("pixels", width=70, anchor="center")
        table.column("status", width=95, anchor="center")
        table.column("advice", width=370, anchor="w")
        table.grid(row=1, column=0, sticky="ew")
        self.fire_table = table

        ttk.Label(
            monitor,
            textvariable=self.fire_advice_text,
            wraplength=980,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        ttk.Label(
            monitor,
            text=(
                f"Regel: vanaf {FIRE_MIN_PIXELS} matchende pixels = FIRE. "
                "Doel: exact één FIRE per frame; 0 = UNKNOWN, 2+ = OVERLAP."
            ),
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))

    def _read_scores(self) -> list[tuple[str, int]]:
        if self.capture is None:
            return []
        names = sorted(getattr(self, "_active_colour_names", set()), key=str.casefold)
        scores: list[tuple[str, int]] = []
        for name in names:
            try:
                preset = load_colour_preset(name)
                mask = build_mask_from_ranges(self.capture, preset.ranges)
                pixels = count_mask_pixels(mask)
            except (KeyError, ValueError, OSError):
                pixels = 0
            scores.append((name, pixels))
        return scores

    def _update_fire_monitor(self) -> None:
        table = getattr(self, "fire_table", None)
        if table is None:
            return

        for item in table.get_children():
            table.delete(item)

        if self.capture is None:
            self.fire_state_text.set("⚠ Geen frame beschikbaar")
            self.fire_advice_text.set("Capture live beeld of laad eerst een replay.")
            self._set_fire_label_warning(True)
            return

        scores = self._read_scores()
        if not scores:
            self.fire_state_text.set("Selecteer colours om te testen")
            self.fire_advice_text.set(
                "Ctrl+klik bijvoorbeeld green, yellow, orange en red. Daarna zie je per frame welke preset firet."
            )
            self._set_fire_label_warning(False)
            return

        firing = [(name, pixels) for name, pixels in scores if pixels >= FIRE_MIN_PIXELS]
        firing_names = {name for name, _ in firing}
        strongest_name = max(firing, key=lambda item: item[1])[0] if firing else None

        if len(firing) == 1:
            state = f"✅ OK — alleen {firing[0][0]} firet"
            advice = (
                "Dit frame is goed afgesteld: exact één colour firet. Speel verder door de replay en controleer "
                "vooral de overgangen naar de volgende HP-kleur."
            )
            warning = False
        elif not firing:
            state = "⚠ UNKNOWN — geen enkele colour firet"
            advice = (
                "Geen preset haalt de FIRE-drempel. Pauzeer op dit frame en kijk met de pipet of dit een nog "
                "ontbrekende HP-tint is. Is de tint al opgeslagen, verhoog dan voorzichtig de tolerance van die colour."
            )
            warning = True
        else:
            ranked_firing = sorted(firing, key=lambda item: item[1], reverse=True)
            overlap_names = " + ".join(name for name, _ in ranked_firing)
            weakest_name, weakest_pixels = ranked_firing[-1]
            strongest_pixels = ranked_firing[0][1]
            state = f"❌ OVERLAP — {overlap_names}"
            advice = (
                f"Begin met '{weakest_name}': die matcht zwakker ({weakest_pixels}px tegenover "
                f"{strongest_pixels}px voor de sterkste match). Selecteer die colour, verlaag tolerance een beetje, "
                "klik Save updated colour en test hetzelfde punt opnieuw met Reset Replay. Stop zodra exact één colour firet."
            )
            warning = True

        self.fire_state_text.set(state)
        self.fire_advice_text.set(advice)
        self._set_fire_label_warning(warning)

        for name, pixels in sorted(scores, key=lambda item: item[1], reverse=True):
            if name not in firing_names:
                status = "OFF"
                row_advice = "Goed: deze colour matcht dit frame niet."
            elif len(firing) == 1:
                status = "FIRE"
                row_advice = "Actieve state; dit is de enige match."
            elif name == strongest_name:
                status = "FIRE"
                row_advice = "Sterkste match, waarschijnlijk de bedoelde state."
            else:
                status = "OVERLAP"
                row_advice = "Matcht tegelijk; tolerance/range waarschijnlijk te breed."

            table.insert("", "end", values=(name, pixels, status, row_advice))

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
