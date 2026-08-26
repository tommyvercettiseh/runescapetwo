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
SAME_STATE_RETRY_S = 5.0

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
    same_state_retry_s: float = SAME_STATE_RETRY_S,
) -> bool:
    """Move the current login screen forward until the player is logged in.

    Every cycle first determines the current screen. A newly reached actionable
    state may be clicked immediately. If the same state remains visible after a
    click, it is left alone for ``same_state_retry_s`` seconds before one retry.
    Transitional states such as Connecting to Server never receive input.
    """
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    previous_state: LoginState | None = None
    handled_state: LoginState | None = None
    last_click_at = float("-inf")
    retry_delay = max(0.0, float(same_state_retry_s))

    while time.monotonic() <= deadline:
        state = get_login_state(bot_id)
        if state is LoginState.LOGGED_IN:
            return True

        # A real screen transition starts a fresh step. This means the next
        # actionable state can be handled immediately instead of inheriting a
        # delay from the previous button.
        if state is not previous_state:
            handled_state = None
            previous_state = state

        image_name = CLICK_IMAGE_BY_STATE.get(state)
        now = time.monotonic()
        may_retry_same_state = now - last_click_at >= retry_delay
        if image_name is not None and (
            handled_state is not state or may_retry_same_state
        ):
            _click(image_name, bot_id)
            handled_state = state
            last_click_at = now

        # CONNECTING, HOME and UNKNOWN intentionally do nothing here.
        time.sleep(max(0.05, float(poll_interval_s)))

    return is_logged_in(bot_id)


__all__ = ["login"]
