from __future__ import annotations

from core.bots import get_bot_offset


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
    return x + int(ox), y + int(oy), width, height
