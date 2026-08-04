from __future__ import annotations

import cv2
import numpy as np

from .colour_presets import HSV, HSVRange, load_colour_preset
from .models import ColourBlob
from .screenshots import capture_area


def build_mask_from_ranges(
    screenshot_rgb: np.ndarray,
    ranges: tuple[HSVRange, ...] | list[HSVRange],
    *,
    erode_px: int = 0,
    dilate_px: int = 0,
) -> np.ndarray:
    """Build one binary mask from one or more HSV ranges."""
    hsv = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2HSV)

    if not ranges:
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    else:
        first_lower, first_upper = ranges[0]
        mask = cv2.inRange(
            hsv,
            np.asarray(first_lower, dtype=np.uint8),
            np.asarray(first_upper, dtype=np.uint8),
        )
        for lower, upper in ranges[1:]:
            extra = cv2.inRange(
                hsv,
                np.asarray(lower, dtype=np.uint8),
                np.asarray(upper, dtype=np.uint8),
            )
            cv2.bitwise_or(mask, extra, dst=mask)

    if erode_px > 0:
        size = int(erode_px) * 2 + 1
        mask = cv2.erode(mask, np.ones((size, size), np.uint8), iterations=1)
    if dilate_px > 0:
        size = int(dilate_px) * 2 + 1
        mask = cv2.dilate(mask, np.ones((size, size), np.uint8), iterations=1)
    return mask


def build_colour_mask(
    screenshot_rgb: np.ndarray,
    colour: str,
    *,
    erode_px: int = 0,
    dilate_px: int = 0,
) -> np.ndarray:
    preset = load_colour_preset(colour)
    return build_mask_from_ranges(
        screenshot_rgb,
        preset.ranges,
        erode_px=erode_px,
        dilate_px=dilate_px,
    )


def count_mask_pixels(mask: np.ndarray) -> int:
    return int(cv2.countNonZero(mask))


def _binary_mask(mask: np.ndarray) -> np.ndarray:
    if mask.dtype == np.uint8:
        return mask
    return (mask > 0).astype(np.uint8)


def count_mask_components(mask: np.ndarray) -> int:
    count, _ = cv2.connectedComponents(_binary_mask(mask), connectivity=8)
    return max(0, int(count) - 1)


def _safe_point(
    component_mask: np.ndarray,
    *,
    origin_x: int,
    origin_y: int,
) -> tuple[int, int, float]:
    padded = cv2.copyMakeBorder(
        component_mask,
        1,
        1,
        1,
        1,
        cv2.BORDER_CONSTANT,
        value=0,
    )
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)
    _, radius, _, location = cv2.minMaxLoc(distance)
    local_x = min(max(int(location[0]) - 1, 0), component_mask.shape[1] - 1)
    local_y = min(max(int(location[1]) - 1, 0), component_mask.shape[0] - 1)
    return origin_x + local_x, origin_y + local_y, float(radius)


def blobs_from_mask(
    mask: np.ndarray,
    *,
    origin: tuple[int, int] = (0, 0),
    minimum_area_px: int = 20,
    maximum_area_px: int | None = None,
) -> list[ColourBlob]:
    """Return connected blobs with exact coloured-pixel counts."""
    minimum = max(1, int(minimum_area_px))
    maximum = None if maximum_area_px is None else max(1, int(maximum_area_px))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        _binary_mask(mask),
        connectivity=8,
    )

    origin_x, origin_y = origin
    blobs: list[ColourBlob] = []

    for label in range(1, count):
        area_px = int(stats[label, cv2.CC_STAT_AREA])
        if area_px < minimum:
            continue
        if maximum is not None and area_px > maximum:
            continue

        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        centroid_x = int(round(float(centroids[label, 0])))
        centroid_y = int(round(float(centroids[label, 1])))

        component = (labels[y : y + height, x : x + width] == label).astype(np.uint8)
        safe_x, safe_y, safe_radius = _safe_point(
            component,
            origin_x=origin_x + x,
            origin_y=origin_y + y,
        )

        blobs.append(
            ColourBlob(
                x=origin_x + x,
                y=origin_y + y,
                width=width,
                height=height,
                area_px=area_px,
                centroid_x=origin_x + centroid_x,
                centroid_y=origin_y + centroid_y,
                safe_x=safe_x,
                safe_y=safe_y,
                safe_radius=safe_radius,
            )
        )

    return sorted(blobs, key=lambda blob: blob.area_px, reverse=True)


