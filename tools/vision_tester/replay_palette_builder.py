from __future__ import annotations

from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, ttk

import cv2
import numpy as np

from core.vision.colour_detection import hsv_ranges_around
from core.vision.colour_presets import normalize_colour_name, save_colour_preset

from . import unified_plus


MAX_ANALYSE_FRAMES = 400
MIN_DYNAMIC_RANGE = 18
MIN_SATURATION = 70
MIN_VALUE = 135
HUE_BIN = 3
SAT_BIN = 16
VALUE_BIN = 16
MIN_BIN_PIXELS = 3
MAX_PALETTE_COLOURS = 40
AUTO_TOLERANCE = 12


def _evenly_spaced(items: list[Path], limit: int) -> list[Path]:
    if len(items) <= limit:
        return items
    indexes = np.linspace(0, len(items) - 1, limit, dtype=int)
    return [items[int(index)] for index in indexes]


def _hue_distance(a: int, b: int) -> int:
    diff = abs(int(a) - int(b))
    return min(diff, 180 - diff)


def _near_hsv(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return (
        _hue_distance(a[0], b[0]) <= 4
        and abs(a[1] - b[1]) <= 24
        and abs(a[2] - b[2]) <= 24
    )


def _analyse_frames(frame_paths: list[Path]) -> tuple[list[tuple[int, int, int]], dict[str, int]]:
    sampled = _evenly_spaced(frame_paths, MAX_ANALYSE_FRAMES)
    rgbs: list[np.ndarray] = []

    expected_shape = None
    for path in sampled:
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        if expected_shape is None:
            expected_shape = rgb.shape
        if rgb.shape != expected_shape:
            continue
        rgbs.append(rgb)

    if len(rgbs) < 2:
        return [], {"frames": len(rgbs), "dynamic_pixels": 0, "candidate_pixels": 0, "bins": 0}

    stack = np.stack(rgbs, axis=0)

    # A position is interesting when its RGB values change substantially over
    # the replay. Static UI/background pixels therefore disappear here.
    channel_range = stack.max(axis=0).astype(np.int16) - stack.min(axis=0).astype(np.int16)
    dynamic_mask = channel_range.max(axis=2) >= MIN_DYNAMIC_RANGE

    counter: Counter[tuple[int, int, int]] = Counter()
    candidate_pixels = 0

    for rgb in rgbs:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        vivid = (hsv[:, :, 1] >= MIN_SATURATION) & (hsv[:, :, 2] >= MIN_VALUE)
        mask = dynamic_mask & vivid
        pixels = hsv[mask]
        candidate_pixels += int(len(pixels))

        for h, s, v in pixels:
            key = (
                min(179, (int(h) // HUE_BIN) * HUE_BIN + HUE_BIN // 2),
                min(255, (int(s) // SAT_BIN) * SAT_BIN + SAT_BIN // 2),
                min(255, (int(v) // VALUE_BIN) * VALUE_BIN + VALUE_BIN // 2),
            )
            counter[key] += 1

    ranked = [(hsv, count) for hsv, count in counter.most_common() if count >= MIN_BIN_PIXELS]

    # Merge neighbouring quantised bins. Keep the strongest representative so
    # anti-aliased shades do not explode into hundreds of base colours.
    palette: list[tuple[int, int, int]] = []
    for hsv, _count in ranked:
        if any(_near_hsv(hsv, existing) for existing in palette):
            continue
        palette.append(hsv)
        if len(palette) >= MAX_PALETTE_COLOURS:
            break

    stats = {
        "frames": len(rgbs),
        "dynamic_pixels": int(np.count_nonzero(dynamic_mask)),
        "candidate_pixels": candidate_pixels,
        "bins": len(ranked),
    }
    return palette, stats


class ReplayPaletteBuilderPage(unified_plus.ToleranceColourPage):
    """Build one multi-base colour preset from the currently loaded raw replay."""

    def __init__(self, parent):
        self.palette_builder_text = tk.StringVar(value="")
        super().__init__(parent)

    def _add_recording_controls(self) -> None:
        super()._add_recording_controls()
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=5, sticky="e", padx=(0, 8))
        ttk.Button(
            controls,
            text="Build palette from replay",
            command=self._build_palette_from_replay,
        ).pack(side="left")
        ttk.Label(controls, textvariable=self.palette_builder_text).pack(side="left", padx=(8, 0))

    def _build_palette_from_replay(self) -> None:
        frames = list(getattr(self, "_replay_frames", []))
        if not frames:
            self.status.set("Laad eerst een RAW replay met Play Video.")
            return

        self._pause_replay()
        self.palette_builder_text.set("Analyseren…")
        self.update_idletasks()

        palette, stats = _analyse_frames(frames)
        if not palette:
            self.palette_builder_text.set("Geen palette")
            self.status.set(
                "Geen duidelijke cijferkleuren gevonden. Zorg dat de replay meerdere HP-stappen bevat."
            )
            return

        default_name = "hp_colours"
        name = simpledialog.askstring(
            "Save replay palette",
            "Naam van het palette:",
            initialvalue=default_name,
            parent=self.winfo_toplevel(),
        )
        if name is None:
            self.palette_builder_text.set(f"{len(palette)} colours gevonden")
            return

        try:
            name = normalize_colour_name(name)
        except ValueError:
            self.status.set("Palette niet opgeslagen: ongeldige naam.")
            return

        ranges = []
        for hsv in palette:
            ranges.extend(
                hsv_ranges_around(
                    hsv,
                    hue_tolerance=2,
                    saturation_tolerance=18,
                    value_tolerance=18,
                )
            )

        save_colour_preset(name, tuple(ranges))

        meta = unified_plus._load_meta()
        meta[name] = {
            "tolerance": AUTO_TOLERANCE,
            "colours": [list(colour) for colour in palette],
            "source": "replay_palette_builder",
            "frames_analysed": stats["frames"],
        }
        unified_plus._save_meta(meta)

        self.current_preset.set(name)
        self.base_colours = list(palette)
        self.colour_tolerance.set(AUTO_TOLERANCE)
        self._active_colour_names = {name}
        self._rebuild_ranges()
        if hasattr(self, "_draw_colour_browser"):
            self._draw_colour_browser()

        self.palette_builder_text.set(f"{len(palette)} colours")
        self.status.set(
            f"Palette '{name}' opgeslagen: {len(palette)} base colours uit "
            f"{stats['frames']} frames · {stats['dynamic_pixels']} dynamische posities · "
            f"{stats['candidate_pixels']} kandidaat-pixels."
        )


def install_replay_palette_builder() -> None:
    unified_plus.ToleranceColourPage = ReplayPaletteBuilderPage


__all__ = ["ReplayPaletteBuilderPage", "install_replay_palette_builder"]
