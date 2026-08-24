from __future__ import annotations

import ctypes
import random
import time
from typing import Any, Mapping, Sequence

from pynput.mouse import Button, Controller

from . import mouse_engine
from .movements import create_path
from .mouse_plan import MousePlanValidationError, validate_mouse_plan
from .mouse_runtime import (
    PENDING_CLICK_TIMEOUT_S,
    MouseActionCancelled,
    MouseExecutionStatus,
    MouseRuntimeError,
    PendingClickUnavailable,
    PendingTimeline as _PendingTimeline,
    action_guard,
    cancel_pending_click as _cancel_pending_click,
    emergency_stop_requested,
    has_pending_click as _has_pending_click,
    last_execution_status,
    pop_pending as _pop_pending,
    raise_if_stopped as _raise_if_stopped,
    request_emergency_stop,
    reset_emergency_stop,
    set_execution_status as _set_execution_status,
    set_pending as _set_pending,
)
from .profile import get_section

_controller = Controller()
_last_engine_error: str | None = None


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def _selected_button(button: str) -> Button:
    if button == "left":
        return Button.left
    if button == "right":
        return Button.right
    raise ValueError("button must be 'left' or 'right'")


def _screen_size() -> tuple[int, int]:
    """Return the size of the complete Windows virtual desktop."""
    try:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(78))
        height = int(user32.GetSystemMetrics(79))
        if width > 0 and height > 0:
            return width, height
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except (AttributeError, OSError):
        return 1920, 1080


def _screen_origin() -> tuple[int, int]:
    """Return the top-left of the virtual desktop in global coordinates."""
    try:
        user32 = ctypes.windll.user32
        return int(user32.GetSystemMetrics(76)), int(user32.GetSystemMetrics(77))
    except (AttributeError, OSError):
        return 0, 0


def _target_to_local(
    target: Mapping[str, Any] | Sequence[float],
    origin: tuple[int, int],
) -> dict[str, Any] | tuple[float, ...]:
    """Translate a global target into provider-local virtual desktop coordinates."""
    origin_x, origin_y = origin
    if isinstance(target, Mapping):
        translated = dict(target)
        for field in ("left", "right", "x"):
            if field in translated:
                translated[field] = float(translated[field]) - origin_x
        for field in ("top", "bottom", "y"):
            if field in translated:
                translated[field] = float(translated[field]) - origin_y
        return translated

    translated = list(target)
    if len(translated) >= 2:
        translated[0] = float(translated[0]) - origin_x
        translated[1] = float(translated[1]) - origin_y
    return tuple(translated)


def _plan_to_global(
    plan: Mapping[str, Any],
    origin: tuple[int, int],
) -> dict[str, Any]:
    """Copy a validated provider plan back into Windows global coordinates."""
    origin_x, origin_y = origin
    translated = dict(plan)
    translated["events"] = [
        {
            **dict(event),
            "x": float(event["x"]) + origin_x,
            "y": float(event["y"]) + origin_y,
        }
        for event in plan["events"]
    ]
    return translated


def _wait_until(deadline: float) -> None:
    while True:
        _raise_if_stopped()
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > 0.003:
            time.sleep(remaining - 0.0015)
        else:
            time.sleep(0)


def _sleep_interruptibly(duration_seconds: float) -> None:
    _wait_until(time.perf_counter() + max(0.0, duration_seconds))


def _timer_resolution(enable: bool) -> None:
    try:
        winmm = ctypes.windll.winmm
        (winmm.timeBeginPeriod if enable else winmm.timeEndPeriod)(1)
    except (AttributeError, OSError):
        pass


def _execute_events(
    events: Sequence[Mapping[str, Any]],
    started_at: float,
    *,
    button: str = "left",
) -> None:
    selected = _selected_button(button)
    pressed = False
    _raise_if_stopped()
    _timer_resolution(True)
    try:
        for event in events:
            _wait_until(started_at + float(event["t_ms"]) / 1000.0)
            _raise_if_stopped()
            event_type = str(event["type"])
            if event_type == "move":
                _controller.position = int(round(event["x"])), int(round(event["y"]))
            elif event_type == "button_down":
                _controller.position = int(round(event["x"])), int(round(event["y"]))
                _controller.press(selected)
                pressed = True
            elif event_type == "button_up":
                _controller.position = int(round(event["x"])), int(round(event["y"]))
                _controller.release(selected)
                pressed = False
    finally:
        if pressed:
            _controller.release(selected)
        _timer_resolution(False)


