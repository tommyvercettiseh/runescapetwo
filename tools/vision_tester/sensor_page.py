from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from core.vision.screenshots import capture_area

from .common import COLOURS, FilterCombobox, LiveToggle, PreviewLabel
from .sensor_checks import SensorCheck, load_sensor_checks
from .sensor_view import analyse_sensor_frame, sensor_description


class SensorPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.live = tk.BooleanVar(value=False)
        self.checks: dict[str, SensorCheck] = {}

        self.bot_id = tk.IntVar(value=1)
        self.sensor_name = tk.StringVar()
        self.description = tk.StringVar(value="Kies een sensor om te zien wat deze controleert.")
        self.found_text = tk.StringVar(value="Gevonden: —")
        self.required_text = tk.StringVar(value="Benodigd: —")
        self.result_text = tk.StringVar(value="NOG NIET GEMETEN")
        self.status = tk.StringVar(value="Sensoren worden geladen uit config/sensor_checks.json.")

        self._build()
        self._load_all()
        self.after(150, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self, padding=(14, 12), style="Surface.TFrame")
        top.pack(fill="x", padx=18, pady=(14, 10))

        sensor_group = ttk.Frame(top, style="Surface.TFrame")
        sensor_group.pack(side="left", fill="x", expand=True)
        ttk.Label(sensor_group, text="SENSOR ZOEKEN", style="SurfaceMuted.TLabel").pack(anchor="w")
        self.sensor_box = FilterCombobox(
            sensor_group,
            textvariable=self.sensor_name,
            width=36,
        )
        self.sensor_box.pack(anchor="w", fill="x", pady=(2, 0), padx=(0, 12))
        self.sensor_box.bind("<<ComboboxSelected>>", self._sensor_changed)

        bot_group = ttk.Frame(top, style="Surface.TFrame")
        bot_group.pack(side="left", padx=(0, 14))
        ttk.Label(bot_group, text="BOT", style="SurfaceMuted.TLabel").pack(anchor="w")
        bot_box = ttk.Combobox(
            bot_group,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=5,
        )
        bot_box.pack(pady=(2, 0))
        bot_box.bind("<<ComboboxSelected>>", lambda _event: self._once())

        self.live_button = LiveToggle(top, variable=self.live, command=self._toggle)
        self.live_button.pack(side="left", padx=3, pady=(15, 0))
        ttk.Button(top, text="Meten", command=self._once, style="Accent.TButton").pack(side="left", padx=(7, 3), pady=(15, 0))
        ttk.Button(top, text="↻", command=self._load_all, width=3).pack(side="left", padx=3, pady=(15, 0))

        intro = ttk.LabelFrame(self, text="  Detectieregel  ", padding=12, style="Card.TLabelframe")
        intro.pack(fill="x", padx=18, pady=(0, 10))
        ttk.Label(intro, textvariable=self.description, justify="left", wraplength=1100, style="Surface.TLabel").pack(anchor="w")

        previews = ttk.Frame(self, padding=(14, 0, 14, 6))
        previews.pack(fill="both", expand=True)

        live_frame = ttk.LabelFrame(previews, text="  01 · Live sensor-area  ", padding=6, style="Card.TLabelframe")
        live_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.live_view = PreviewLabel(live_frame, fallback_width=620, fallback_height=500)
        self.live_view.pack(fill="both", expand=True)

        detected_frame = ttk.LabelFrame(
            previews,
            text="  02 · Wat de sensor ziet  ",
            padding=6,
            style="Card.TLabelframe",
        )
        detected_frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.detected_view = PreviewLabel(detected_frame, fallback_width=620, fallback_height=500)
        self.detected_view.pack(fill="both", expand=True)

        previews.rowconfigure(0, weight=1)
        previews.columnconfigure(0, weight=1)
        previews.columnconfigure(1, weight=1)

        result = ttk.LabelFrame(self, text="  Uitkomst  ", padding=12, style="Card.TLabelframe")
        result.pack(fill="x", padx=18, pady=(0, 8))

        values = ttk.Frame(result, style="Surface.TFrame")
        values.pack(side="left", fill="x", expand=True)
        ttk.Label(values, textvariable=self.found_text, font=("Segoe UI", 12), style="Surface.TLabel").pack(anchor="w")
        ttk.Label(values, textvariable=self.required_text, font=("Segoe UI", 12), style="Surface.TLabel").pack(anchor="w", pady=(4, 0))

        self.result_label = ttk.Label(
            result,
            textvariable=self.result_text,
            font=("Segoe UI", 22, "bold"),
            anchor="center",
            width=18,
            style="Surface.TLabel",
        )
        self.result_label.pack(side="right", padx=16)

        ttk.Label(self, textvariable=self.status, padding=(20, 8), style="Muted.TLabel").pack(fill="x")

    def _load_all(self) -> None:
        try:
            self.checks = {
                name: check
                for name, check in load_sensor_checks().items()
                if check.enabled
            }
            names = sorted(self.checks)
            self.sensor_box.set_options(names)

            if self.sensor_name.get() not in self.checks:
                self.sensor_name.set(names[0] if names else "")

            if names:
                self._sensor_changed()
                self.status.set(f"{len(names)} actieve sensor(en) beschikbaar.")
            else:
                self.description.set(
                    "Nog geen actieve sensoren gevonden. Voeg ze toe in config/sensor_checks.json."
                )
                self._clear_result("GEEN SENSOREN")
        except Exception as exc:
            self.status.set(f"Configuratiefout: {exc}")
            self._clear_result("ERROR")

    def _selected_check(self) -> SensorCheck | None:
        return self.checks.get(self.sensor_name.get())

    def _sensor_changed(self, _event=None) -> None:
        check = self._selected_check()
        if check is None:
            self.description.set("Kies een bestaande sensor.")
            self._clear_result("NOG NIET GEMETEN")
            return
        self.description.set(sensor_description(check))
        self._clear_result("NOG NIET GEMETEN")
        self.status.set(
            f"Klaar voor meting: {check.name} gebruikt automatisch area '{check.area}'."
        )

    def _toggle(self) -> None:
        if not self._selected_check():
            self.live.set(False)
            self.status.set("Kies eerst een sensor.")
            return
        self.status.set("Live sensormeting actief." if self.live.get() else "Live sensormeting gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._measure()

    def _tick(self) -> None:
        if self.live.get():
            self._measure()
        self.after(150, self._tick)

    def _measure(self) -> None:
        check = self._selected_check()
        if check is None:
            return

        started = time.perf_counter()
        try:
            screenshot, region = capture_area(check.area, bot_id=self.bot_id.get())
            frame = analyse_sensor_frame(
                screenshot,
                check,
                origin=(region[0], region[1]),
            )
            self.live_view.show(screenshot)
            self.detected_view.show(frame.detected)
            self.found_text.set(f"Gevonden: {frame.found} {frame.unit}")
            self.required_text.set(f"Benodigd: {frame.required} {frame.unit}")
            self._set_result(frame.result)

            elapsed = (time.perf_counter() - started) * 1000.0
            self.status.set(
                f"Bot {self.bot_id.get()} | {check.name} | area {check.area} | {elapsed:.1f} ms"
            )
        except Exception as exc:
            self.live.set(False)
            self._clear_result("ERROR")
            self.status.set(f"Sensor '{check.name}' kan niet meten: {exc}")

    def _set_result(self, result: bool) -> None:
        self.result_text.set("TRUE" if result else "FALSE")
        self.result_label.configure(foreground=COLOURS["accent"] if result else COLOURS["danger"])

    def _clear_result(self, text: str) -> None:
        self.found_text.set("Gevonden: —")
        self.required_text.set("Benodigd: —")
        self.result_text.set(text)
        self.result_label.configure(foreground=COLOURS["muted"])
