from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from core.vision.screenshots import capture_area

from . import ui
from .sensor_checks import SensorCheck, load_sensor_checks
from .sensor_view import analyse_sensor_frame, sensor_description


class SensorPage(ctk.CTkFrame):
    """Live sensor calibration page used by the production Vision Tester."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent")
        self.live = tk.BooleanVar(value=False)
        self.sensor_name = tk.StringVar()
        self.bot_id = tk.StringVar(value="1")
        self.status = tk.StringVar(value="Sensoren worden geladen.")
        self.description = tk.StringVar(value="Kies een sensor.")
        self.checks: dict[str, SensorCheck] = {}
        self._build()
        self._load()
        self.after(150, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live sensormeting actief.")
        self.after_idle(self._measure)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        toolbar = ui.card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)

        group = ctk.CTkFrame(toolbar, fg_color="transparent")
        group.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        ui.label(group, "SENSOR", muted=True, size=11).pack(anchor="w")
        self.sensor_box = ctk.CTkComboBox(
            group,
            variable=self.sensor_name,
            values=[],
            command=lambda _value: self._changed(),
            height=38,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            button_color=ui.BORDER,
            button_hover_color=ui.CONTROL_HOVER,
            text_color=ui.TEXT,
        )
        self.sensor_box.pack(fill="x", pady=(4, 0))

        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=16, pady=14)
        ctk.CTkOptionMenu(
            actions,
            values=["1", "2", "3", "4"],
            variable=self.bot_id,
            width=76,
            fg_color=ui.CARD_ALT,
            button_color=ui.BORDER,
            text_color=ui.TEXT,
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            progress_color=ui.ACCENT,
            text_color=ui.TEXT,
        ).grid(row=0, column=1, padx=(0, 10))
        ui.button(actions, "Meten", self._once, primary=True, width=100).grid(
            row=0,
            column=2,
        )

        desc = ui.card(self)
        desc.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        ui.label(
            desc,
            "",
            textvariable=self.description,
            size=12,
            wraplength=1200,
            justify="left",
        ).pack(anchor="w", padx=16, pady=12)

        previews = ctk.CTkFrame(self, fg_color="transparent")
        previews.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        previews.grid_rowconfigure(0, weight=1)
        previews.grid_columnconfigure(0, weight=1, uniform="sensor")
        previews.grid_columnconfigure(1, weight=1, uniform="sensor")
        self.views: list[ui.ImageView] = []
        for column, title in enumerate(("LIVE SENSOR AREA", "WAT DE SENSOR ZIET")):
            card = ui.card(previews)
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            ui.label(card, title, size=12, bold=True).pack(
                anchor="w",
                padx=14,
                pady=12,
            )
            view = ui.ImageView(card)
            view.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.views.append(view)
        self.live_view, self.detected_view = self.views

        result = ui.card(self)
        result.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.measurement = ui.label(result, "Nog niet gemeten", size=13)
        self.measurement.pack(side="left", padx=16, pady=12)
        self.outcome = ui.label(result, "—", size=20, bold=True)
        self.outcome.pack(side="right", padx=18, pady=10)

        status = ui.card(self)
        status.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))
        ui.label(
            status,
            "",
            textvariable=self.status,
            muted=True,
            size=11,
        ).pack(anchor="w", padx=14, pady=9)

    def _load(self) -> None:
        self.checks = {
            name: check
            for name, check in load_sensor_checks().items()
            if check.enabled
        }
        names = sorted(self.checks)
        self.sensor_box.configure(values=names)
        if names:
            self.sensor_name.set(names[0])
            self._changed()

    def _changed(self) -> None:
        check = self.checks.get(self.sensor_name.get())
        if check:
            self.description.set(sensor_description(check))
            self.status.set(
                f"Klaar voor meting: {check.name} gebruikt area '{check.area}'."
            )

    def _once(self) -> None:
        self.live.set(False)
        self._measure()

    def capture_hotkey(self) -> None:
        self._once()

    def _tick(self) -> None:
        if self.live.get():
            self._measure()
        self.after(150, self._tick)

    def _measure(self) -> None:
        check = self.checks.get(self.sensor_name.get())
        if not check:
            return

        started = time.perf_counter()
        try:
            screenshot, region = capture_area(
                check.area,
                bot_id=int(self.bot_id.get()),
            )
            frame = analyse_sensor_frame(
                screenshot,
                check,
                origin=(region[0], region[1]),
            )
            self.live_view.show(screenshot)
            self.detected_view.show(frame.detected)
            self.measurement.configure(
                text=(
                    f"Gevonden {frame.found} {frame.unit}  •  "
                    f"Benodigd {frame.required} {frame.unit}"
                )
            )
            self.outcome.configure(
                text="TRUE" if frame.result else "FALSE",
                text_color=ui.SUCCESS if frame.result else ui.DANGER,
            )
            elapsed = (time.perf_counter() - started) * 1000
            self.status.set(
                f"Bot {self.bot_id.get()}  •  {check.name}  •  {elapsed:.1f} ms"
            )
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")


__all__ = ["SensorPage"]
