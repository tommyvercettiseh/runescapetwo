from __future__ import annotations

from core.bots import get_bot_offset, get_screen_size


def apply_offset(
    area: tuple[int, int, int, int],
    *,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
) -> tuple[int, int, int, int]:
    if bot_id is not None and offset is not None:
        raise ValueError("Use either bot_id or offset, not both")
    if offset is not None:
        if (
            not isinstance(offset, (tuple, list))
            or len(offset) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in offset
            )
        ):
            raise ValueError("offset must contain two integers")
        ox, oy = offset
    else:
        ox, oy = get_bot_offset(bot_id)

    x, y, width, height = area
    shifted = x + int(ox), y + int(oy), width, height
    screen_width, screen_height = get_screen_size()
    if (
        shifted[0] < 0
        or shifted[1] < 0
        or shifted[0] + width > screen_width
        or shifted[1] + height > screen_height
    ):
        raise ValueError("Offset area falls outside the configured screen")
    return shifted
