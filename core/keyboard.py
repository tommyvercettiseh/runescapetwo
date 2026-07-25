from __future__ import annotations

import math
import random
import time
from typing import Any

from .profile import get_section

_controller: Any | None = None


def _get_controller() -> Any:
    global _controller
    if _controller is None:
        from pynput.keyboard import Controller

        _controller = Controller()
    return _controller


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def _resolve(key: str):
    from pynput.keyboard import Key

    special_keys = {
        "alt": Key.alt,
        "backspace": Key.backspace,
        "ctrl": Key.ctrl,
        "delete": Key.delete,
        "down": Key.down,
        "end": Key.end,
        "enter": Key.enter,
        "esc": Key.esc,
        "home": Key.home,
        "left": Key.left,
        "page_down": Key.page_down,
        "page_up": Key.page_up,
        "right": Key.right,
        "shift": Key.shift,
        "space": Key.space,
        "tab": Key.tab,
        "up": Key.up,
    }
    raw_key = str(key)
    clean_key = raw_key.strip().lower()
    if clean_key in special_keys:
        return special_keys[clean_key]
    if len(raw_key) != 1:
        raise ValueError(f"Unknown keyboard key: {key}")
    return raw_key


def key_down(key: str) -> None:
    _get_controller().press(_resolve(key))


def key_up(key: str) -> None:
    _get_controller().release(_resolve(key))


def press(key: str) -> None:
    """Press and release one key using the active profile."""
    settings = get_section("keyboard")
    resolved = _resolve(key)
    controller = _get_controller()

    controller.press(resolved)
    try:
        time.sleep(_between(settings, "press_hold_min_s", "press_hold_max_s"))
    finally:
        controller.release(resolved)


def hold(key: str, duration_s: float | None = None) -> None:
    """Hold one key. A supplied duration overrides the profile."""
    settings = get_section("keyboard")
    resolved = _resolve(key)
    duration = duration_s

    if duration is None:
        duration = _between(settings, "press_hold_min_s", "press_hold_max_s")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or duration < 0
    ):
        raise ValueError("Hold duration must be a finite non-negative number")

    controller = _get_controller()
    controller.press(resolved)
    try:
        time.sleep(float(duration))
    finally:
        controller.release(resolved)


def type_text(text: str, enter: bool = False) -> None:
    """Type text using profile-driven intervals and optional pauses."""
    if not isinstance(enter, bool):
        raise ValueError("enter must be a boolean")
    settings = get_section("keyboard")
    controller = _get_controller()

    for character in str(text):
        controller.type(character)
        time.sleep(_between(settings, "type_delay_min_s", "type_delay_max_s"))

        if random.random() < float(settings["pause_chance"]):
            time.sleep(_between(settings, "pause_min_s", "pause_max_s"))

    if enter:
        press("enter")


def hotkey(*keys: str) -> None:
    """Press a key combination and release it in reverse order."""
    if not keys:
        raise ValueError("hotkey requires at least one key")
    resolved = [_resolve(key) for key in keys]
    controller = _get_controller()

    pressed: list[Any] = []
    try:
        for key in resolved:
            controller.press(key)
            pressed.append(key)
    finally:
        for key in reversed(pressed):
            controller.release(key)
