from __future__ import annotations

import time

import pytest

from core import mouse_runtime


def teardown_function() -> None:
    mouse_runtime.reset_emergency_stop()
    mouse_runtime.set_pending(None)


def test_pending_click_requires_fresh_cursor_inside_target() -> None:
    mouse_runtime.set_pending(
        mouse_runtime.PendingTimeline(
            events=[{"type": "button_down", "t_ms": 0}],
            created_at=time.perf_counter(),
            target_bounds=(10, 10, 20, 20),
        )
    )

    assert mouse_runtime.has_pending_click((15, 15)) is True
    assert mouse_runtime.has_pending_click((25, 25)) is False


def test_expired_pending_click_is_cleared() -> None:
    mouse_runtime.set_pending(
        mouse_runtime.PendingTimeline(
            events=[{"type": "button_down", "t_ms": 0}],
            created_at=time.perf_counter() - mouse_runtime.PENDING_CLICK_TIMEOUT_S - 1,
            target_bounds=(10, 10, 20, 20),
        )
    )

    assert mouse_runtime.has_pending_click((15, 15)) is False
    assert mouse_runtime.pop_pending() is None


def test_emergency_stop_remains_interruptible() -> None:
    mouse_runtime.request_emergency_stop()

    with pytest.raises(mouse_runtime.MouseActionCancelled):
        mouse_runtime.raise_if_stopped()

    mouse_runtime.reset_emergency_stop()
    mouse_runtime.raise_if_stopped()
