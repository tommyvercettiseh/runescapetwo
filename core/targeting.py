from __future__ import annotations

import math
from typing import Protocol


class ColourBlobTarget(Protocol):
    x: int
    y: int
    width: int
    height: int
    safe_radius: float

    @property
    def safe_point(self) -> tuple[int, int]: ...


MIN_IMAGE_EDGE_PADDING = 20.0
MAX_IMAGE_EDGE_PADDING = 45.0
DEFAULT_BLOB_EDGE_PADDING = 20.0
MAX_BLOB_EDGE_PADDING = 45.0


def normalize_image_edge_padding(value: float) -> float:
    """Keep the horizontal image margin safe without collapsing the target."""
    return min(MAX_IMAGE_EDGE_PADDING, max(MIN_IMAGE_EDGE_PADDING, float(value)))


def validate_image_edge_padding(value: float) -> float:
    """Return a valid percentage or fail explicitly for script callers."""
    padding = float(value)
    if not MIN_IMAGE_EDGE_PADDING <= padding <= MAX_IMAGE_EDGE_PADDING:
        raise ValueError(
            "image_edge_padding must be between "
            f"{MIN_IMAGE_EDGE_PADDING:g} and {MAX_IMAGE_EDGE_PADDING:g}"
        )
    return padding


def image_target_bounds(
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    image_edge_padding: float = MIN_IMAGE_EDGE_PADDING,
) -> tuple[int, int, int, int]:
    """Return the central horizontal zone of an image bounding box.

    ``image_edge_padding`` is the percentage removed from both horizontal sides.
    """
    if right <= left or bottom <= top:
        raise ValueError("Target bounds must have positive width and height")

    padding = validate_image_edge_padding(image_edge_padding)
    width = right - left
    margin = max(1, int(round(width * padding / 100.0)))
    safe_left = left + margin
    safe_right = right - margin
    if safe_right <= safe_left:
        center = int(round((left + right) / 2.0))
        safe_left = max(left, center - 1)
        safe_right = min(right, center + 1)
    return safe_left, top, safe_right, bottom


def validate_blob_edge_padding(value: float) -> float:
    """Return a finite percentage that leaves a usable centre zone."""
    if isinstance(value, bool):
        raise TypeError("blob_edge_padding must be a percentage")
    try:
        padding = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("blob_edge_padding must be a percentage") from exc
    if not math.isfinite(padding) or not 0 <= padding <= MAX_BLOB_EDGE_PADDING:
        raise ValueError(
            "blob_edge_padding must be between 0 and "
            f"{MAX_BLOB_EDGE_PADDING:g} percent"
        )
    return padding


def colour_blob_target_bounds(
    blob: ColourBlobTarget,
    *,
    blob_edge_padding: float = DEFAULT_BLOB_EDGE_PADDING,
) -> tuple[int, int, int, int]:
    """Intersect percentage-padded bounds with a square inside the real blob."""
    padding = validate_blob_edge_padding(blob_edge_padding)
    safe_x, safe_y = blob.safe_point
    half_side = max(0, int(math.floor(float(blob.safe_radius) / math.sqrt(2.0))))
    safe_circle_square = (
        safe_x - half_side,
        safe_y - half_side,
        safe_x + half_side + 1,
        safe_y + half_side + 1,
    )
    horizontal_margin = int(math.ceil(blob.width * padding / 100.0))
    vertical_margin = int(math.ceil(blob.height * padding / 100.0))
    percentage_padded_bounds = (
        blob.x + horizontal_margin,
        blob.y + vertical_margin,
        blob.x + blob.width - horizontal_margin,
        blob.y + blob.height - vertical_margin,
    )
    left = max(safe_circle_square[0], percentage_padded_bounds[0])
    top = max(safe_circle_square[1], percentage_padded_bounds[1])
    right = min(safe_circle_square[2], percentage_padded_bounds[2])
    bottom = min(safe_circle_square[3], percentage_padded_bounds[3])
    if right <= left or bottom <= top:
        raise ValueError(
            "blob_edge_padding leaves no click zone safely inside the colour blob"
        )
    return left, top, right, bottom


def area_target_bounds(
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    area_edge_padding: int = 0,
) -> tuple[int, int, int, int]:
    """Return an area bounding box with an equal pixel margin on every side."""
    if right <= left or bottom <= top:
        raise ValueError("Target bounds must have positive width and height")
    validate_area_edge_padding(area_edge_padding)

    safe_left = left + area_edge_padding
    safe_top = top + area_edge_padding
    safe_right = right - area_edge_padding
    safe_bottom = bottom - area_edge_padding
    if safe_right <= safe_left or safe_bottom <= safe_top:
        raise ValueError("area_edge_padding leaves no usable target area")
    return safe_left, safe_top, safe_right, safe_bottom


def validate_area_edge_padding(area_edge_padding: int) -> int:
    """Validate a whole, non-negative pixel margin for script callers."""
    if isinstance(area_edge_padding, bool) or not isinstance(area_edge_padding, int):
        raise TypeError("area_edge_padding must be a whole number of pixels")
    if area_edge_padding < 0:
        raise ValueError("area_edge_padding cannot be negative")
    return area_edge_padding
