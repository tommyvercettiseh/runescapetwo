from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from core.vision.colour_detection import hsv_ranges_around, sample_hsv

from . import preset_ui
from .colour_view_cleanup import CompactColourPage
from .enhanced_config import PIPETTE_EDGE_PADDING


DEFAULT_TOLERANCE = 35
META_PATH = Path(__file__).resolve().parents[2] / "config" / "colour_preset_meta.json"


def tolerance_values(value: int) -> tuple[int, int, int]:
    """Translate one friendly 0..100 slider to HSV tolerances."""
    amount = min(100, max(0, int(value))) / 100.0
    hue = 1 + round(14 * amount)
    saturation = 8 + round(92 * amount)
    brightness = 8 + round(92 * amount)
    return hue, saturation, brightness


def _load_meta() -> dict[str, dict[str, object]]:
    try:
        data = json.loads(META_PATH.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_meta(data: dict[str, dict[str, object]]) -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = META_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temporary, META_PATH)


def _infer_base_colours(ranges) -> list[tuple[int, int, int]]:
    return [
        (
            round((int(lower[0]) + int(upper[0])) / 2),
            round((int(lower[1]) + int(upper[1])) / 2),
            round((int(lower[2]) + int(upper[2])) / 2),
        )
        for lower, upper in ranges
    ]


class ToleranceColourPage(CompactColourPage):
    """Multi-colour HSV page controlled by one friendly tolerance slider."""

    def __init__(self, parent) -> None:
        self.colour_tolerance = tk.IntVar(master=parent, value=DEFAULT_TOLERANCE)
        self.base_colours: list[tuple[int, int, int]] = []
        self.colour_count_text = tk.StringVar(master=parent, value="0 colours")
        self.tolerance_text = tk.StringVar(
            master=parent,
            value=f"{DEFAULT_TOLERANCE}%",
        )
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()

        for child in self.grid_slaves():
            info = child.grid_info()
            row = int(info.get("row", 0))
            if row >= 3:
                child.grid_configure(row=row + 1)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)

        bar = ttk.LabelFrame(self, text="Colour width", padding=(10, 7))
        bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        bar.columnconfigure(2, weight=1)

        ttk.Label(bar, text="Tolerance").grid(row=0, column=0, sticky="w")
        ttk.Label(bar, textvariable=self.tolerance_text, width=5).grid(
            row=0,
            column=1,
            padx=(7, 5),
        )
        self.tolerance_slider = ttk.Scale(
            bar,
            from_=0,
            to=100,
            variable=self.colour_tolerance,
            command=self._tolerance_changed,
            length=280,
        )
        self.tolerance_slider.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(0, 14),
        )

        ttk.Label(bar, textvariable=self.colour_count_text).grid(
            row=0,
            column=3,
            padx=(0, 8),
        )
        ttk.Button(
            bar,
            text="Remove last",
            command=self._remove_last_colour,
        ).grid(row=0, column=4, padx=4)
        ttk.Button(
            bar,
            text="Clear colours",
            command=self._clear_colours,
        ).grid(row=0, column=5, padx=(4, 0))
        ttk.Label(
            bar,
            text=(
                "Pipette adds a base colour. Slider widens/narrows "
                "all saved colours automatically."
            ),
            foreground=preset_ui.BASIC_MUTED,
        ).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(6, 0),
        )

    def _rebuild_ranges(self) -> None:
        hue, saturation, brightness = tolerance_values(
            self.colour_tolerance.get()
        )
        combined = []
        for hsv in self.base_colours:
            combined.extend(
                hsv_ranges_around(
                    hsv,
                    hue_tolerance=hue,
                    saturation_tolerance=saturation,
                    value_tolerance=brightness,
                )
            )
        self.ranges = tuple(combined)

        count = len(self.base_colours)
        self.colour_count_text.set(
            f"{count} colour" if count == 1 else f"{count} colours"
        )
        self.tolerance_text.set(f"{int(self.colour_tolerance.get())}%")
        self._update_preset_summary()
        self._reset_blob_history()
        self._render()

    def _tolerance_changed(self, value) -> None:
        self.colour_tolerance.set(round(float(value)))
        self._rebuild_ranges()

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
                f"Pipette: choose inside the safe area ({padding}px edge padding)."
            )
            return

        sample_size = self._selected_sample_size()
        radius = sample_size // 2
        hsv = sample_hsv(self.capture, x, y, radius=radius)
        if hsv not in self.base_colours:
            self.base_colours.append(hsv)

        self.capture_view.set_marker(x, y, sample_size)
        self._rebuild_ranges()
        self.status.set(
            f"Added colour {hsv} to {self.current_preset.get()} • "
            f"{len(self.base_colours)} base colour(s) • "
            f"tolerance {self.colour_tolerance.get()}%."
        )

    def _remove_last_colour(self) -> None:
        if self.base_colours:
            self.base_colours.pop()
            self._rebuild_ranges()
            self.status.set("Last base colour removed.")

    def _clear_colours(self) -> None:
        self.base_colours.clear()
        self.capture_view.clear_marker()
        self._rebuild_ranges()
        self.status.set("Base colours cleared.")

    def _load_current_preset(self) -> None:
        super()._load_current_preset()
        name = self.current_preset.get().strip()
        meta = _load_meta().get(name, {})
        colours = meta.get("colours") if isinstance(meta, dict) else None
        if isinstance(colours, list):
            self.base_colours = [
                tuple(int(value) for value in item)
                for item in colours
                if isinstance(item, list) and len(item) == 3
            ]
        else:
            self.base_colours = _infer_base_colours(self.ranges)

        try:
            tolerance = (
                int(meta.get("tolerance", DEFAULT_TOLERANCE))
                if isinstance(meta, dict)
                else DEFAULT_TOLERANCE
            )
        except (TypeError, ValueError):
            tolerance = DEFAULT_TOLERANCE
        self.colour_tolerance.set(min(100, max(0, tolerance)))
        self._rebuild_ranges()

    def _save_current_preset(self) -> None:
        self._rebuild_ranges()
        super()._save_current_preset()
        name = self.current_preset.get().strip()
        if not name or not self.base_colours:
            return

        data = _load_meta()
        data[name] = {
            "tolerance": int(self.colour_tolerance.get()),
            "colours": [list(colour) for colour in self.base_colours],
        }
        try:
            _save_meta(data)
        except OSError as exc:
            self.status.set(
                f"Preset saved, but colour metadata failed: {exc}"
            )

    def _new_preset(self) -> None:
        self.base_colours = []
        self.colour_tolerance.set(DEFAULT_TOLERANCE)
        self._rebuild_ranges()
        super()._new_preset()

    def _delete_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        super()._delete_current_preset()
        if name:
            data = _load_meta()
            if name in data:
                data.pop(name, None)
                try:
                    _save_meta(data)
                except OSError:
                    pass
        self.base_colours = []
        self._rebuild_ranges()


__all__ = [
    "DEFAULT_TOLERANCE",
    "ToleranceColourPage",
    "_infer_base_colours",
    "_load_meta",
    "_save_meta",
    "tolerance_values",
]
