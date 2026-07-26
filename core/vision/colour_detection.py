from __future__ import annotations

import cv2
import numpy as np

from .areas import get_area
from .models import ColourBlob
from .offsets import apply_offset, resolve_offset
from .screenshots import capture_rgb

HSVRange = tuple[tuple[int, int, int], tuple[int, int, int]]

# Named defaults stay intentionally small and readable. Project-specific ranges
# can be added later without mixing colour logic into image detection.
COLOUR_RANGES: dict[str, tuple[HSVRange, ...]] = {
    "red": (
        ((0, 90, 70), (10, 255, 255)),
        ((170, 90, 70), (179, 255, 255)),
    ),
    "green": (((35, 60, 50), (85, 255, 255)),),
    "blue": (((90, 60, 50), (135, 255, 255)),),
    "cyan": (((80, 50, 60), (100, 255, 255)),),
    "yellow": (((20, 80, 80), (35, 255, 255)),),
    "orange": (((8, 90, 70), (22, 255, 255)),),
    "purple": (((135, 50, 40), (169, 255, 255)),),
    "pink": (((160, 45, 70), (179, 255, 255)),),
    "white": (((0, 0, 190), (179, 60, 255)),),
    "black": (((0, 0, 0), (179, 255, 45)),),
}

ALIASES = {
    "rood": "red",
    "groen": "green",
    "blauw": "blue",
    "cyaan": "cyan",
    "geel": "yellow",
    "oranje": "orange",
    "paars": "purple",
    "roze": "pink",
    "wit": "white",
    "zwart": "black",
}


def normalize_colour_name(colour: str) -> str:
    name = str(colour).strip().lower()
    name = ALIASES.get(name, name)
    if name not in COLOUR_RANGES:
        raise ValueError(f"Unknown colour: {colour}")
    return name


def build_colour_mask(
    screenshot_rgb: np.ndarray,
    colour: str,
    *,
    erode_px: int = 0,
    dilate_px: int = 0,
) -> np.ndarray:
    """Build a binary mask for one named colour."""
    name = normalize_colour_name(colour)
    hsv = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2HSV)

    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in COLOUR_RANGES[name]:
        mask |= cv2.inRange(
            hsv,
            np.array(lower, dtype=np.uint8),
            np.array(upper, dtype=np.uint8),
        )

    if erode_px > 0:
        size = int(erode_px) * 2 + 1
        mask = cv2.erode(mask, np.ones((size, size), np.uint8), iterations=1)
    if dilate_px > 0:
        size = int(dilate_px) * 2 + 1
        mask = cv2.dilate(mask, np.ones((size, size), np.uint8), iterations=1)
    return mask


def blobs_from_mask(
    mask: np.ndarray,
    *,
    origin: tuple[int, int] = (0, 0),
    minimum_area_px: float = 20.0,
    maximum_area_px: float | None = None,
) -> list[ColourBlob]:
    """Convert connected mask regions to absolute-screen blobs."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    origin_x, origin_y = origin
    blobs: list[ColourBlob] = []

    for contour in contours:
        area_px = float(cv2.contourArea(contour))
        if area_px < float(minimum_area_px):
            continue
        if maximum_area_px is not None and area_px > float(maximum_area_px):
            continue

        x, y, width, height = cv2.boundingRect(contour)
        moments = cv2.moments(contour)
        if moments["m00"]:
            centroid_x = int(moments["m10"] / moments["m00"])
            centroid_y = int(moments["m01"] / moments["m00"])
        else:
            centroid_x = x + width // 2
            centroid_y = y + height // 2

        blobs.append(
            ColourBlob(
                x=origin_x + x,
                y=origin_y + y,
                width=width,
                height=height,
                area_px=area_px,
                centroid_x=origin_x + centroid_x,
                centroid_y=origin_y + centroid_y,
            )
        )

    return sorted(blobs, key=lambda blob: blob.area_px, reverse=True)


def find_colour_blobs(
    colour: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    minimum_area_px: float = 20.0,
    maximum_area_px: float | None = None,
    erode_px: int = 0,
    dilate_px: int = 0,
) -> list[ColourBlob]:
    """Find colour blobs inside one local area for the selected bot."""
    resolved_offset = resolve_offset(bot_id=bot_id, offset=offset)
    region = apply_offset(get_area(area), resolved_offset)
    screenshot = capture_rgb(region)
    origin = (0, 0) if region is None else (region[0], region[1])
    mask = build_colour_mask(
        screenshot,
        colour,
        erode_px=erode_px,
        dilate_px=dilate_px,
    )
    return blobs_from_mask(
        mask,
        origin=origin,
        minimum_area_px=minimum_area_px,
        maximum_area_px=maximum_area_px,
    )


def find_colour(
    colour: str,
    **kwargs,
) -> ColourBlob | None:
    """Return the largest valid colour blob, or None."""
    blobs = find_colour_blobs(colour, **kwargs)
    return blobs[0] if blobs else None


def colour_exists(colour: str, **kwargs) -> bool:
    return find_colour(colour, **kwargs) is not None
