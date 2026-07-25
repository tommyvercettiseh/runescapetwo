from __future__ import annotations

import cv2
import numpy as np

from .colours import ColourSettings
from .models import ColourBlob


def _non_negative_integer(value: int, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}")
    return value


def create_mask(
    screenshot_rgb: np.ndarray,
    settings: ColourSettings,
) -> np.ndarray:
    if screenshot_rgb.ndim != 3 or screenshot_rgb.shape[2] != 3:
        raise ValueError("Colour detection requires an RGB image")

    hsv = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in settings.ranges:
        current = cv2.inRange(
            hsv,
            np.asarray(lower, dtype=np.uint8),
            np.asarray(upper, dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask, current)
    return mask


def find_blobs(
    screenshot_rgb: np.ndarray,
    settings: ColourSettings,
    *,
    origin: tuple[int, int] = (0, 0),
    min_blob_px: int | None = None,
    padding_px: int | None = None,
) -> list[ColourBlob]:
    minimum = settings.min_blob_px if min_blob_px is None else min_blob_px
    padding = settings.padding_px if padding_px is None else padding_px
    minimum = _non_negative_integer(minimum, "min_blob_px", 1)
    padding = _non_negative_integer(padding, "padding_px")

    if (
        not isinstance(origin, tuple)
        or len(origin) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in origin
        )
    ):
        raise ValueError("origin must contain two integers")

    mask = create_mask(screenshot_rgb, settings)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask,
        connectivity=8,
    )
    origin_x, origin_y = origin
    blobs: list[ColourBlob] = []

    for label in range(1, count):
        x, y, width, height, pixel_count = map(int, stats[label])
        if pixel_count < minimum:
            continue

        component = np.where(
            labels[y : y + height, x : x + width] == label,
            255,
            0,
        ).astype(np.uint8)
        if padding:
            size = padding * 2 + 1
            component = cv2.erode(
                component,
                np.ones((size, size), dtype=np.uint8),
                iterations=1,
                borderType=cv2.BORDER_CONSTANT,
                borderValue=0,
            )

        local_y, local_x = np.where(component > 0)
        if local_x.size == 0:
            continue

        clickable_points = np.column_stack(
            (
                local_x + x + origin_x,
                local_y + y + origin_y,
            )
        ).astype(np.int32)
        clickable_points.flags.writeable = False
        blobs.append(
            ColourBlob(
                x=x + origin_x,
                y=y + origin_y,
                width=width,
                height=height,
                pixel_count=pixel_count,
                clickable_points=clickable_points,
            )
        )

    return sorted(blobs, key=lambda blob: blob.pixel_count, reverse=True)
