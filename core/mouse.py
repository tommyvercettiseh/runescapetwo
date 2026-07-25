from __future__ import annotations

import random
import time
from typing import Any

from .bots import to_screen_point, validate_screen_point
from .movements import create_path
from .profile import get_section
from .windows import enable_dpi_awareness

_controller: Any | None = None


def _get_controller() -> Any:
    global _controller
    if _controller is None:
        enable_dpi_awareness()
        from pynput.mouse import Controller

        _controller = Controller()
    return _controller


def _between(settings: dict, minimum: str, maximum: str) -> float:
    return random.uniform(float(settings[minimum]), float(settings[maximum]))


def _resolve_button(button: str):
    from pynput.mouse import Button

    buttons = {"left": Button.left, "right": Button.right, "middle": Button.middle}
    try:
        return buttons[str(button).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown mouse button: {button}") from exc


def move_to(
    x: int,
    y: int,
    method: str | None = None,
    *,
    bot_id: int | None = None,
) -> None:
    """Move to an absolute point or a bot-relative point when bot_id is given."""
    settings = get_section("mouse")
    controller = _get_controller()
    start = tuple(map(int, controller.position))
    target = (
        to_screen_point(x, y, bot_id=bot_id)
        if bot_id is not None
        else validate_screen_point(x, y)
    )

    movement_method = (
        method or str(settings["movement_method"])
    ).strip().lower()
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
        controller.position = point
        time.sleep(step_delay)


def click(button: str = "left") -> None:
    """Click using the delays from the active profile."""
    settings = get_section("mouse")
    selected = _resolve_button(button)

    time.sleep(_between(settings, "pre_click_min_s", "pre_click_max_s"))
    controller = _get_controller()
    controller.press(selected)
    try:
        time.sleep(_between(settings, "click_hold_min_s", "click_hold_max_s"))
    finally:
        controller.release(selected)
    time.sleep(_between(settings, "post_click_min_s", "post_click_max_s"))


def move_and_click(
    x: int,
    y: int,
    button: str = "left",
    *,
    bot_id: int | None = None,
) -> None:
    move_to(x, y, bot_id=bot_id)
    click(button)


def click_at(
    x: int,
    y: int,
    button: str = "left",
    *,
    bot_id: int | None = None,
) -> None:
    move_and_click(x, y, button, bot_id=bot_id)


def scroll(amount: int) -> None:
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("Scroll amount must be an integer")
    settings = get_section("mouse")
    direction = 1 if amount > 0 else -1
    controller = _get_controller()

    for _ in range(abs(amount)):
        controller.scroll(0, direction)
        time.sleep(_between(settings, "scroll_delay_min_s", "scroll_delay_max_s"))


def position() -> tuple[int, int]:
    return tuple(map(int, _get_controller().position))