def _external_plan(
    target: Mapping[str, Any] | Sequence[float],
    *,
    target_radius: float | None = None,
    padding_px: float | None = None,
    require_external: bool = False,
    require_click: bool = False,
) -> dict[str, Any] | None:
    global _last_engine_error
    settings = mouse_engine.load_settings()
    if not bool(settings.get("enabled")):
        message = "External mouse engine is disabled"
        _last_engine_error = message
        _set_execution_status("fallback", fallback_used=True, error=message)
        if require_external:
            raise mouse_engine.MouseEngineDisabled(message)
        return None
    origin = _screen_origin()
    global_start = tuple(map(int, _controller.position))
    start = (global_start[0] - origin[0], global_start[1] - origin[1])
    local_target = _target_to_local(target, origin)
    screen_size = _screen_size()
    try:
        plan = mouse_engine.create_plan(
            start,
            local_target,
            target_radius=target_radius,
            padding_px=padding_px,
            coordinate_size=screen_size,
            settings=settings,
        )
        validate_mouse_plan(
            plan,
            target=local_target,
            screen_size=screen_size,
            require_click=require_click,
            target_padding=(
                float(settings.get("default_padding_px", 0))
                if padding_px is None
                else float(padding_px)
            ),
        )
    except Exception as exc:
        _last_engine_error = str(exc)
        _set_execution_status("fallback", fallback_used=True, error=str(exc))
        if bool(settings.get("fallback_on_error", True)) and not require_external:
            return None
        if isinstance(exc, mouse_engine.MouseEngineError):
            raise
        if isinstance(exc, MousePlanValidationError):
            raise mouse_engine.MouseEngineUnavailable(
                f"Mouse provider returned an unsafe plan: {exc}"
            ) from exc
        raise mouse_engine.MouseEngineUnavailable(str(exc)) from exc
    _last_engine_error = None
    _set_execution_status("external")
    return _plan_to_global(plan, origin)


