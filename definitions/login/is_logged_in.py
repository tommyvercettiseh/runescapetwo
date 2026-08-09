from __future__ import annotations

from core import vision


LOGIN_AREA = "Info_Area"
LOGIN_EXP_IMAGE = "Login_Exp"
LOGIN_GLOBE_IMAGE = "Login_Globe"


def is_logged_in(bot_id: int = 1) -> bool:
    """Return True only when both logged-in HUD images are visible."""
    exp_visible = vision.image_exists(
        LOGIN_EXP_IMAGE,
        area=LOGIN_AREA,
        bot_id=bot_id,
    )
    globe_visible = vision.image_exists(
        LOGIN_GLOBE_IMAGE,
        area=LOGIN_AREA,
        bot_id=bot_id,
    )
    return exp_visible and globe_visible


__all__ = [
    "LOGIN_AREA",
    "LOGIN_EXP_IMAGE",
    "LOGIN_GLOBE_IMAGE",
    "is_logged_in",
]
