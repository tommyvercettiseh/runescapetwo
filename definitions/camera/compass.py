from __future__ import annotations

from typing import Literal

from core import vision


CompassDirection = Literal["north", "east", "south", "west"]
COMPASS_AREA = "Compass_Area"
COMPASS_MENU_AREA = "Bot_Area_Full"
COMPASS_NORTH_CHECK_IMAGE = "Compass_NorthCheck"

COMPASS_IMAGES: dict[CompassDirection, str] = {
    "north": "Compass_North",
    "east": "Compass_East",
    "south": "Compass_South",
    "west": "Compass_West",
}


def is_compass_north(*, bot_id: int = 1) -> bool:
    """Return True only when the dedicated north-check template is visible."""
    return vision.find_image(
        image_name=COMPASS_NORTH_CHECK_IMAGE,
        area=COMPASS_AREA,
        bot_id=bot_id,
    ) is not None


def is_compass_direction(
    direction: CompassDirection,
    *,
    bot_id: int = 1,
) -> bool:
    """Legacy direction lookup kept for existing callers.

    North uses the dedicated Compass_NorthCheck sensor. Other directions still
    use their existing templates until dedicated check templates are added.
    """
    if direction == "north":
        return is_compass_north(bot_id=bot_id)

    image_name = COMPASS_IMAGES[direction]
    return vision.find_image(
        image_name=image_name,
        area=COMPASS_AREA,
        bot_id=bot_id,
    ) is not None


__all__ = [
    "COMPASS_AREA",
    "COMPASS_MENU_AREA",
    "COMPASS_NORTH_CHECK_IMAGE",
    "COMPASS_IMAGES",
    "CompassDirection",
    "is_compass_north",
    "is_compass_direction",
]
