from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


# HP digits are bright/saturated while the RuneScape UI behind them is mostly
# brown/grey and substantially less saturated. These gates deliberately remove
# the background before hue classification.
MIN_SATURATION = 105
MIN_VALUE = 130
MIN_COLOUR_PIXELS = 3
MIN_CONFIDENCE = 0.52

STATES = ("green", "yellow", "orange", "red")
LOW_STATES = {"orange", "red"}
SAFE_STATES = {"green", "yellow"}


@dataclass(frozen=True)
class HpStoplightReading:
    state: str
    pixels: dict[str, int]
    coloured_pixels: int
    confidence: float

    @property
    def low(self) -> bool:
        if self.state in LOW_STATES:
            return True
        if self.state in SAFE_STATES:
            return False
        raise ValueError("HP stoplight state is UNKNOWN")


def _count_hue(hue: np.ndarray, mask: np.ndarray, low: int, high: int) -> int:
    return int(np.count_nonzero(mask & (hue >= low) & (hue <= high)))


def classify_hp_frame(frame_rgb: np.ndarray) -> HpStoplightReading:
    """Classify bright HP-number pixels into a stoplight colour.

    The classifier does not depend on saved colour presets. It first discards
    low-saturation/dark UI pixels and then scores broad, non-overlapping OpenCV
    HSV hue zones. UNKNOWN is returned when there is not enough evidence.
    """

    if frame_rgb is None or frame_rgb.size == 0:
        return HpStoplightReading("unknown", {state: 0 for state in STATES}, 0, 0.0)

    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    candidate = (sat >= MIN_SATURATION) & (val >= MIN_VALUE)

    # OpenCV hue is 0..179. Zones are intentionally non-overlapping.
    # Red wraps around 0, hence its two ranges.
    red = _count_hue(hue, candidate, 0, 8) + _count_hue(hue, candidate, 170, 179)
    orange = _count_hue(hue, candidate, 9, 22)
    yellow = _count_hue(hue, candidate, 23, 38)
    green = _count_hue(hue, candidate, 39, 85)

    pixels = {
        "green": green,
        "yellow": yellow,
        "orange": orange,
        "red": red,
    }
    coloured_pixels = sum(pixels.values())

    if coloured_pixels < MIN_COLOUR_PIXELS:
        return HpStoplightReading("unknown", pixels, coloured_pixels, 0.0)

    winner, winner_pixels = max(pixels.items(), key=lambda item: item[1])
    confidence = winner_pixels / coloured_pixels if coloured_pixels else 0.0
    if winner_pixels < MIN_COLOUR_PIXELS or confidence < MIN_CONFIDENCE:
        return HpStoplightReading("unknown", pixels, coloured_pixels, confidence)

    return HpStoplightReading(winner, pixels, coloured_pixels, confidence)


__all__ = [
    "HpStoplightReading",
    "LOW_STATES",
    "MIN_COLOUR_PIXELS",
    "MIN_CONFIDENCE",
    "MIN_SATURATION",
    "MIN_VALUE",
    "SAFE_STATES",
    "STATES",
    "classify_hp_frame",
]