def analyse_colour_image(
    screenshot_rgb: np.ndarray,
    colour: str,
    *,
    origin: tuple[int, int] = (0, 0),
    minimum_area_px: int = 20,
    maximum_area_px: int | None = None,
) -> tuple[np.ndarray, list[ColourBlob], int]:
    mask = build_colour_mask(screenshot_rgb, colour)
    blobs = blobs_from_mask(
        mask,
        origin=origin,
        minimum_area_px=minimum_area_px,
        maximum_area_px=maximum_area_px,
    )
    return mask, blobs, count_mask_pixels(mask)


def count_colour_pixels(
    colour: str,
    *,
    area: str | None = "game",
    bot_id: int | None = None,
) -> int:
    screenshot, _ = capture_area(area, bot_id=bot_id)
    return count_mask_pixels(build_colour_mask(screenshot, colour))


def colour_exists(
    colour: str,
    *,
    area: str | None = "game",
    bot_id: int | None = None,
    minimum_pixels: int = 1,
) -> bool:
    """Check total matching pixels; no blob-size rule is applied."""
    return count_colour_pixels(
        colour,
        area=area,
        bot_id=bot_id,
    ) >= max(1, int(minimum_pixels))


def find_colour_blobs(
    colour: str,
    *,
    area: str | None = "game",
    bot_id: int | None = None,
    minimum_area_px: int = 20,
    maximum_area_px: int | None = None,
) -> list[ColourBlob]:
    screenshot, region = capture_area(area, bot_id=bot_id)
    _, blobs, _ = analyse_colour_image(
        screenshot,
        colour,
        origin=(region[0], region[1]),
        minimum_area_px=minimum_area_px,
        maximum_area_px=maximum_area_px,
    )
    return blobs


def find_colour(colour: str, **kwargs) -> ColourBlob | None:
    blobs = find_colour_blobs(colour, **kwargs)
    return blobs[0] if blobs else None


def sample_hsv(
    screenshot_rgb: np.ndarray,
    x: int,
    y: int,
    *,
    radius: int = 2,
) -> HSV:
    """Sample a small patch robustly, including hues around red's wrap point."""
    height, width = screenshot_rgb.shape[:2]
    x = min(max(0, int(x)), width - 1)
    y = min(max(0, int(y)), height - 1)
    radius = max(0, int(radius))

    patch = screenshot_rgb[
        max(0, y - radius) : min(height, y + radius + 1),
        max(0, x - radius) : min(width, x + radius + 1),
    ]
    hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(np.int16)
    center_hue = int(
        cv2.cvtColor(
            screenshot_rgb[y : y + 1, x : x + 1],
            cv2.COLOR_RGB2HSV,
        )[0, 0, 0]
    )

    hue_delta = ((hsv[:, 0] - center_hue + 90) % 180) - 90
    hue = int(round((center_hue + float(np.median(hue_delta))) % 180))
    saturation = int(round(float(np.median(hsv[:, 1]))))
    value = int(round(float(np.median(hsv[:, 2]))))
    return hue, saturation, value


def hsv_ranges_around(
    hsv: HSV,
    *,
    hue_tolerance: int = 5,
    saturation_tolerance: int = 40,
    value_tolerance: int = 40,
) -> tuple[HSVRange, ...]:
    hue, saturation, value = hsv
    hue_tolerance = min(89, max(0, int(hue_tolerance)))
    saturation_tolerance = max(0, int(saturation_tolerance))
    value_tolerance = max(0, int(value_tolerance))

    lower_sv = (
        max(0, saturation - saturation_tolerance),
        max(0, value - value_tolerance),
    )
    upper_sv = (
        min(255, saturation + saturation_tolerance),
        min(255, value + value_tolerance),
    )

    low_hue = hue - hue_tolerance
    high_hue = hue + hue_tolerance
    if low_hue < 0:
        return (
            ((0, lower_sv[0], lower_sv[1]), (high_hue, upper_sv[0], upper_sv[1])),
            ((180 + low_hue, lower_sv[0], lower_sv[1]), (179, upper_sv[0], upper_sv[1])),
        )
    if high_hue > 179:
        return (
            ((low_hue, lower_sv[0], lower_sv[1]), (179, upper_sv[0], upper_sv[1])),
            ((0, lower_sv[0], lower_sv[1]), (high_hue - 180, upper_sv[0], upper_sv[1])),
        )
    return (
        (
            (low_hue, lower_sv[0], lower_sv[1]),
            (high_hue, upper_sv[0], upper_sv[1]),
        ),
    )
