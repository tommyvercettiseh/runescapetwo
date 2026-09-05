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


__all__ = [
    "COMPASS_AREA",
    "COMPASS_IMAGES",
    "CompassDirection",
    "is_compass_direction",
]
