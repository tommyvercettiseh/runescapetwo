from __future__ import annotations

from core import vision


def has_image_in_area(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
) -> bool:
    """Return whether one named template is visible inside one named area."""
    return vision.image_exists(
        image_name,
        area=area_name,
        bot_id=bot_id,
    )


__all__ = ["has_image_in_area"]
