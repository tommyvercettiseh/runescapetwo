from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from core.vision.colour_presets import HSVRange


@dataclass(frozen=True)
class DominantColour:
    hsv: tuple[int, int, int]
    rgb: tuple[int, int, int]
    pixels: int
    percentage: float


def editor_sample_from_ranges(ranges: tuple[HSVRange, ...]) -> tuple[int, int, int]:
    """Return a useful editable HSV centre for one or more stored ranges."""
    if not ranges:
        raise ValueError("At least one HSV range is required")

    saturation_low = min(lower[1] for lower, _upper in ranges)
    saturation_high = max(upper[1] for _lower, upper in ranges)
    value_low = min(lower[2] for lower, _upper in ranges)
    value_high = max(upper[2] for _lower, upper in ranges)

    low_wrap = next((item for item in ranges if item[0][0] == 0), None)
    high_wrap = next((item for item in ranges if item[1][0] == 179), None)
    if len(ranges) == 2 and low_wrap and high_wrap:
        hue_start = high_wrap[0][0]
        hue_end = low_wrap[1][0] + 180
        hue = int(round((hue_start + hue_end) / 2.0)) % 180
    else:
        hue_low = min(lower[0] for lower, _upper in ranges)
        hue_high = max(upper[0] for _lower, upper in ranges)
        hue = int(round((hue_low + hue_high) / 2.0))

    return (
        hue,
        int(round((saturation_low + saturation_high) / 2.0)),
        int(round((value_low + value_high) / 2.0)),
    )


def isolate_colour(screenshot_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Keep matching pixels in their original colour and make everything else black."""
    isolated = np.zeros_like(screenshot_rgb)
    isolated[mask > 0] = screenshot_rgb[mask > 0]
    return isolated


def filter_mask_by_blob_size(
    mask: np.ndarray,
    *,
    minimum_area_px: int,
    maximum_area_px: int | None,
) -> tuple[np.ndarray, int]:
    """Keep only connected colour regions inside the configured pixel range."""
    minimum = max(1, int(minimum_area_px))
    maximum = None if maximum_area_px is None else max(1, int(maximum_area_px))
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8),
        connectivity=8,
    )
    filtered = np.zeros(mask.shape, dtype=np.uint8)
    valid_count = 0
    for label in range(1, count):
        area_px = int(stats[label, cv2.CC_STAT_AREA])
        if area_px < minimum or (maximum is not None and area_px > maximum):
            continue
        filtered[labels == label] = 255
        valid_count += 1
    return filtered, valid_count


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
