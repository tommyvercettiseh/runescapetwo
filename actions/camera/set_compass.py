from __future__ import annotations

import time

from core import mouse_actions
from definitions.camera.compass import (
    COMPASS_AREA,
    COMPASS_IMAGES,
    COMPASS_MENU_AREA,
    CompassDirection,
    is_compass_north,
)


COMPASS_CLICK_PADDING = 4
CONTEXT_MENU_DELAY_S = 0.15


def set_compass(
    direction: CompassDirection,
    *,
    bot_id: int = 1,
    via_menu: bool = False,
) -> bool:
    """Set the compass to a cardinal direction.

    North defaults to a normal left-click in Compass_Area because RuneScape
    resets the compass to north that way. Set ``via_menu=True`` to use the
    right-click menu for north too. East, south and west always use the menu.
    """
    if direction == "north" and not via_menu:
        if is_compass_north(bot_id=bot_id):
            return True

        clicked = mouse_actions.click_in_area(
            area_name=COMPASS_AREA,
            bot_id=bot_id,
            button="left",
            area_edge_padding=COMPASS_CLICK_PADDING,
        )
        if not clicked:
            return False

        return is_compass_north(bot_id=bot_id)

    opened = mouse_actions.click_in_area(
        area_name=COMPASS_AREA,
        bot_id=bot_id,
        button="right",
        area_edge_padding=COMPASS_CLICK_PADDING,
    )
    if not opened:
        return False

    time.sleep(CONTEXT_MENU_DELAY_S)

    selected = mouse_actions.click_image(
        image_name=COMPASS_IMAGES[direction],
        area_name=COMPASS_MENU_AREA,
        bot_id=bot_id,
        button="left",
        confirm_before_click=False,
    )
    if not selected:
        return False

    if direction == "north":
        return is_compass_north(bot_id=bot_id)

    return True


__all__ = ["set_compass"]
