from __future__ import annotations

from typing import Literal

from . import mouse
from .targeting import area_target_bounds, image_target_bounds
from .vision.api import find_image, wait_for_image
from .vision.areas import get_region
from .vision.models import Hit


DEFAULT_AREA_NAME = "Bot_Area_Full"
MouseButton = Literal["left", "right"]


def _validate_button(button: str) -> MouseButton:
    if button == "left":
        return "left"
    if button == "right":
        return "right"
    raise ValueError("button must be 'left' or 'right'")


def _find_target_image(
    image_name: str,
    *,
    area_name: str,
    bot_id: int,
    wait: bool,
    timeout_seconds: float | None,
) -> Hit | None:
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if wait:
        return wait_for_image(
            image_name,
            area=area_name,
            bot_id=bot_id,
            timeout_s=timeout_seconds,
        )
    return find_image(image_name, area=area_name, bot_id=bot_id)


# Example in scripts:
# from core import mouse_actions
#
# mouse_actions.move_to_image(
#     "Logs",
#     area_name="Bot_Area_Full",
#     bot_id=1,
#     image_edge_padding=20,  # Percentage aan beide horizontale randen
# )
def move_to_image(
    image_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    image_edge_padding: float = 20,
    wait: bool = False,
    timeout_seconds: float | None = None,
) -> bool:
    """Find an image and move to its horizontally safe inner bounding box."""
    hit = _find_target_image(
        image_name,
        area_name=area_name,
        bot_id=bot_id,
        wait=wait,
        timeout_seconds=timeout_seconds,
    )
    if hit is None:
        return False

    left, top, right, bottom = image_target_bounds(
        hit.x,
        hit.y,
        hit.x + hit.width,
        hit.y + hit.height,
        image_edge_padding=image_edge_padding,
    )
    mouse.move_to_target(left, top, right, bottom)
    return True


# Example in scripts:
# from core import mouse_actions
#
# mouse_actions.click_image(
#     "Logs",
#     area_name="Bot_Area_Full",
#     bot_id=1,
#     button="right",
#     image_edge_padding=20,  # Percentage aan beide horizontale randen
# )
def click_image(
    image_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    button: MouseButton = "left",
    image_edge_padding: float = 20,
    wait: bool = False,
    timeout_seconds: float | None = None,
) -> bool:
    """Find an image and click inside its horizontally safe inner bbox."""
    selected_button = _validate_button(button)
    hit = _find_target_image(
        image_name,
        area_name=area_name,
        bot_id=bot_id,
        wait=wait,
        timeout_seconds=timeout_seconds,
    )
    if hit is None:
        return False

    left, top, right, bottom = image_target_bounds(
        hit.x,
        hit.y,
        hit.x + hit.width,
        hit.y + hit.height,
        image_edge_padding=image_edge_padding,
    )
    mouse.move_and_click_target(
        left,
        top,
        right,
        bottom,
        button=selected_button,
    )
    return True


# Example in scripts:
# from core import mouse_actions
#
# mouse_actions.move_to_area(
#     "Inventory_Area",
#     bot_id=1,
#     area_edge_padding=8,  # Pixels aan alle randen
# )
def move_to_area(
    area_name: str,
    *,
    bot_id: int = 1,
    area_edge_padding: int = 0,
) -> None:
    """Move to a safe target inside one configured bot area."""
    x, y, width, height = get_region(area_name, bot_id=bot_id)
    left, top, right, bottom = area_target_bounds(
        x,
        y,
        x + width,
        y + height,
        area_edge_padding=area_edge_padding,
    )
    mouse.move_to_target(left, top, right, bottom)


# Example in scripts:
# from core import mouse_actions
#
# mouse_actions.click_in_area(
#     "Inventory_Area",
#     bot_id=1,
#     button="right",
#     area_edge_padding=8,  # Pixels aan alle randen
# )
def click_in_area(
    area_name: str,
    *,
    bot_id: int = 1,
    button: MouseButton = "left",
    area_edge_padding: int = 0,
) -> None:
    """Click inside one configured bot area."""
    selected_button = _validate_button(button)
    x, y, width, height = get_region(area_name, bot_id=bot_id)
    left, top, right, bottom = area_target_bounds(
        x,
        y,
        x + width,
        y + height,
        area_edge_padding=area_edge_padding,
    )
    mouse.move_and_click_target(
        left,
        top,
        right,
        bottom,
        button=selected_button,
    )


__all__ = [
    "MouseButton",
    "move_to_image",
    "click_image",
    "move_to_area",
    "click_in_area",
]
