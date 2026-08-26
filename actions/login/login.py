from __future__ import annotations

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
from actions.login.state_loop import run_bounded_state_loop


DEFAULT_TIMEOUT_S = 120.0
POLL_INTERVAL_S = 0.40
SAME_STATE_RETRY_S = 5.0
MAX_ATTEMPTS_PER_STATE = 3

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
    max_attempts_per_state: int = MAX_ATTEMPTS_PER_STATE,
) -> bool:
    """Move the current login screen forward until the player is logged in.

    The screen may remain on slow/transitional states for the full timeout, but
    each clickable state is attempted only a bounded number of times. This
    prevents a slow server or flickering UI from causing an endless click loop.
    """

    def act(state: LoginState) -> None:
        _click(CLICK_IMAGE_BY_STATE[state], bot_id)

    return run_bounded_state_loop(
        get_state=lambda: get_login_state(bot_id),
        success_state=LoginState.LOGGED_IN,
        actionable_states=CLICK_IMAGE_BY_STATE,
        act=act,
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        retry_s=same_state_retry_s,
        max_attempts_per_state=max_attempts_per_state,
        final_check=lambda: is_logged_in(bot_id),
    )


__all__ = ["login"]
