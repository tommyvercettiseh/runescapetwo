from __future__ import annotations

from core import vision


LOGOUT_AREA = "Bot_Area_Full"
LOGIN_DISCONNECTED_IMAGE = "Login_Disconnected"
LOGIN_PLAY_NOW_IMAGE = "Login_Play_Now"
LOGIN_WORLD_SELECTION_IMAGE = "Login_World_Selection"


def is_logged_out(bot_id: int = 1) -> bool:
    """Return True only for a strongly confirmed logged-out screen.

    ``Login_World_Selection`` alone is not sufficient because it can still be
    visible while the player is in-game. Require it together with a known
    login-screen action target.
    """
    world_selection_visible = vision.image_exists(
        LOGIN_WORLD_SELECTION_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    if not world_selection_visible:
        return False

    disconnected_visible = vision.image_exists(
        LOGIN_DISCONNECTED_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    play_now_visible = vision.image_exists(
        LOGIN_PLAY_NOW_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    return disconnected_visible or play_now_visible


__all__ = [
    "LOGOUT_AREA",
    "LOGIN_DISCONNECTED_IMAGE",
    "LOGIN_PLAY_NOW_IMAGE",
    "LOGIN_WORLD_SELECTION_IMAGE",
    "is_logged_out",
]
