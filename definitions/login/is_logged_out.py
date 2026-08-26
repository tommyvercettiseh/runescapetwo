from __future__ import annotations

from core import vision


LOGOUT_AREA = "Bot_Area_Full"
LOGIN_DISCONNECTED_IMAGE = "Login_Disconnected"
LOGIN_PLAY_NOW_IMAGE = "Login_Play_Now"
LOGIN_WORLD_SELECTION_IMAGE = "Login_World_Selection"


def is_logged_out(bot_id: int = 1) -> bool:
    """Return True only when the login/home screen is strongly confirmed.

    ``Login_World_Selection`` is the anchor for the login screen, but on its
    own it is not a strong enough success signal. Require either ``Play Now``
    or ``Disconnected`` alongside it so actions cannot finish early on a
    stray/false-positive World Selection match.
    """
    world_selection_visible = vision.image_exists(
        LOGIN_WORLD_SELECTION_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    if not world_selection_visible:
        return False

    play_now_visible = vision.image_exists(
        LOGIN_PLAY_NOW_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    if play_now_visible:
        return True

    return vision.image_exists(
        LOGIN_DISCONNECTED_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )


__all__ = [
    "LOGOUT_AREA",
    "LOGIN_DISCONNECTED_IMAGE",
    "LOGIN_PLAY_NOW_IMAGE",
    "LOGIN_WORLD_SELECTION_IMAGE",
    "is_logged_out",
]
