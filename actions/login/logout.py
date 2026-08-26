from __future__ import annotations

from core import mouse_actions
from definitions.login.logout_state import (
    INTERFACE_SCREEN_CROSS_IMAGE,
    LOGOUT_AREA,
    LOGOUT_CLICK_HERE_IMAGE,
    LOGOUT_DOOR_UNSELECTED_IMAGE,
    LogoutState,
    get_logout_state,
)
from actions.login.state_loop import run_bounded_state_loop


DEFAULT_TIMEOUT_S = 60.0
POLL_INTERVAL_S = 0.40
SAME_STATE_RETRY_S = 5.0
MAX_ATTEMPTS_PER_STATE = 3

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
    max_attempts_per_state: int = MAX_ATTEMPTS_PER_STATE,
) -> bool:
    """Log out through visually confirmed, bounded actions only.

    Slow screens may be observed for the full timeout. Each clickable state is
    attempted only ``max_attempts_per_state`` times during the entire run.
    Hover-sensitive logout targets skip the second identical-image check;
    ``Interface_ScreenCross`` keeps it.
    """

    def act(state: LogoutState) -> None:
        _click(
            CLICK_IMAGE_BY_STATE[state],
            bot_id,
            confirm_before_click=(state is LogoutState.BLOCKED_BY_INTERFACE),
        )

    return run_bounded_state_loop(
        get_state=lambda: get_logout_state(bot_id),
        success_state=LogoutState.LOGGED_OUT,
        actionable_states=CLICK_IMAGE_BY_STATE,
        act=act,
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        retry_s=same_state_retry_s,
        max_attempts_per_state=max_attempts_per_state,
        final_check=lambda: get_logout_state(bot_id) is LogoutState.LOGGED_OUT,
    )


__all__ = ["logout"]
