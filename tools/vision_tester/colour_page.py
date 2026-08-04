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
from .colour_debug import dominant_colours, isolate_colour
from .common import COLOURS, FilterCombobox, LiveToggle, PreviewLabel, SourceBar


class ColourPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.live = tk.BooleanVar(value=False)
        self.pipette_active = tk.BooleanVar(value=False)
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
        self.debug_info = tk.StringVar(value="Topkleuren verschijnen na de eerste capture.")
        self.colour_swatches: list[tk.Frame] = []
        self._dominant_signature: tuple[tuple[int, int, int, int], ...] | None = None

        self._build()
        for variable in (self.minimum, self.maximum, self.h_tol, self.s_tol, self.v_tol):
            variable.trace_add("write", self._settings_changed)
        self.after(100, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self, style="Surface.TFrame", padding=(14, 12))
        top.pack(fill="x", padx=18, pady=(14, 10))
        self.source = SourceBar(top)
        self.source.pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(top, style="Surface.TFrame")
        actions.pack(side="right")
        self.live_button = LiveToggle(actions, variable=self.live, command=self._toggle)
        self.live_button.pack(side="left", padx=3)
        ttk.Button(actions, text="Capture", command=self._once, style="Accent.TButton").pack(side="left", padx=(7, 0))

        settings = ttk.LabelFrame(self, text="  Detectie-instellingen  ", padding=12, style="Card.TLabelframe")
        settings.pack(fill="x", padx=18, pady=(0, 10))
        ttk.Label(settings, text="PRESET ZOEKEN", style="SurfaceMuted.TLabel").grid(row=0, column=0, sticky="w")
        self.preset_box = FilterCombobox(settings, textvariable=self.name, width=25)
        self.preset_box.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.preset_box.bind("<<ComboboxSelected>>", lambda _event: self._load())
        ttk.Button(settings, text="Laden", command=self._load).grid(row=1, column=1, padx=3)
        ttk.Button(settings, text="Opslaan", command=self._save).grid(row=1, column=2, padx=3)
        ttk.Button(settings, text="Verwijderen", command=self._delete).grid(row=1, column=3, padx=3)
        self.pipette_button = ttk.Checkbutton(
            settings,
            text="PIPET",
            variable=self.pipette_active,
            command=self._toggle_pipette,
            style="Toggle.TCheckbutton",
        )
        self.pipette_button.grid(row=1, column=4, padx=(12, 8))

        fields = (
            ("Min blob px", self.minimum, 1, 50000),
            ("Max blob px", self.maximum, 0, 100000),
            ("Hue tol", self.h_tol, 0, 40),
            ("Sat tol", self.s_tol, 0, 255),
            ("Value tol", self.v_tol, 0, 255),
        )
        for index, (label, variable, low, high) in enumerate(fields, start=5):
            ttk.Label(settings, text=label.upper(), style="SurfaceMuted.TLabel").grid(row=0, column=index, sticky="w", padx=3)
            ttk.Spinbox(settings, from_=low, to=high, textvariable=variable, width=10).grid(
                row=1, column=index, padx=3
            )
        settings.columnconfigure(0, weight=1)
        self._refresh_presets()

        debug = ttk.LabelFrame(self, text="  Dominante kleuren  ", padding=10, style="Card.TLabelframe")
        debug.pack(fill="x", padx=18, pady=(0, 10))
        self.swatch_container = ttk.Frame(debug, style="Surface.TFrame")
        self.swatch_container.pack(fill="x")
        self.debug_label = ttk.Label(
            self.swatch_container,
            textvariable=self.debug_info,
            style="SurfaceMuted.TLabel",
        )
        self.debug_label.pack(anchor="w", pady=8)

        previews = ttk.Frame(self, padding=(14, 0, 14, 8))
        previews.pack(fill="both", expand=True)
        capture_frame = ttk.LabelFrame(previews, text="  Live area · klik om kleur te pakken  ", padding=6, style="Card.TLabelframe")
        capture_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.capture_view = PreviewLabel(capture_frame)
        self.capture_view.pack(fill="both", expand=True)
        self.capture_view.bind("<Button-1>", self._pick)

        mask_frame = ttk.LabelFrame(previews, text="  Binair masker  ", padding=6, style="Card.TLabelframe")
        mask_frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.mask_view = PreviewLabel(mask_frame)
        self.mask_view.pack(fill="both", expand=True)

        isolated_frame = ttk.LabelFrame(
            previews,
            text="Kleur geïsoleerd — alles zwart behalve geselecteerde pixels",
            padding=6,
            style="Card.TLabelframe",
        )
        isolated_frame.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        self.isolated_view = PreviewLabel(isolated_frame)
        self.isolated_view.pack(fill="both", expand=True)

        overlay_frame = ttk.LabelFrame(previews, text="  Geldige blobs · exacte pixels  ", padding=6, style="Card.TLabelframe")
        overlay_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=4, pady=4)
        self.overlay_view = PreviewLabel(overlay_frame, fallback_height=420)
        self.overlay_view.pack(fill="both", expand=True)
        for row in range(2):
            previews.rowconfigure(row, weight=1)
        for column in range(3):
            previews.columnconfigure(column, weight=1)

        ttk.Label(self, textvariable=self.status, padding=(20, 8), style="Muted.TLabel").pack(fill="x")

    def _refresh_presets(self) -> None:
        self.preset_box.set_options(list_colour_presets())

    def _toggle(self) -> None:
        if self.live.get():
            self.status.set("Live capture actief.")
        else:
            self.status.set("Live capture gepauzeerd.")

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

        self._update_colour_debug()
        if not self.ranges:
            blank = np.zeros(self.capture.shape[:2], dtype=np.uint8)
            black_rgb = np.zeros_like(self.capture)
            self.mask_view.show(cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB))
            self.isolated_view.show(black_rgb)
            self.overlay_view.show(self.capture)
            self.status.set(
                f"Bot {self.source.bot_id.get()} | {self.source.area.get()} | "
                "nog geen kleur geselecteerd"
            )
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

        selected_pixels = count_mask_pixels(mask)
        total_pixels = max(1, mask.size)
        self.mask_view.show(cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))
        self.isolated_view.show(isolate_colour(self.capture, mask))
        self.overlay_view.show(overlay)
        elapsed = (time.perf_counter() - started) * 1000.0
        self.status.set(
            f"Bot {self.source.bot_id.get()} | {self.source.area.get()} | "
            f"geselecteerde kleur {selected_pixels} px ({selected_pixels / total_pixels * 100.0:.2f}%) | "
            f"geldige blobs {len(blobs)} | {elapsed:.1f} ms"
        )

    def _update_colour_debug(self) -> None:
        if self.capture is None:
            return
        colours = dominant_colours(self.capture, limit=5)
        if not colours:
            self.debug_info.set("Geen kleuren gevonden.")
            return

        signature = tuple((*colour.rgb, colour.pixels) for colour in colours)
        if signature == self._dominant_signature:
            return
        self._dominant_signature = signature

        self.debug_info.set("")
        self.debug_label.pack_forget()
        for widget in self.colour_swatches:
            widget.destroy()
        self.colour_swatches.clear()

        for index, colour in enumerate(colours, start=1):
            card = tk.Frame(
                self.swatch_container,
                background=COLOURS["surface_raised"],
                highlightbackground=COLOURS["border"],
                highlightthickness=1,
            )
            card.pack(side="left", fill="x", expand=True, padx=(0 if index == 1 else 5, 5))
            swatch = tk.Frame(card, background=self._rgb_hex(colour.rgb), width=44, height=44)
            swatch.pack(side="left", padx=8, pady=8)
            swatch.pack_propagate(False)
            copy = tk.Frame(card, background=COLOURS["surface_raised"])
            copy.pack(side="left", fill="both", expand=True, pady=6)
            tk.Label(
                copy,
                text=f"#{index}  {colour.percentage:.1f}%",
                background=COLOURS["surface_raised"],
                foreground=COLOURS["text"],
                font=("Segoe UI Semibold", 10),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                copy,
                text=f"RGB {colour.rgb}\nHSV {colour.hsv}",
                background=COLOURS["surface_raised"],
                foreground=COLOURS["muted"],
                font=("Segoe UI", 8),
                anchor="w",
                justify="left",
            ).pack(fill="x")
            self.colour_swatches.append(card)

    @staticmethod
    def _rgb_hex(rgb: tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _toggle_pipette(self) -> None:
        self.capture_view.configure(cursor="crosshair" if self.pipette_active.get() else "")
        if self.pipette_active.get():
            self.status.set("Pipet blijft actief. Klik kleuren tot je het pipet zelf uitzet.")
        else:
            self.status.set("Pipet uitgeschakeld.")

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette_active.get():
            return
        x = int(event.x / max(self.capture_view.scale, 1e-9))
        y = int(event.y / max(self.capture_view.scale, 1e-9))
        height, width = self.capture.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return
        self.sample = sample_hsv(self.capture, x, y, radius=2)
        self._rebuild_ranges()
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
