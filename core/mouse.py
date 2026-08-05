from __future__ import annotations

from dataclasses import dataclass
import ctypes
import random
import threading
import time
from typing import Any, Mapping, Sequence

from pynput.mouse import Button, Controller

from . import mouse_engine
from .movements import create_path
from .profile import get_section

_controller = Controller()
_thread_state = threading.local()
_last_engine_error: str | None = None


@dataclass
class _PendingTimeline:
    events: list[dict[str, Any]]
    started_at: float


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def _selected_button(button: str) -> Button:
    return Button.left if button == "left" else Button.right


def _screen_size() -> tuple[int, int]:
    try:
        user32 = ctypes.windll.user32
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except (AttributeError, OSError):
        return 1920, 1080


def _wait_until(deadline: float) -> None:
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > 0.003:
            time.sleep(remaining - 0.0015)
        else:
            time.sleep(0)


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
    _timer_resolution(True)
    try:
        for event in events:
            _wait_until(started_at + float(event["t_ms"]) / 1000.0)
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
) -> dict[str, Any] | None:
    global _last_engine_error
    settings = mouse_engine.load_settings()
    if not bool(settings.get("enabled")):
        return None
    start = tuple(map(int, _controller.position))
    try:
        plan = mouse_engine.create_plan(
            start,
            target,
            target_radius=target_radius,
            padding_px=padding_px,
            coordinate_size=_screen_size(),
            settings=settings,
        )
    except Exception as exc:
        _last_engine_error = str(exc)
        if bool(settings.get("fallback_on_error", True)):
            return None
        raise
    _last_engine_error = None
    return plan


def _split_before_first_click(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    copied = [dict(event) for event in events]
    for index, event in enumerate(copied):
        if event.get("type") == "button_down":
            return copied[:index], copied[index:]
    return copied, []


def _set_pending(value: _PendingTimeline | None) -> None:
    _thread_state.pending = value


def _pop_pending() -> _PendingTimeline | None:
    pending = getattr(_thread_state, "pending", None)
    _thread_state.pending = None
    return pending


def _native_move_to(x: int, y: int, method: str | None = None) -> None:
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
        _controller.position = point
        time.sleep(step_delay)


def _native_click(button: str = "left") -> None:
    settings = get_section("mouse")
    selected = _selected_button(button)
    time.sleep(_between(settings, "pre_click_min_s", "pre_click_max_s"))
    _controller.press(selected)
    time.sleep(_between(settings, "click_hold_min_s", "click_hold_max_s"))
    _controller.release(selected)
    time.sleep(_between(settings, "post_click_min_s", "post_click_max_s"))


def move_to(
    x: int,
    y: int,
    method: str | None = None,
    *,
    target_radius: float | None = None,
) -> None:
    """Move to a point using the external engine or active-profile fallback."""
    _set_pending(None)
    use_external = method is None or method.strip().lower() in {"external", "ai_mouse_lab"}
    if use_external:
        settings = mouse_engine.load_settings()
        radius = float(
            target_radius
            if target_radius is not None
            else settings.get("default_target_radius_px", 6)
        )
        plan = _external_plan((int(x), int(y), radius))
        if plan is not None:
            before, after = _split_before_first_click(plan["events"])
            started_at = time.perf_counter()
            _execute_events(before, started_at)
            _set_pending(_PendingTimeline(after, started_at) if after else None)
            return
    _native_move_to(x, y, method if not use_external else None)


def click(button: str = "left") -> None:
    """Finish a pending external plan or use active-profile click delays."""
    pending = _pop_pending()
    if pending is not None:
        _execute_events(pending.events, pending.started_at, button=button)
        return
    _native_click(button)


def move_and_click(
    x: int,
    y: int,
    button: str = "left",
    *,
    target_radius: float | None = None,
) -> None:
    _set_pending(None)
    settings = mouse_engine.load_settings()
    radius = float(
        target_radius
        if target_radius is not None
        else settings.get("default_target_radius_px", 6)
    )
    plan = _external_plan((int(x), int(y), radius))
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
) -> None:
    _set_pending(None)
    bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
    plan = _external_plan(bounds, padding_px=padding_px)
    if plan is not None:
        before, after = _split_before_first_click(plan["events"])
        started_at = time.perf_counter()
        _execute_events(before, started_at)
        _set_pending(_PendingTimeline(after, started_at) if after else None)
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
) -> None:
    _set_pending(None)
    bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
    plan = _external_plan(bounds, padding_px=padding_px)
    if plan is not None:
        _execute_events(plan["events"], time.perf_counter(), button=button)
        return
    _native_move_to(*_safe_point(bounds, padding_px))
    _native_click(button)


def scroll(amount: int) -> None:
    settings = get_section("mouse")
    direction = 1 if amount > 0 else -1
    for _ in range(abs(int(amount))):
        _controller.scroll(0, direction)
        time.sleep(_between(settings, "scroll_delay_min_s", "scroll_delay_max_s"))


def position() -> tuple[int, int]:
    return tuple(map(int, _controller.position))


def last_engine_error() -> str | None:
    return _last_engine_error
