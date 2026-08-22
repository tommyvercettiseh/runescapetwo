from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


SKILLING_AREA = "Skilling_Area"
MIN_SATURATION = 90
MIN_VALUE = 90

GREEN_HUE_RANGES = ((35, 90),)
RED_HUE_RANGES = ((0, 10), (170, 179))


@dataclass(frozen=True)
class SkillingReading:
    skilling: bool
    green_pixels: int
    red_pixels: int


def _count_hue_ranges(hue: np.ndarray, mask: np.ndarray, ranges) -> int:
    total = 0
    for low, high in ranges:
        total += int(np.count_nonzero(mask & (hue >= low) & (hue <= high)))
    return total


def classify_skilling_frame(frame_rgb: np.ndarray) -> SkillingReading:
    """Classify the skilling indicator.

    Rules are intentionally strict and simple:
    - any red pixel means NOT skilling;
    - otherwise any green pixel means skilling;
    - no red and no green also means NOT skilling.
    """
    if frame_rgb is None or frame_rgb.size == 0:
        return SkillingReading(False, 0, 0)

    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    candidate = (saturation >= MIN_SATURATION) & (value >= MIN_VALUE)

    green_pixels = _count_hue_ranges(hue, candidate, GREEN_HUE_RANGES)
    red_pixels = _count_hue_ranges(hue, candidate, RED_HUE_RANGES)

    if red_pixels > 0:
        return SkillingReading(False, green_pixels, red_pixels)

    return SkillingReading(green_pixels > 0, green_pixels, red_pixels)


__all__ = [
    "GREEN_HUE_RANGES",
    "MIN_SATURATION",
    "MIN_VALUE",
    "RED_HUE_RANGES",
    "SKILLING_AREA",
    "SkillingReading",
    "classify_skilling_frame",
]
