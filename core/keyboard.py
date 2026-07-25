from __future__ import annotations

import random
import time

from pynput.keyboard import Controller, Key

from .profile import get_section

_controller: Controller | None = None


def _get_controller() -> Controller:
    global _controller
    if _controller is None:
        _controller = Controller()
    return _controller

_SPECIAL_KEYS = {
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


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def _resolve(key: str):
    clean_key = str(key).strip().lower()
    return _SPECIAL_KEYS.get(clean_key, key)


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
    time.sleep(_between(settings, "press_hold_min_s", "press_hold_max_s"))
    controller.release(resolved)


def hold(key: str, duration_s: float | None = None) -> None:
    """Hold one key. A supplied duration overrides the profile."""
    settings = get_section("keyboard")
    resolved = _resolve(key)
    duration = duration_s

    if duration is None:
        duration = _between(settings, "press_hold_min_s", "press_hold_max_s")
    if float(duration) < 0:
        raise ValueError("Hold duration cannot be negative")

    controller = _get_controller()
    controller.press(resolved)
    time.sleep(float(duration))
    controller.release(resolved)


def type_text(text: str, enter: bool = False) -> None:
    """Type text using profile-driven intervals and optional pauses."""
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

    for key in resolved:
        controller.press(key)

    for key in reversed(resolved):
        controller.release(key)
