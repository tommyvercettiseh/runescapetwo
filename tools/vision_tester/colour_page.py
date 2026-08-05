from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageTk

from core.vision.colour_detection import (
    build_mask_from_ranges,
    count_mask_pixels,
    hsv_ranges_around,
    sample_hsv,
)
from core.vision.colour_presets import HSVRange
from core.vision.screenshots import capture_area
from .colour_debug import filter_mask_by_blob_size, isolate_colour
from .common import COLOURS, LiveToggle, PreviewLabel, SourceBar


class ColourPage(ttk.Frame):
    """Minimal live colour sampler with only the controls needed while tuning."""

    def __init__(self, parent):
        super().__init__(parent)
        self.live = tk.BooleanVar(value=False)
        self.pipette_active = tk.BooleanVar(value=False)
        self.capture: np.ndarray | None = None
        self.region: tuple[int, int, int, int] | None = None
        self.sample: tuple[int, int, int] | None = None
        self.ranges: tuple[HSVRange, ...] = ()

        self.minimum = tk.IntVar(value=20)
        self.maximum = tk.IntVar(value=0)
        self.status = tk.StringVar(value="Kies een area en maak een capture.")

        # The former HSV fields are deliberately hidden. These defaults keep the
        # same practical sampling behaviour when a colour is picked.
        self.hue_tolerance = 5
        self.saturation_tolerance = 40
        self.value_tolerance = 40

        self._build()
        for variable in (self.minimum, self.maximum):
            variable.trace_add("write", self._render_setting_changed)
        self.after(100, self._tick)

    def _build(self) -> None:
        toolbar = ttk.Frame(self, style="Surface.TFrame", padding=(16, 14))
        toolbar.pack(fill="x", padx=22, pady=(18, 12))
        self.source = SourceBar(toolbar)
        self.source.grid(row=0, column=0, sticky="ew", padx=(0, 22))

        fields = (
            ("MIN BLOB PX", self.minimum, 1, 50000),
            ("MAX BLOB PX", self.maximum, 0, 100000),
        )
        for column, (label, variable, low, high) in enumerate(fields, start=1):
            field = ttk.Frame(toolbar, style="Surface.TFrame")
            field.grid(row=0, column=column, sticky="sw", padx=(0, 10))
            ttk.Label(field, text=label, style="SurfaceMuted.TLabel").pack(anchor="w")
            ttk.Spinbox(
                field,
                from_=low,
                to=high,
                textvariable=variable,
                width=11,
            ).pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(toolbar, style="Surface.TFrame")
        actions.grid(row=0, column=3, sticky="se")
        ttk.Label(actions, text="KLEUR KIEZEN", style="SurfaceMuted.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        self._pipette_icon = self._make_pipette_icon()
        self.pipette_button = ttk.Button(
            actions,
            image=self._pipette_icon,
            command=self._toggle_pipette,
            style="Icon.TButton",
        )
        self.pipette_button.grid(row=1, column=0, padx=(0, 8), pady=(3, 0))
        self.live_button = LiveToggle(actions, variable=self.live, command=self._toggle)
        self.live_button.grid(row=1, column=1, padx=(0, 8), pady=(3, 0))
        ttk.Button(actions, text="CAPTURE", command=self._once, style="Accent.TButton").grid(
            row=1, column=2, pady=(3, 0)
        )

        toolbar.columnconfigure(0, weight=1)

        previews = ttk.Frame(self, padding=(18, 2, 18, 10))
        previews.pack(fill="both", expand=True)
        preview_specs = (
            ("LIVE AREA", "Klik met het pipet om een kleur te pakken"),
            ("BINAIR MASKER", "Wit is geselecteerd"),
            ("KLEUR GEÏSOLEERD", "Alleen de geselecteerde kleur blijft zichtbaar"),
        )
        views: list[PreviewLabel] = []
        for column, (title, subtitle) in enumerate(preview_specs):
            card = ttk.Frame(previews, style="Surface.TFrame", padding=(12, 11))
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            ttk.Label(card, text=title, style="Surface.TLabel", font=("Segoe UI Semibold", 11)).pack(
                anchor="w"
            )
            ttk.Label(card, text=subtitle, style="SurfaceMuted.TLabel").pack(
                anchor="w", pady=(2, 10)
            )
            view = PreviewLabel(card, fallback_width=650, fallback_height=650)
            view.pack(fill="both", expand=True)
            views.append(view)

        self.capture_view, self.mask_view, self.isolated_view = views
        self.capture_view.bind("<Button-1>", self._pick)
        previews.rowconfigure(0, weight=1)
        for column in range(3):
            previews.columnconfigure(column, weight=1, uniform="preview")

        status_bar = ttk.Frame(self, style="Surface.TFrame", padding=(18, 10))
        status_bar.pack(fill="x", padx=22, pady=(0, 18))
        self.colour_chip = tk.Frame(
            status_bar,
            width=18,
            height=18,
            background=COLOURS["surface_raised"],
            highlightbackground=COLOURS["border"],
            highlightthickness=1,
        )
        self.colour_chip.pack(side="left", padx=(0, 10))
        self.colour_chip.pack_propagate(False)
        ttk.Label(status_bar, textvariable=self.status, style="SurfaceMuted.TLabel").pack(
            side="left", fill="x", expand=True
        )

    @staticmethod
    def _make_pipette_icon() -> ImageTk.PhotoImage:
        """Draw a crisp pipette icon without an external icon dependency."""
        scale = 2
        image = Image.new("RGBA", (24 * scale, 24 * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        ink = (23, 67, 93, 255)
        accent = (66, 207, 232, 255)
        draw.rounded_rectangle(
            (13 * scale, 2 * scale, 20 * scale, 9 * scale),
            radius=2 * scale,
            fill=accent,
        )
        draw.line((16 * scale, 7 * scale, 7 * scale, 16 * scale), fill=ink, width=3 * scale)
        draw.line((12 * scale, 5 * scale, 19 * scale, 12 * scale), fill=ink, width=2 * scale)
        draw.polygon(
            ((7 * scale, 14 * scale), (10 * scale, 17 * scale), (4 * scale, 21 * scale)),
            fill=ink,
        )
        image = image.resize((24, 24), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def _toggle(self) -> None:
        self.status.set("Live capture actief." if self.live.get() else "Live capture gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._capture()

    def _tick(self) -> None:
        if self.live.get():
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
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _render(self, started: float | None = None) -> None:
        if self.capture is None:
            return

        if not self.ranges:
            blank = np.zeros(self.capture.shape[:2], dtype=np.uint8)
            self.mask_view.show(cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB))
            self.isolated_view.show(np.zeros_like(self.capture))
            self.status.set(
                f"Bot {self.source.bot_id.get()}  •  {self.source.area.get()}  •  kies een kleur met het pipet"
            )
            return

        started = time.perf_counter() if started is None else started
        mask = build_mask_from_ranges(self.capture, self.ranges)
        maximum = self.maximum.get() or None
        filtered_mask, valid_blob_count = filter_mask_by_blob_size(
            mask,
            minimum_area_px=max(1, self.minimum.get()),
            maximum_area_px=maximum,
        )

        selected_pixels = count_mask_pixels(filtered_mask)
        total_pixels = max(1, filtered_mask.size)
        self.mask_view.show(cv2.cvtColor(filtered_mask, cv2.COLOR_GRAY2RGB))
        self.isolated_view.show(isolate_colour(self.capture, filtered_mask))
        elapsed = (time.perf_counter() - started) * 1000.0
        self.status.set(
            f"Bot {self.source.bot_id.get()}  •  {self.source.area.get()}  •  "
            f"{selected_pixels} px geselecteerd ({selected_pixels / total_pixels * 100.0:.2f}%)  •  "
            f"{valid_blob_count} geldige blobs  •  {elapsed:.1f} ms"
        )

    def _toggle_pipette(self) -> None:
        active = not self.pipette_active.get()
        self.pipette_active.set(active)
        self.pipette_button.configure(style="IconActive.TButton" if active else "Icon.TButton")
        self.capture_view.configure(cursor="crosshair" if active else "")
        self.status.set(
            "Pipet actief. Klik een kleur in Live Area."
            if active
            else "Pipet uitgeschakeld."
        )

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette_active.get():
            return
        x = int(event.x / max(self.capture_view.scale, 1e-9))
        y = int(event.y / max(self.capture_view.scale, 1e-9))
        height, width = self.capture.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return
        self.sample = sample_hsv(self.capture, x, y, radius=2)
        self.ranges = hsv_ranges_around(
            self.sample,
            hue_tolerance=self.hue_tolerance,
            saturation_tolerance=self.saturation_tolerance,
            value_tolerance=self.value_tolerance,
        )
        hsv_pixel = np.array([[self.sample]], dtype=np.uint8)
        rgb = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2RGB)[0, 0]
        self.colour_chip.configure(
            background="#{:02x}{:02x}{:02x}".format(*(int(value) for value in rgb))
        )
        self._render()

    def _render_setting_changed(self, *_args) -> None:
        try:
            self.minimum.get()
            self.maximum.get()
        except tk.TclError:
            return
        self._render()
