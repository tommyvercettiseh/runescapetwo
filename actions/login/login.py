from __future__ import annotations

import time

from core import mouse_actions
from definitions.login.is_logged_in import is_logged_in
from definitions.login.state import (
    LOGIN_AREA,
    LOGIN_CLICK_HERE_IMAGE,
    LOGIN_OK_IMAGE,
    LOGIN_PLAY_NOW_IMAGE,
    LoginState,
    get_login_state,
)


DEFAULT_TIMEOUT_S = 60.0
POLL_INTERVAL_S = 0.40
CLICK_RETRY_S = 1.00

CLICK_IMAGE_BY_STATE = {
    LoginState.DISCONNECTED: LOGIN_OK_IMAGE,
    LoginState.PLAY_NOW: LOGIN_PLAY_NOW_IMAGE,
    LoginState.CLICK_HERE_TO_PLAY: LOGIN_CLICK_HERE_IMAGE,
}


def _click(image_name: str, bot_id: int) -> bool:
    return bool(
        mouse_actions.click_image(
            image_name=image_name,
            area_name=LOGIN_AREA,
            bot_id=bot_id,
            confirm_before_click=True,
        )
    )


def login(
    bot_id: int = 1,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    poll_interval_s: float = POLL_INTERVAL_S,
) -> bool:
    """Move the current login screen forward until the player is logged in.

    The current screen is analysed every cycle. Transitional states such as
    Connecting to Server are deliberately left alone; the action only clicks
    buttons that are safe for the detected stage.
    """
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    next_click_at = 0.0

    while time.monotonic() <= deadline:
        state = get_login_state(bot_id)
        if state is LoginState.LOGGED_IN:
            return True

        image_name = CLICK_IMAGE_BY_STATE.get(state)
        now = time.monotonic()
        if image_name is not None and now >= next_click_at:
            _click(image_name, bot_id)
            next_click_at = now + CLICK_RETRY_S

        # CONNECTING, HOME and UNKNOWN intentionally do nothing here.
        time.sleep(max(0.05, float(poll_interval_s)))

    return is_logged_in(bot_id)


__all__ = ["login"]