def _split_before_first_click(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    copied = [dict(event) for event in events]
    for index, event in enumerate(copied):
        if event.get("type") == "button_down":
            return copied[:index], copied[index:]
    return copied, []


def _rebase_pending_events(
    movement_events: Sequence[Mapping[str, Any]],
    click_events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Restart the provider's remaining click timing when click() is called."""
    if not click_events:
        return []
    movement_finished_at = (
        float(movement_events[-1]["t_ms"])
        if movement_events
        else float(click_events[0]["t_ms"])
    )
    return [
        {
            **dict(event),
            "t_ms": max(0.0, float(event["t_ms"]) - movement_finished_at),
        }
        for event in click_events
    ]


def _point_target_bounds(
    x: float,
    y: float,
    radius: float,
) -> tuple[float, float, float, float]:
    return x - radius, y - radius, x + radius, y + radius


def _rectangle_target_bounds(
    bounds: Mapping[str, float],
) -> tuple[float, float, float, float]:
    return (
        float(bounds["left"]),
        float(bounds["top"]),
        float(bounds["right"]),
        float(bounds["bottom"]),
    )


def has_pending_click() -> bool:
    return _has_pending_click(position())


def cancel_pending_click() -> bool:
    return _cancel_pending_click()


def _native_move_to(x: int, y: int, method: str | None = None) -> None:
    _raise_if_stopped()
    settings = get_section("mouse")
    start = tuple(map(int, _controller.position))
    target = (int(x), int(y))
    movement_method = method or str(settings["movement_method"])
    steps = random.randint(int(settings["steps_min"]), int(settings["steps_max"]))
    duration = _between(settings, "duration_min_s", "duration_max_s")
    movement_settings = settings.get("movement_settings", {}).get(movement_method, {})
    path = create_path(movement_method, start, target, steps, movement_settings)
    step_delay = duration / max(1, len(path))
    for point in path:
        _raise_if_stopped()
        _controller.position = point
        _sleep_interruptibly(step_delay)


def _native_click(button: str = "left") -> None:
    _raise_if_stopped()
    settings = get_section("mouse")
    selected = _selected_button(button)
    _sleep_interruptibly(_between(settings, "pre_click_min_s", "pre_click_max_s"))
    _controller.press(selected)
    try:
        _sleep_interruptibly(
            _between(settings, "click_hold_min_s", "click_hold_max_s")
        )
        _raise_if_stopped()
    finally:
        _controller.release(selected)
    _sleep_interruptibly(_between(settings, "post_click_min_s", "post_click_max_s"))


def move_to(
    x: int,
    y: int,
    method: str | None = None,
    *,
    target_radius: float | None = None,
    require_external: bool = False,
    keep_pending_click: bool = True,
) -> None:
    """Move to a point using the external engine or active-profile fallback."""
    with action_guard():
        _raise_if_stopped()
        _set_pending(None)
        use_external = method is None or method.strip().lower() in {
            "external",
            "ai_mouse_lab",
        }
        if require_external and not use_external:
            raise ValueError("require_external cannot be combined with a native method")
        if use_external:
            settings = mouse_engine.load_settings()
            radius = float(
                target_radius
                if target_radius is not None
                else settings.get("default_target_radius_px", 6)
            )
            plan = _external_plan(
                (int(x), int(y), radius),
                require_external=require_external,
            )
            if plan is not None:
                before, after = _split_before_first_click(plan["events"])
                started_at = time.perf_counter()
                _execute_events(before, started_at)
                pending_events = _rebase_pending_events(before, after)
                pending = (
                    _PendingTimeline(
                        pending_events,
                        time.perf_counter(),
                        _point_target_bounds(int(x), int(y), radius),
                    )
                    if keep_pending_click and pending_events
                    else None
                )
                _set_pending(pending)
                return
        if not use_external or not last_execution_status().fallback_used:
            _set_execution_status("native")
        _native_move_to(x, y, method if not use_external else None)


def click(button: str = "left", *, require_pending: bool = False) -> None:
    """Finish a pending external plan or use active-profile click delays."""
    with action_guard():
        _raise_if_stopped()
        _selected_button(button)
        if has_pending_click():
            pending = _pop_pending()
            if pending is not None:
                _set_execution_status("external")
                _execute_events(pending.events, time.perf_counter(), button=button)
                return
        if require_pending:
            raise PendingClickUnavailable(
                "No pending click is available. Move to a target again before clicking."
            )
        _set_execution_status("native")
        _native_click(button)


def move_and_click(
    x: int,
    y: int,
    button: str = "left",
    *,
    target_radius: float | None = None,
    require_external: bool = False,
) -> None:
    with action_guard():
        _raise_if_stopped()
        _selected_button(button)
        _set_pending(None)
        settings = mouse_engine.load_settings()
        radius = float(
            target_radius
            if target_radius is not None
            else settings.get("default_target_radius_px", 6)
        )
        plan = _external_plan(
            (int(x), int(y), radius),
            require_external=require_external,
            require_click=True,
        )
        if plan is not None:
            _execute_events(plan["events"], time.perf_counter(), button=button)
            return
        _native_move_to(x, y)
        _native_click(button)


def _safe_point(bounds: Mapping[str, float], padding_px: float) -> tuple[int, int]:
    padding = max(0, int(round(padding_px)))
    left = int(round(bounds["left"])) + padding
    top = int(round(bounds["top"])) + padding
    right = int(round(bounds["right"])) - padding - 1
    bottom = int(round(bounds["bottom"])) - padding - 1
    if right < left or bottom < top:
        return (
            int(round((float(bounds["left"]) + float(bounds["right"])) / 2)),
            int(round((float(bounds["top"]) + float(bounds["bottom"])) / 2)),
        )
    return random.randint(left, right), random.randint(top, bottom)


def move_to_target(
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    padding_px: float = 0,
    require_external: bool = False,
    keep_pending_click: bool = True,
) -> None:
    with action_guard():
        _raise_if_stopped()
        _set_pending(None)
        bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
        plan = _external_plan(
            bounds,
            padding_px=padding_px,
            require_external=require_external,
        )
        if plan is not None:
            before, after = _split_before_first_click(plan["events"])
            started_at = time.perf_counter()
            _execute_events(before, started_at)
            pending_events = _rebase_pending_events(before, after)
            pending = (
                _PendingTimeline(
                    pending_events,
                    time.perf_counter(),
                    _rectangle_target_bounds(bounds),
                )
                if keep_pending_click and pending_events
                else None
            )
            _set_pending(pending)
            return
        _native_move_to(*_safe_point(bounds, padding_px))


def move_and_click_target(
    left: int,
    top: int,
    right: int,
    bottom: int,
    *,
    padding_px: float = 0,
    button: str = "left",
    require_external: bool = False,
) -> None:
    with action_guard():
        _raise_if_stopped()
        _selected_button(button)
        _set_pending(None)
        bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
        plan = _external_plan(
            bounds,
            padding_px=padding_px,
            require_external=require_external,
            require_click=True,
        )
        if plan is not None:
            _execute_events(plan["events"], time.perf_counter(), button=button)
            return
        _native_move_to(*_safe_point(bounds, padding_px))
        _native_click(button)


def scroll(amount: int) -> None:
    with action_guard():
        _raise_if_stopped()
        _set_pending(None)
        _set_execution_status("native")
        settings = get_section("mouse")
        direction = 1 if amount > 0 else -1
        for _ in range(abs(int(amount))):
            _raise_if_stopped()
            _controller.scroll(0, direction)
            time.sleep(_between(settings, "scroll_delay_min_s", "scroll_delay_max_s"))


def position() -> tuple[int, int]:
    return tuple(map(int, _controller.position))


def last_engine_error() -> str | None:
    return _last_engine_error
