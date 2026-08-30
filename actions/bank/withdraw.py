from __future__ import annotations

from core import mouse_actions


WITHDRAW_AREA = "Bot_Area"


def withdraw(
    image_name: str,
    bot_id: int = 1,
):
    return mouse_actions.click_image(
        image_name=image_name,
        area_name=WITHDRAW_AREA,
        bot_id=bot_id,
    )


__all__ = ["withdraw"]
