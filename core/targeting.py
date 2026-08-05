from __future__ import annotations


MIN_IMAGE_EDGE_PADDING = 20.0
MAX_IMAGE_EDGE_PADDING = 45.0


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
