from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np

from core.vision.colour_detection import hsv_ranges_around, sample_hsv
from . import preset_ui
from .deep_zoom import ZoomImageView
from .enhanced_config import (
    MAX_ZOOM_PERCENT,
    MIN_ZOOM_PERCENT,
    PIPETTE_EDGE_PADDING,
    SAMPLE_SIZES,
)
from .screen_overlay import ScreenAreaOverlay
from .source_controls import SearchableSourceControls


class EnhancedColourPage(preset_ui.PresetColourPage):
    """Colour preset page with deep zoom, safe sampling and desktop area guides."""

    def __init__(self, parent) -> None:
        self.pipette_sample_size = tk.IntVar(master=parent, value=1)
        self._screen_area_overlay: ScreenAreaOverlay | None = None
        self._last_pipette_point: tuple[int, int] | None = None
        super().__init__(parent)

    def _build(self) -> None:
        self.configure(fg_color=preset_ui.BASIC_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_capture_toolbar()
        self._build_preset_bar()
        self._build_detection_controls()
        self._build_previews()

        ttk.Label(
            self,
            textvariable=self.status,
            anchor="w",
            relief="sunken",
            padding=(7, 3),
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

    def _build_capture_toolbar(self) -> None:
        toolbar = ttk.LabelFrame(self, text="Capture", padding=(10, 7))
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 5))
        toolbar.columnconfigure(0, weight=1)

        self.source = SearchableSourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew")

        ttk.Checkbutton(
            toolbar,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
        ).grid(row=0, column=1, padx=(18, 7))
        ttk.Button(toolbar, text="Capture", command=self._once).grid(
            row=0,
            column=2,
        )

    def _build_preset_bar(self) -> None:
        presetbar = ttk.LabelFrame(self, text="Colour preset", padding=(10, 7))
        presetbar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        presetbar.columnconfigure(1, weight=1)
        presetbar.columnconfigure(3, weight=1)

        ttk.Label(presetbar, text="Search").grid(row=0, column=0, sticky="w")
        ttk.Entry(presetbar, textvariable=self.preset_search).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(7, 14),
        )
        ttk.Label(presetbar, text="Current preset").grid(
            row=0,
            column=2,
            sticky="w",
        )
        self.preset_box = ttk.Combobox(
            presetbar,
            values=[preset_ui.DEFAULT_PRESET_NAME],
            textvariable=self.current_preset,
            width=24,
        )
        self.preset_box.grid(row=0, column=3, sticky="ew", padx=(7, 14))
        self.preset_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._preset_selected(self.current_preset.get()),
        )

        ttk.Button(
            presetbar,
            text="Load",
            command=self._load_current_preset,
        ).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(
            presetbar,
            text="New",
            command=self._new_preset,
        ).grid(row=0, column=5, padx=5)
        ttk.Button(
            presetbar,
            text="Save current preset",
            command=self._save_current_preset,
        ).grid(row=0, column=6, padx=5)
        ttk.Button(
            presetbar,
            text="Delete",
            command=self._delete_current_preset,
        ).grid(row=0, column=7, padx=(5, 0))

        ttk.Label(
            presetbar,
            textvariable=self.preset_summary,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            presetbar,
            text=preset_ui.PRESETS_PATH_LABEL,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(
            row=1,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(6, 0),
        )

    def _build_detection_controls(self) -> None:
        controls = ttk.LabelFrame(self, text="Detection", padding=(10, 7))
        controls.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        controls.columnconfigure(15, weight=1)

        ttk.Label(controls, text="Min blob px").grid(row=0, column=0)
        minimum_entry = ttk.Entry(
            controls,
            textvariable=self.minimum,
            width=7,
        )
        minimum_entry.grid(row=0, column=1, padx=(5, 10))
        minimum_entry.bind("<KeyRelease>", lambda _event: self._render())

        ttk.Label(controls, text="Max blob px").grid(row=0, column=2)
        maximum_entry = ttk.Entry(
            controls,
            textvariable=self.maximum,
            width=7,
        )
        maximum_entry.grid(row=0, column=3, padx=(5, 12))
        maximum_entry.bind("<KeyRelease>", lambda _event: self._render())

        self.pipette_button = ttk.Button(
            controls,
            text="Pipette",
            command=self._toggle_pipette,
        )
        self.pipette_button.grid(row=0, column=4, padx=(0, 5))

        ttk.Label(controls, text="Pipet px").grid(row=0, column=5, padx=(8, 3))
        ttk.Combobox(
            controls,
            values=SAMPLE_SIZES,
            textvariable=self.pipette_sample_size,
            state="readonly",
            width=3,
        ).grid(row=0, column=6, padx=(0, 5))

        self.move_colour_button = ttk.Button(
            controls,
            text="Move colour",
            command=lambda: self._start_colour_mouse_action(click=False),
        )
        self.move_colour_button.grid(row=0, column=7, padx=5)
        self.click_colour_button = ttk.Button(
            controls,
            text="Click colour",
            command=lambda: self._start_colour_mouse_action(click=True),
        )
        self.click_colour_button.grid(row=0, column=8, padx=5)

        self.trace_switch = ttk.Checkbutton(
            controls,
            text="Trace",
            variable=self.mouse_trace,
            command=self._trace_changed,
        )
        self.trace_switch.grid(row=0, column=9, padx=(10, 5))
        self.auto_switch = ttk.Checkbutton(
            controls,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
        )
        self.auto_switch.grid(row=0, column=10, padx=5)

        self.zoom_label = ttk.Label(
            controls,
            text=f"Zoom {self.zoom.get()}%",
        )
        self.zoom_label.grid(row=0, column=11, padx=(10, 4))
        self.zoom_slider = ttk.Scale(
            controls,
            from_=MIN_ZOOM_PERCENT,
            to=MAX_ZOOM_PERCENT,
            variable=self.zoom,
            command=self._zoom_changed,
            length=105,
        )
        self.zoom_slider.grid(row=0, column=12, padx=(0, 12))

        ttk.Label(controls, text="Live blob").grid(row=0, column=13)
        ttk.Label(
            controls,
            textvariable=self.blob_live_text,
            foreground=preset_ui.BASIC_GREEN,
        ).grid(row=0, column=14, padx=(5, 8))
        ttk.Label(
            controls,
            textvariable=self.blob_range_text,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(row=0, column=15, sticky="e")
        ttk.Button(
            controls,
            text="Reset range",
            command=self._reset_blob_history,
        ).grid(row=0, column=16, padx=(8, 0))

        self.blob_meter = preset_ui.BasicProgressbar(controls)
        self.blob_meter.grid(
            row=1,
            column=0,
            columnspan=17,
            sticky="ew",
            pady=(7, 0),
        )
        self.blob_meter.set(0)
        self._sync_zoom_state()

    def _build_previews(self) -> None:
        previews = ttk.Frame(self)
        previews.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 6))
        previews.rowconfigure(0, weight=1)
        previews.columnconfigure(0, weight=3, uniform="preview")
        previews.columnconfigure(1, weight=2, uniform="preview")
        previews.columnconfigure(2, weight=2, uniform="preview")

        specs = (
            ("Live area", "Pick a colour here with the pipette."),
            ("Binary mask", "Valid matching pixels are white."),
            ("Isolated colour", "Only matching colour pixels remain."),
        )
        for column, (title, subtitle) in enumerate(specs):
            frame = ttk.LabelFrame(previews, text=title, padding=5)
            frame.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 4, 0),
            )
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)
            ttk.Label(
                frame,
                text=subtitle,
                foreground=preset_ui.BASIC_MUTED,
            ).grid(row=0, column=0, sticky="w", pady=(0, 4))
            view = ZoomImageView(
                frame,
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
            view.grid(row=1, column=0, sticky="nsew")
            self.views.append(view)

        self.capture_view, self.mask_view, self.isolated_view = self.views
        self.capture_view.bind("<Button-1>", self._pick)

    def _draw_blob_overlay(self, _blob, _safe_bounds=None) -> np.ndarray:
        """Keep previews clean; the desktop overlay owns target guides."""
        return self.capture.copy()

    def _selected_sample_size(self) -> int:
        try:
            value = int(self.pipette_sample_size.get())
        except (TypeError, ValueError):
            return 1
        return value if value in SAMPLE_SIZES else 1

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette:
            return

        point = self.capture_view.image_coordinates(event.x, event.y)
        if point is None:
            return

        x, y = point
        height, width = self.capture.shape[:2]
        padding = PIPETTE_EDGE_PADDING
        if (
            x < padding
            or y < padding
            or x >= width - padding
            or y >= height - padding
        ):
            self.status.set(
                f"Pipet: kies binnen de groene schermrand ({padding}px padding)."
            )
            return

        sample_size = self._selected_sample_size()
        radius = sample_size // 2
        self.ranges = hsv_ranges_around(
            sample_hsv(self.capture, x, y, radius=radius),
            hue_tolerance=5,
            saturation_tolerance=40,
            value_tolerance=40,
        )
        self.current_blob_px = 0
        self.observed_min_px = None
        self.observed_max_px = None
        self.blob_range_text.set("MIN —   MAX —")
        self._last_pipette_point = (x, y)
        self.capture_view.set_marker(x, y, sample_size)
        self._render()
        self.capture_view.set_marker(x, y, sample_size)
        self._update_preset_summary()
        self.status.set(
            f"Colour sampled for preset: {self.current_preset.get()} "
            f"({sample_size}×{sample_size})."
        )

    def _capture(self) -> None:
        overlay = self._screen_area_overlay
        if overlay is not None and not overlay.capture_excluded:
            overlay.hide()
            self.update_idletasks()

        super()._capture()
        if self.capture is None:
            return

        if overlay is None:
            try:
                overlay = ScreenAreaOverlay(self.winfo_toplevel())
            except (tk.TclError, AttributeError):
                overlay = None
            self._screen_area_overlay = overlay

        if overlay is not None:
            overlay.show_region(self.capture_region)

    def deactivate(self) -> None:
        super().deactivate()
        if self._screen_area_overlay is not None:
            self._screen_area_overlay.hide()


__all__ = ["EnhancedColourPage"]
