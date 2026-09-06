from __future__ import annotations

from typing import Literal

from core import vision


CompassDirection = Literal["north", "east", "south", "west"]
COMPASS_AREA = "Compass_Area"

COMPASS_IMAGES: dict[CompassDirection, str] = {
    "north": "Compass_North",
    "east": "Compass_East",
    "south": "Compass_South",
    "west": "Compass_West",
}


def is_compass_direction(
    direction: CompassDirection,
    *,
    bot_id: int = 1,
) -> bool:
    image_name = COMPASS_IMAGES[direction]
    return vision.find_image(
        image_name=image_name,
        area=COMPASS_AREA,
        bot_id=bot_id,
    ) is not None


def is_compass_north(bot_id: int = 1) -> bool:
    return is_compass_direction("north", bot_id=bot_id)


def is_compass_east(bot_id: int = 1) -> bool:
    return is_compass_direction("east", bot_id=bot_id)


def is_compass_south(bot_id: int = 1) -> bool:
    return is_compass_direction("south", bot_id=bot_id)


def is_compass_west(bot_id: int = 1) -> bool:
    return is_compass_direction("west", bot_id=bot_id)


def is_compass_north_missing(bot_id: int = 1) -> bool:
    return not is_compass_north(bot_id)


def is_compass_east_missing(bot_id: int = 1) -> bool:
    return not is_compass_east(bot_id)


def is_compass_south_missing(bot_id: int = 1) -> bool:
    return not is_compass_south(bot_id)


def is_compass_west_missing(bot_id: int = 1) -> bool:
    return not is_compass_west(bot_id)


__all__ = [
    "COMPASS_AREA",
    "COMPASS_IMAGES",
    "CompassDirection",
    "is_compass_direction",
    "is_compass_north",
    "is_compass_east",
    "is_compass_south",
    "is_compass_west",
    "is_compass_north_missing",
    "is_compass_east_missing",
    "is_compass_south_missing",
    "is_compass_west_missing",
]
