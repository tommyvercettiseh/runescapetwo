from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


ALLOWED_EVENT_TYPES = {"move", "button_down", "button_up"}
MAX_PLAN_DURATION_MS = 30_000.0


class MousePlanValidationError(ValueError):
    """Raised before unsafe provider output can control the physical mouse."""


def _finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise MousePlanValidationError(f"{field_name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MousePlanValidationError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(number):
        raise MousePlanValidationError(f"{field_name} must be a finite number")
    return number


def _target_bounds(
    target: Mapping[str, Any] | Sequence[float],
) -> tuple[float, float, float, float]:
    if isinstance(target, Mapping):
        if all(name in target for name in ("left", "top", "right", "bottom")):
            bounds = (
                _finite_number(target["left"], "target.left"),
                _finite_number(target["top"], "target.top"),
                _finite_number(target["right"], "target.right"),
                _finite_number(target["bottom"], "target.bottom"),
            )
        elif "x" in target and "y" in target and "radius" in target:
            x = _finite_number(target["x"], "target.x")
            y = _finite_number(target["y"], "target.y")
            radius = _finite_number(target["radius"], "target.radius")
            bounds = x - radius, y - radius, x + radius, y + radius
        else:
            raise MousePlanValidationError("target has no supported bounds")
    else:
        if isinstance(target, (str, bytes)) or len(target) < 3:
            raise MousePlanValidationError("point target requires x, y and radius")
        x = _finite_number(target[0], "target.x")
        y = _finite_number(target[1], "target.y")
        radius = _finite_number(target[2], "target.radius")
        bounds = x - radius, y - radius, x + radius, y + radius

    left, top, right, bottom = bounds
    if right <= left or bottom <= top:
        raise MousePlanValidationError("target bounds must have positive dimensions")
    return bounds


def validate_mouse_plan(
    plan: Any,
    *,
    target: Mapping[str, Any] | Sequence[float],
    screen_size: Sequence[float],
    require_click: bool,
    target_padding: float = 0,
) -> dict[str, Any]:
    """Validate provider output before it is sent to the mouse controller."""
    if not isinstance(plan, dict):
        raise MousePlanValidationError("mouse provider must return an object")
    events = plan.get("events")
    if not isinstance(events, list) or not events:
        raise MousePlanValidationError("mouse plan requires at least one event")

    if len(screen_size) < 2:
        raise MousePlanValidationError("screen_size requires width and height")
    screen_width = _finite_number(screen_size[0], "screen width")
    screen_height = _finite_number(screen_size[1], "screen height")
    if screen_width <= 0 or screen_height <= 0:
        raise MousePlanValidationError("screen dimensions must be positive")

    left, top, right, bottom = _target_bounds(target)
    padding = _finite_number(target_padding, "target padding")
    if padding < 0:
        raise MousePlanValidationError("target padding must not be negative")
    if isinstance(target, Mapping):
        left += padding
        top += padding
        right -= padding
        bottom -= padding
        if right <= left or bottom <= top:
            raise MousePlanValidationError("target padding leaves no safe click area")
    if left < 0 or top < 0 or right > screen_width or bottom > screen_height:
        raise MousePlanValidationError("target bounds fall outside the screen")

    previous_time = -1.0
    pressed = False
    move_count = 0
    click_count = 0
    last_click_position: tuple[float, float] | None = None

    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise MousePlanValidationError(f"event {index} must be an object")
        event_type = str(event.get("type", ""))
        if event_type not in ALLOWED_EVENT_TYPES:
            raise MousePlanValidationError(
                f"event {index} has unsupported type: {event_type!r}"
            )

        event_time = _finite_number(event.get("t_ms"), f"event {index}.t_ms")
        if event_time < previous_time:
            raise MousePlanValidationError("mouse event times must not go backwards")
        if event_time < 0 or event_time > MAX_PLAN_DURATION_MS:
            raise MousePlanValidationError(
                f"mouse plan duration must stay within {MAX_PLAN_DURATION_MS:g} ms"
            )
        previous_time = event_time

        x = _finite_number(event.get("x"), f"event {index}.x")
        y = _finite_number(event.get("y"), f"event {index}.y")
        if not 0 <= x < screen_width or not 0 <= y < screen_height:
            raise MousePlanValidationError(f"event {index} falls outside the screen")

        if event_type == "move":
            move_count += 1
            if pressed and not (left <= x < right and top <= y < bottom):
                raise MousePlanValidationError(
                    "mouse plan moves outside the safe target while pressed"
                )
        elif event_type == "button_down":
            if pressed:
                raise MousePlanValidationError("mouse plan presses an already pressed button")
            pressed = True
            click_count += 1
            if click_count > 1:
                raise MousePlanValidationError("mouse plan may contain only one click")
            last_click_position = x, y
        elif event_type == "button_up":
            if not pressed:
                raise MousePlanValidationError("mouse plan releases a button before pressing it")
            if not left <= x < right or not top <= y < bottom:
                raise MousePlanValidationError(
                    "mouse plan releases outside the safe target bounds"
                )
            pressed = False

    if move_count == 0:
        raise MousePlanValidationError("mouse plan requires at least one move event")
    if pressed:
        raise MousePlanValidationError("mouse plan leaves the button pressed")
    if require_click and click_count == 0:
        raise MousePlanValidationError("click action requires button events")
    if click_count and events[-1].get("type") != "button_up":
        raise MousePlanValidationError("mouse plan must finish with button_up")
    if click_count and last_click_position is not None:
        click_x, click_y = last_click_position
        if not left <= click_x < right or not top <= click_y < bottom:
            raise MousePlanValidationError(
                "final provider click falls outside the safe target bounds"
            )

    return plan
