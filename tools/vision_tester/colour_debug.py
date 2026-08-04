from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class DominantColour:
    hsv: tuple[int, int, int]
    rgb: tuple[int, int, int]
    pixels: int
    percentage: float


def isolate_colour(screenshot_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Keep matching pixels in their original colour and make everything else black."""
    isolated = np.zeros_like(screenshot_rgb)
    isolated[mask > 0] = screenshot_rgb[mask > 0]
    return isolated


def dominant_colours(
    screenshot_rgb: np.ndarray,
    *,
    limit: int = 5,
    hue_step: int = 6,
    saturation_step: int = 32,
    value_step: int = 32,
) -> list[DominantColour]:
    """Return stable dominant HSV colour groups instead of noisy exact RGB values."""
    if screenshot_rgb.size == 0 or limit <= 0:
        return []

    hsv = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2HSV)
    flat = hsv.reshape(-1, 3).astype(np.int32)

    hue_step = max(1, int(hue_step))
    saturation_step = max(1, int(saturation_step))
    value_step = max(1, int(value_step))

    quantized = np.column_stack(
        (
            flat[:, 0] // hue_step,
            flat[:, 1] // saturation_step,
            flat[:, 2] // value_step,
        )
    )
    bins, inverse, counts = np.unique(
        quantized,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    order = np.argsort(counts)[::-1][: int(limit)]
    total = max(1, flat.shape[0])
    result: list[DominantColour] = []

    for bin_index in order:
        members = flat[inverse == bin_index]
        median_hsv = tuple(int(round(float(value))) for value in np.median(members, axis=0))
        hsv_pixel = np.array([[median_hsv]], dtype=np.uint8)
        rgb = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2RGB)[0, 0]
        pixels = int(counts[bin_index])
        result.append(
            DominantColour(
                hsv=median_hsv,
                rgb=tuple(int(value) for value in rgb),
                pixels=pixels,
                percentage=(pixels / total) * 100.0,
            )
        )

    return result
