from __future__ import annotations

from core import vision


LOGOUT_AREA = "Bot_Area_Full"
LOGIN_DISCONNECTED_IMAGE = "Login_Disconnected"
LOGIN_WORLD_SELECTION_IMAGE = "Login_World_Selection"


def is_logged_out(bot_id: int = 1) -> bool:
    """Return True when a known logged-out screen is visible."""
    disconnected_visible = vision.image_exists(
        LOGIN_DISCONNECTED_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    world_selection_visible = vision.image_exists(
        LOGIN_WORLD_SELECTION_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    return disconnected_visible or world_selection_visible


__all__ = [
    "LOGOUT_AREA",
    "LOGIN_DISCONNECTED_IMAGE",
    "LOGIN_WORLD_SELECTION_IMAGE",
    "is_logged_out",
]
