from __future__ import annotations

import time
from collections.abc import Callable, Collection
from typing import Hashable, TypeVar

from core.action_trace import trace


StateT = TypeVar("StateT", bound=Hashable)


def _state_label(state: StateT) -> str:
    return str(getattr(state, "value", state))


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
    limit_reported: set[StateT] = set()
    previous_state: StateT | None = None

    while time.monotonic() <= deadline:
        state = get_state()
        if state != previous_state:
            trace(f"[STATE] {_state_label(state)}")
            previous_state = state

        if state == success_state:
            trace("[OK] success state reached")
            return True

        if state in actionable_states:
            used = attempts.get(state, 0)
            last_attempt = last_attempt_at.get(state, float("-inf"))
            now = time.monotonic()

            if used < max_attempts and now - last_attempt >= retry_delay:
                attempt_number = used + 1
                trace(
                    f"[ACTION] {_state_label(state)} attempt "
                    f"{attempt_number}/{max_attempts}"
                )
                act(state)
                attempts[state] = attempt_number
                last_attempt_at[state] = now
            elif used >= max_attempts and state not in limit_reported:
                trace(
                    f"[LIMIT] {_state_label(state)} reached "
                    f"{max_attempts} attempts; observing only"
                )
                limit_reported.add(state)

        time.sleep(max(0.05, float(poll_interval_s)))

    trace("[TIMEOUT] action timeout reached")
    if final_check is not None:
        result = bool(final_check())
    else:
        result = get_state() == success_state
    trace(f"[RESULT] final check = {result}")
    return result


__all__ = ["run_bounded_state_loop"]
