from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import threading
import time
from typing import Any, Iterator

PENDING_CLICK_TIMEOUT_S = 3.0

_thread_state = threading.local()
_action_lock = threading.RLock()
_emergency_stop = threading.Event()


class MouseRuntimeError(RuntimeError):
    pass


class MouseActionCancelled(MouseRuntimeError):
    pass


class PendingClickUnavailable(MouseRuntimeError):
    pass


@dataclass(frozen=True)
class MouseExecutionStatus:
    engine: str
    fallback_used: bool = False
    error: str | None = None


@dataclass
class PendingTimeline:
    events: list[dict[str, Any]]
    created_at: float
    target_bounds: tuple[float, float, float, float]


@contextmanager
def action_guard() -> Iterator[None]:
    """Serialize access to the one physical mouse shared by every bot."""
    with _action_lock:
        yield


def set_execution_status(
    engine: str,
    *,
    fallback_used: bool = False,
    error: str | None = None,
) -> None:
    _thread_state.execution_status = MouseExecutionStatus(
        engine=engine,
        fallback_used=fallback_used,
        error=error,
    )


def last_execution_status() -> MouseExecutionStatus:
    return getattr(
        _thread_state,
        "execution_status",
        MouseExecutionStatus(engine="none"),
    )


def request_emergency_stop() -> None:
    _emergency_stop.set()


def reset_emergency_stop() -> None:
    _emergency_stop.clear()


def emergency_stop_requested() -> bool:
    return _emergency_stop.is_set()


def raise_if_stopped() -> None:
    if _emergency_stop.is_set():
        raise MouseActionCancelled(
            "Mouse emergency stop is active. Call reset_emergency_stop() before retrying."
        )


def set_pending(value: PendingTimeline | None) -> None:
    _thread_state.pending = value


def pop_pending() -> PendingTimeline | None:
    pending = getattr(_thread_state, "pending", None)
    _thread_state.pending = None
    return pending


def has_pending_click(position: tuple[int, int]) -> bool:
    pending = getattr(_thread_state, "pending", None)
    if pending is None:
        return False
    if time.perf_counter() - pending.created_at > PENDING_CLICK_TIMEOUT_S:
        set_pending(None)
        return False
    x, y = position
    left, top, right, bottom = pending.target_bounds
    if not (left <= x < right and top <= y < bottom):
        set_pending(None)
        return False
    return bool(pending.events)


def cancel_pending_click() -> bool:
    with action_guard():
        existed = getattr(_thread_state, "pending", None) is not None
        set_pending(None)
        return existed
