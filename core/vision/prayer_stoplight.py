from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "config" / "prayer_stoplight.json"

DEFAULT_PROFILE = {
    "area": "Prayer_Area",
    "min_saturation": 105,
    "min_value": 130,
    "min_colour_pixels": 3,
    "min_confidence": 0.52,
    "hue_ranges": {
        "green": [[39, 85]],
        "yellow": [[23, 38]],
        "orange": [[9, 22]],
        "red": [[0, 8], [170, 179]],
    },
    "safe_states": ["green", "yellow"],
    "low_states": ["orange", "red"],
}

STATES = ("green", "yellow", "orange", "red")


def load_prayer_stoplight_profile() -> dict:
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return DEFAULT_PROFILE.copy()

    if not isinstance(data, dict):
        return DEFAULT_PROFILE.copy()

    profile = DEFAULT_PROFILE.copy()
    profile.update(data)
    if not isinstance(profile.get("hue_ranges"), dict):
        profile["hue_ranges"] = DEFAULT_PROFILE["hue_ranges"]
    return profile


def save_prayer_stoplight_profile(profile: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class PrayerStoplightReading:
    state: str
    pixels: dict[str, int]
    coloured_pixels: int
    confidence: float

    @property
    def low(self) -> bool:
        profile = load_prayer_stoplight_profile()
        if self.state in profile.get("low_states", []):
            return True
        if self.state in profile.get("safe_states", []):
            return False
        raise ValueError("Prayer stoplight state is UNKNOWN")


def _count_hue_ranges(hue: np.ndarray, mask: np.ndarray, ranges) -> int:
    total = 0
    for item in ranges:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        low, high = int(item[0]), int(item[1])
        total += int(np.count_nonzero(mask & (hue >= low) & (hue <= high)))
    return total


def classify_prayer_frame(frame_rgb: np.ndarray) -> PrayerStoplightReading:
    profile = load_prayer_stoplight_profile()
    min_saturation = int(profile.get("min_saturation", 105))
    min_value = int(profile.get("min_value", 130))
    min_colour_pixels = int(profile.get("min_colour_pixels", 3))
    min_confidence = float(profile.get("min_confidence", 0.52))
    hue_ranges = profile.get("hue_ranges", {})

    if frame_rgb is None or frame_rgb.size == 0:
        return PrayerStoplightReading("unknown", {state: 0 for state in STATES}, 0, 0.0)

    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    candidate = (sat >= min_saturation) & (val >= min_value)

    pixels = {
        state: _count_hue_ranges(hue, candidate, hue_ranges.get(state, []))
        for state in STATES
    }
    coloured_pixels = sum(pixels.values())

    if coloured_pixels < min_colour_pixels:
        return PrayerStoplightReading("unknown", pixels, coloured_pixels, 0.0)

    winner, winner_pixels = max(pixels.items(), key=lambda item: item[1])
    confidence = winner_pixels / coloured_pixels if coloured_pixels else 0.0
    if winner_pixels < min_colour_pixels or confidence < min_confidence:
        return PrayerStoplightReading("unknown", pixels, coloured_pixels, confidence)

    return PrayerStoplightReading(winner, pixels, coloured_pixels, confidence)


__all__ = [
    "DEFAULT_PROFILE",
    "PrayerStoplightReading",
    "PROFILE_PATH",
    "STATES",
    "classify_prayer_frame",
    "load_prayer_stoplight_profile",
    "save_prayer_stoplight_profile",
]
