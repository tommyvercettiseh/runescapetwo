from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import numpy as np

from core.vision.colour_detection import (
    blobs_from_mask,
    build_mask_from_ranges,
    count_mask_pixels,
    hsv_ranges_around,
    sample_hsv,
)
from core.vision.colour_presets import (
    HSVRange,
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    save_colour_preset,
)
from core.vision.screenshots import capture_area
from .common import PreviewLabel, SourceBar


class ColourPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.capture: np.ndarray | None = None
        self.region: tuple[int, int, int, int] | None = None
        self.sample: tuple[int, int, int] | None = None
        self.ranges: tuple[HSVRange, ...] = ()

        self.name = tk.StringVar()
        self.minimum = tk.IntVar(value=20)
        self.maximum = tk.IntVar(value=0)
        self.h_tol = tk.IntVar(value=5)
        self.s_tol = tk.IntVar(value=40)
        self.v_tol = tk.IntVar(value=40)
        self.status = tk.StringVar(value="Kies een area en kleurpreset, of gebruik het pipet.")

        self._build()
        for variable in (self.minimum, self.maximum, self.h_tol, self.s_tol, self.v_tol):
            variable.trace_add("write", self._settings_changed)
        self.after(100, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.source = SourceBar(top)
        self.source.pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(top, padding=8)
        actions.pack(side="right")
        self.live_button = ttk.Button(actions, text="Live", command=self._toggle)
        self.live_button.pack(side="left", padx=3)
        ttk.Button(actions, text="Eenmalig", command=self._once).pack(side="left", padx=3)

        settings = ttk.LabelFrame(self, text="Kleurdetectie", padding=8)
        settings.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Label(settings, text="Preset").grid(row=0, column=0, sticky="w")
        self.preset_box = ttk.Combobox(settings, textvariable=self.name, width=25)
        self.preset_box.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.preset_box.bind("<<ComboboxSelected>>", lambda _event: self._load())
        ttk.Button(settings, text="Laden", command=self._load).grid(row=1, column=1, padx=3)
        ttk.Button(settings, text="Opslaan", command=self._save).grid(row=1, column=2, padx=3)
        ttk.Button(settings, text="Verwijderen", command=self._delete).grid(row=1, column=3, padx=3)
        ttk.Button(settings, text="Pipet", command=self._enable_pipette).grid(row=1, column=4, padx=(12, 3))

        fields = (
            ("Min blob px", self.minimum, 1, 50000),
            ("Max blob px", self.maximum, 0, 100000),
            ("Hue tol", self.h_tol, 0, 40),
            ("Sat tol", self.s_tol, 0, 255),
            ("Value tol", self.v_tol, 0, 255),
        )
        for index, (label, variable, low, high) in enumerate(fields, start=5):
            ttk.Label(settings, text=label).grid(row=0, column=index, sticky="w", padx=3)
            ttk.Spinbox(settings, from_=low, to=high, textvariable=variable, width=10).grid(
                row=1, column=index, padx=3
            )
        settings.columnconfigure(0, weight=1)
        self._refresh_presets()

        previews = ttk.Frame(self, padding=(8, 0, 8, 8))
        previews.pack(fill="both", expand=True)
        capture_frame = ttk.LabelFrame(previews, text="Live area — klik hier met pipet", padding=4)
        capture_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.capture_view = PreviewLabel(capture_frame)
        self.capture_view.pack(fill="both", expand=True)
        self.capture_view.bind("<Button-1>", self._pick)

        mask_frame = ttk.LabelFrame(previews, text="Masker", padding=4)
        mask_frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.mask_view = PreviewLabel(mask_frame)
        self.mask_view.pack(fill="both", expand=True)

        overlay_frame = ttk.LabelFrame(previews, text="Geldige blobs + exacte pixels", padding=4)
        overlay_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.overlay_view = PreviewLabel(overlay_frame, fallback_height=420)
        self.overlay_view.pack(fill="both", expand=True)
        for row in range(2):
            previews.rowconfigure(row, weight=1)
        for column in range(2):
            previews.columnconfigure(column, weight=1)

        ttk.Label(self, textvariable=self.status, padding=(10, 5)).pack(fill="x")

    def _refresh_presets(self) -> None:
        self.preset_box["values"] = list_colour_presets()

    def _toggle(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")

    def _once(self) -> None:
        self.running = False
        self.live_button.configure(text="Live")
        self._capture()

    def _tick(self) -> None:
        if self.running:
            self._capture()
        self.after(100, self._tick)

    def _capture(self) -> None:
        started = time.perf_counter()
        try:
            self.capture, self.region = capture_area(
                self.source.area.get(), bot_id=self.source.bot_id.get()
            )
            self.capture_view.show(self.capture)
            self._render(started)
        except Exception as exc:
            self.running = False
            self.live_button.configure(text="Live")
            self.status.set(f"Fout: {exc}")

    def _render(self, started: float | None = None) -> None:
        if self.capture is None:
            return
        if not self.ranges:
            blank = np.zeros(self.capture.shape[:2], dtype=np.uint8)
            self.mask_view.show(cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB))
            self.overlay_view.show(self.capture)
            return
        started = time.perf_counter() if started is None else started
        mask = build_mask_from_ranges(self.capture, self.ranges)
        maximum = self.maximum.get() or None
        origin = (self.region[0], self.region[1]) if self.region else (0, 0)
        blobs = blobs_from_mask(
            mask,
            origin=origin,
            minimum_area_px=max(1, self.minimum.get()),
            maximum_area_px=maximum,
        )
        overlay = self.capture.copy()
        for index, blob in enumerate(blobs, start=1):
            x = blob.x - origin[0]
            y = blob.y - origin[1]
            cv2.rectangle(overlay, (x, y), (x + blob.width, y + blob.height), (40, 220, 90), 2)
            cv2.putText(
                overlay,
                f"#{index} {blob.area_px} px",
                (x, max(16, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (40, 220, 90),
                1,
                cv2.LINE_AA,
            )
        self.mask_view.show(cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))
        self.overlay_view.show(overlay)
        elapsed = (time.perf_counter() - started) * 1000.0
        self.status.set(
            f"Bot {self.source.bot_id.get()} | {self.source.area.get()} | "
            f"kleurpixels {count_mask_pixels(mask)} | blobs {len(blobs)} | {elapsed:.1f} ms"
        )

    def _enable_pipette(self) -> None:
        self.capture_view.configure(cursor="crosshair")
        self.status.set("Klik op de gewenste kleur in de live area.")

    def _pick(self, event) -> None:
        if self.capture is None or str(self.capture_view.cget("cursor")) != "crosshair":
            return
        x = int(event.x / max(self.capture_view.scale, 1e-9))
        y = int(event.y / max(self.capture_view.scale, 1e-9))
        height, width = self.capture.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return
        self.sample = sample_hsv(self.capture, x, y, radius=2)
        self._rebuild_ranges()
        self.capture_view.configure(cursor="")
        self._render()

    def _settings_changed(self, *_args) -> None:
        if self.sample is not None:
            self._rebuild_ranges()
        self._render()

    def _rebuild_ranges(self) -> None:
        if self.sample is None:
            return
        self.ranges = hsv_ranges_around(
            self.sample,
            hue_tolerance=self.h_tol.get(),
            saturation_tolerance=self.s_tol.get(),
            value_tolerance=self.v_tol.get(),
        )

    def _load(self) -> None:
        try:
            preset = load_colour_preset(self.name.get())
            self.name.set(preset.name)
            self.ranges = preset.ranges
            self.sample = None
            self._render()
        except Exception as exc:
            self.status.set(str(exc))

    def _save(self) -> None:
        if not self.name.get().strip() or not self.ranges:
            messagebox.showerror("Preset", "Geef een naam en kies eerst een kleur met het pipet.")
            return
        try:
            save_colour_preset(self.name.get(), self.ranges)
            self.name.set(self.name.get().strip().lower())
            self._refresh_presets()
            self.status.set(f"Preset '{self.name.get()}' opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))

    def _delete(self) -> None:
        try:
            if delete_colour_preset(self.name.get()):
                self.name.set("")
                self.ranges = ()
                self._refresh_presets()
                self._render()
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))
