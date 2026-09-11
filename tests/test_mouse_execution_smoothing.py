from __future__ import annotations

import math

from core import mouse


def _max_spatial_step(events: list[dict[str, float]], start: tuple[int, int]) -> float:
    previous = (float(start[0]), float(start[1]))
    largest = 0.0
    for event in events:
        if "x" not in event or "y" not in event:
            continue
        current = (float(event["x"]), float(event["y"]))
        largest = max(largest, math.hypot(current[0] - previous[0], current[1] - previous[1]))
        previous = current
    return largest


def test_densify_execution_events_limits_large_move_steps():
    events = [
        {"type": "move", "t_ms": 120.0, "x": 160.0, "y": 0.0},
        {"type": "button_down", "t_ms": 150.0, "x": 160.0, "y": 0.0},
        {"type": "button_up", "t_ms": 190.0, "x": 160.0, "y": 0.0},
    ]

    dense = mouse._densify_execution_events(
        events,
        start_position=(0, 0),
        max_step_px=45.0,
    )

    move_events = [event for event in dense if event["type"] == "move"]
    assert len(move_events) == 4
    assert _max_spatial_step(move_events, (0, 0)) <= 45.0 + 1e-9

    # The original click events keep their timing and order.
    assert dense[-2] == events[-2]
    assert dense[-1] == events[-1]


def test_densify_execution_events_preserves_move_endpoint_and_timing():
    events = [
        {"type": "move", "t_ms": 100.0, "x": 90.0, "y": 0.0},
        {"type": "move", "t_ms": 200.0, "x": 180.0, "y": 0.0},
    ]

    dense = mouse._densify_execution_events(
        events,
        start_position=(0, 0),
        max_step_px=45.0,
    )

    assert dense[-1] == events[-1]
    times = [float(event["t_ms"]) for event in dense]
    assert times == sorted(times)
    assert math.isclose(float(dense[1]["t_ms"]), 100.0)
    assert math.isclose(float(dense[-1]["t_ms"]), 200.0)


def test_densify_execution_events_leaves_small_steps_unchanged():
    events = [
        {"type": "move", "t_ms": 20.0, "x": 20.0, "y": 10.0},
        {"type": "move", "t_ms": 40.0, "x": 40.0, "y": 20.0},
    ]

    dense = mouse._densify_execution_events(
        events,
        start_position=(0, 0),
        max_step_px=45.0,
    )

    assert dense == events


def test_densify_execution_events_rejects_invalid_limit():
    events = [{"type": "move", "t_ms": 20.0, "x": 20.0, "y": 10.0}]

    for invalid in (0.0, -1.0, float("inf"), float("nan")):
        try:
            mouse._densify_execution_events(
                events,
                start_position=(0, 0),
                max_step_px=invalid,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for max_step_px={invalid!r}")
