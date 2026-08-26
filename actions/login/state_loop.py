from __future__ import annotations

import time
from collections.abc import Callable, Collection
from typing import Hashable, TypeVar


StateT = TypeVar("StateT", bound=Hashable)


def run_bounded_state_loop(
    *,
    get_state: Callable[[], StateT],
    success_state: StateT,
    actionable_states: Collection[StateT],
    act: Callable[[StateT], None],
    timeout_s: float,
    poll_interval_s: float,
    retry_s: float,
    max_attempts_per_state: int,
    final_check: Callable[[], bool] | None = None,
) -> bool:
    """Poll state and perform bounded, rate-limited actions.

    Each actionable state may be acted on at most ``max_attempts_per_state``
    times during the entire run. Reaching another state does not reset that
    counter, so a flickering UI can never create an unbounded click loop.
    Non-actionable states are only observed.
    """
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    retry_delay = max(0.0, float(retry_s))
    max_attempts = max(0, int(max_attempts_per_state))
    attempts: dict[StateT, int] = {}
    last_attempt_at: dict[StateT, float] = {}

    while time.monotonic() <= deadline:
        state = get_state()
        if state == success_state:
            return True

        if state in actionable_states:
            used = attempts.get(state, 0)
            last_attempt = last_attempt_at.get(state, float("-inf"))
            now = time.monotonic()

            if used < max_attempts and now - last_attempt >= retry_delay:
                act(state)
                attempts[state] = used + 1
                last_attempt_at[state] = now

        time.sleep(max(0.05, float(poll_interval_s)))

    if final_check is not None:
        return bool(final_check())
    return get_state() == success_state


__all__ = ["run_bounded_state_loop"]
