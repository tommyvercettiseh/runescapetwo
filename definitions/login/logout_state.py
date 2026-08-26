from __future__ import annotations

from enum import Enum

from core import vision


LOGOUT_AREA = "Bot_Area_Full"
LOGOUT_CLICK_HERE_IMAGE = "LogOut_ClickHereToLogOut"
LOGOUT_DOOR_SELECTED_IMAGE = "LogOut_Door_Selected"
LOGOUT_DOOR_UNSELECTED_IMAGE = "LogOut_Door_Unselected"
LOGIN_WORLD_SELECTION_IMAGE = "Login_World_Selection"
INTERFACE_SCREEN_CROSS_IMAGE = "Interface_ScreenCross"


class LogoutState(str, Enum):
    LOGGED_OUT = "logged_out"
    READY_TO_LOGOUT = "ready_to_logout"
    BLOCKED_BY_INTERFACE = "blocked_by_interface"
    MENU_OPEN = "menu_open"
    MENU_CLOSED = "menu_closed"
    UNKNOWN = "unknown"


def get_logout_state(bot_id: int = 1) -> LogoutState:
    """Return the current logout stage without changing anything on screen."""
    if vision.image_exists(
        LOGIN_WORLD_SELECTION_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    ):
        return LogoutState.LOGGED_OUT

    if vision.image_exists(
        LOGOUT_CLICK_HERE_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    ):
        return LogoutState.READY_TO_LOGOUT

    selected = vision.image_exists(
        LOGOUT_DOOR_SELECTED_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    )
    if selected:
        if vision.image_exists(
            INTERFACE_SCREEN_CROSS_IMAGE,
            area=LOGOUT_AREA,
            bot_id=bot_id,
        ):
            return LogoutState.BLOCKED_BY_INTERFACE
        return LogoutState.MENU_OPEN

    if vision.image_exists(
        LOGOUT_DOOR_UNSELECTED_IMAGE,
        area=LOGOUT_AREA,
        bot_id=bot_id,
    ):
        return LogoutState.MENU_CLOSED

    return LogoutState.UNKNOWN


__all__ = [
    "INTERFACE_SCREEN_CROSS_IMAGE",
    "LOGIN_WORLD_SELECTION_IMAGE",
    "LOGOUT_AREA",
    "LOGOUT_CLICK_HERE_IMAGE",
    "LOGOUT_DOOR_SELECTED_IMAGE",
    "LOGOUT_DOOR_UNSELECTED_IMAGE",
    "LogoutState",
    "get_logout_state",
]
