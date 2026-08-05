from __future__ import annotations


MIN_X_PADDING_PERCENT = 20.0
MAX_X_PADDING_PERCENT = 45.0


def normalize_x_padding_percent(value: float) -> float:
    """Keep the horizontal safe margin useful without collapsing the target."""
    return min(MAX_X_PADDING_PERCENT, max(MIN_X_PADDING_PERCENT, float(value)))


def horizontal_target_bounds(
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    x_padding_percent: float = MIN_X_PADDING_PERCENT,
) -> tuple[int, int, int, int]:
    """Return the central horizontal part of a detected image rectangle."""
    if right <= left or bottom <= top:
        raise ValueError("Target bounds must have positive width and height")

    percent = normalize_x_padding_percent(x_padding_percent)
    width = right - left
    margin = max(1, int(round(width * percent / 100.0)))
    safe_left = left + margin
    safe_right = right - margin
    if safe_right <= safe_left:
        center = int(round((left + right) / 2.0))
        safe_left = max(left, center - 1)
        safe_right = min(right, center + 1)
    return safe_left, top, safe_right, bottom
