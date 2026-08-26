from __future__ import annotations

from enum import Enum

from core import vision

from .is_logged_in import is_logged_in


LOGIN_AREA = "Bot_Area_Full"
LOGIN_CLICK_HERE_IMAGE = "Login_Click_Here_To_Play"
LOGIN_CONNECTING_IMAGE = "Login_Connecting_To_Server"
LOGIN_DISCONNECTED_IMAGE = "Login_Disconnected"
LOGIN_OK_IMAGE = "Login_OK"
LOGIN_PLAY_NOW_IMAGE = "Login_Play_Now"
LOGIN_WORLD_SELECTION_IMAGE = "Login_World_Selection"


class LoginState(str, Enum):
    LOGGED_IN = "logged_in"
    CLICK_HERE_TO_PLAY = "click_here_to_play"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    PLAY_NOW = "play_now"
    HOME = "home"
    UNKNOWN = "unknown"


def get_login_state(bot_id: int = 1) -> LoginState:
    """Return the current login stage without changing anything on screen."""
    if is_logged_in(bot_id):
        return LoginState.LOGGED_IN

    checks = (
        (LOGIN_CLICK_HERE_IMAGE, LoginState.CLICK_HERE_TO_PLAY),
        (LOGIN_DISCONNECTED_IMAGE, LoginState.DISCONNECTED),
        (LOGIN_CONNECTING_IMAGE, LoginState.CONNECTING),
        (LOGIN_PLAY_NOW_IMAGE, LoginState.PLAY_NOW),
        (LOGIN_WORLD_SELECTION_IMAGE, LoginState.HOME),
    )
    for image_name, state in checks:
        if vision.image_exists(image_name, area=LOGIN_AREA, bot_id=bot_id):
            return state

    return LoginState.UNKNOWN


__all__ = [
    "LOGIN_AREA",
    "LOGIN_CLICK_HERE_IMAGE",
    "LOGIN_CONNECTING_IMAGE",
    "LOGIN_DISCONNECTED_IMAGE",
    "LOGIN_OK_IMAGE",
    "LOGIN_PLAY_NOW_IMAGE",
    "LOGIN_WORLD_SELECTION_IMAGE",
    "LoginState",
    "get_login_state",
]
