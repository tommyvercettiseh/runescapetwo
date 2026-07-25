from __future__ import annotations


def apply_offset(
    area: tuple[int, int, int, int] | None,
    offset: tuple[int, int] = (0, 0),
) -> tuple[int, int, int, int] | None:
    if area is None:
        return None
    x, y, width, height = area
    ox, oy = offset
    return x + int(ox), y + int(oy), width, height
