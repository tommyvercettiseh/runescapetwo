from __future__ import annotations

from core import mouse_actions
from definitions.camera.compass import (
    COMPASS_AREA,
    CompassDirection,
    is_compass_direction,
)


COMPASS_CLICK_PADDING = 4


def ensure_compass_direction(
    direction: CompassDirection,
    *,
    bot_id: int = 1,
) -> bool:
    """Ensure the compass is facing the requested cardinal direction.

    If the requested direction is already visible, nothing is clicked.
    Otherwise the compass area is clicked once and the direction is checked again.
    """
    if is_compass_direction(direction, bot_id=bot_id):
        return True

    click_result = mouse_actions.click_in_area(
        area_name=COMPASS_AREA,
        bot_id=bot_id,
        button="left",
        area_edge_padding=COMPASS_CLICK_PADDING,
    )
    if not click_result:
        return False

    return is_compass_direction(direction, bot_id=bot_id)


__all__ = ["ensure_compass_direction"]
