from __future__ import annotations

import time

from core import mouse_actions
from definitions.login.logout_state import (
    INTERFACE_SCREEN_CROSS_IMAGE,
    LOGOUT_AREA,
    LOGOUT_CLICK_HERE_IMAGE,
    LOGOUT_DOOR_UNSELECTED_IMAGE,
    LogoutState,
    get_logout_state,
)


DEFAULT_TIMEOUT_S = 30.0
POLL_INTERVAL_S = 0.40
SAME_STATE_RETRY_S = 5.0

CLICK_IMAGE_BY_STATE = {
    LogoutState.MENU_CLOSED: LOGOUT_DOOR_UNSELECTED_IMAGE,
    LogoutState.BLOCKED_BY_INTERFACE: INTERFACE_SCREEN_CROSS_IMAGE,
    LogoutState.READY_TO_LOGOUT: LOGOUT_CLICK_HERE_IMAGE,
}


def _click(
    image_name: str,
    bot_id: int,
    *,
    confirm_before_click: bool = True,
) -> bool:
    return bool(
        mouse_actions.click_image(
            image_name=image_name,
            area_name=LOGOUT_AREA,
            bot_id=bot_id,
            confirm_before_click=confirm_before_click,
        )
    )


def logout(
    bot_id: int = 1,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    poll_interval_s: float = POLL_INTERVAL_S,
    same_state_retry_s: float = SAME_STATE_RETRY_S,
) -> bool:
    """Log out through visually confirmed states only.

    The door is selected first when needed. If the logout button is hidden by
    another interface, ``Interface_ScreenCross`` is closed and the state is
    checked again. The explicit logout button is then clicked and success is
    confirmed only by the strong logged-out state.

    ``LogOut_Door_Unselected`` and ``LogOut_ClickHereToLogOut`` are not
    re-confirmed after moving the mouse because their visual state can change
    on hover. ``Interface_ScreenCross`` keeps the normal pre-click
    confirmation.
    """
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    previous_state: LogoutState | None = None
    handled_state: LogoutState | None = None
    last_click_at = float("-inf")
    retry_delay = max(0.0, float(same_state_retry_s))

    while time.monotonic() <= deadline:
        state = get_logout_state(bot_id)
        if state is LogoutState.LOGGED_OUT:
            return True

        if state is not previous_state:
            handled_state = None
            previous_state = state

        image_name = CLICK_IMAGE_BY_STATE.get(state)
        now = time.monotonic()
        may_retry_same_state = now - last_click_at >= retry_delay
        if image_name is not None and (
            handled_state is not state or may_retry_same_state
        ):
            _click(
                image_name,
                bot_id,
                confirm_before_click=(state is LogoutState.BLOCKED_BY_INTERFACE),
            )
            handled_state = state
            last_click_at = now

        # MENU_OPEN waits for a logout button or blocking interface to appear.
        # UNKNOWN never receives input.
        time.sleep(max(0.05, float(poll_interval_s)))

    return get_logout_state(bot_id) is LogoutState.LOGGED_OUT


__all__ = ["logout"]
