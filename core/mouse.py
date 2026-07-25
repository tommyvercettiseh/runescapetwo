from __future__ import annotations

import random
import time

from pynput.mouse import Button, Controller

from .movements import create_path
from .profile import get_section

_controller = Controller()


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def move_to(x: int, y: int, method: str | None = None) -> None:
    """Move to a point using the active profile."""
    settings = get_section("mouse")
    start = tuple(map(int, _controller.position))
    target = (int(x), int(y))

    movement_method = method or str(settings["movement_method"])
    steps = random.randint(int(settings["steps_min"]), int(settings["steps_max"]))
    duration = _between(settings, "duration_min_s", "duration_max_s")
    movement_settings = settings.get("movement_settings", {}).get(movement_method, {})
    path = create_path(
        movement_method,
        start,
        target,
        steps,
        movement_settings,
    )

    step_delay = duration / max(1, len(path))
    for point in path:
        _controller.position = point
        time.sleep(step_delay)


def click(button: str = "left") -> None:
    """Click using the delays from the active profile."""
    settings = get_section("mouse")
    selected = Button.left if button == "left" else Button.right

    time.sleep(_between(settings, "pre_click_min_s", "pre_click_max_s"))
    _controller.press(selected)
    time.sleep(_between(settings, "click_hold_min_s", "click_hold_max_s"))
    _controller.release(selected)
    time.sleep(_between(settings, "post_click_min_s", "post_click_max_s"))


def move_and_click(x: int, y: int, button: str = "left") -> None:
    move_to(x, y)
    click(button)


def scroll(amount: int) -> None:
    settings = get_section("mouse")
    direction = 1 if amount > 0 else -1

    for _ in range(abs(int(amount))):
        _controller.scroll(0, direction)
        time.sleep(_between(settings, "scroll_delay_min_s", "scroll_delay_max_s"))


def position() -> tuple[int, int]:
    return tuple(map(int, _controller.position))
