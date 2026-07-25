from __future__ import annotations

import time

from core.profile import get_section

from .areas import get_area as get_base_area
from .detection import find_all_matches, find_best_match
from .models import Hit
from .offsets import apply_offset
from .screenshots import capture_rgb
from .templates import load_settings, load_template


def get_area(
    name: str | None,
    *,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
) -> tuple[int, int, int, int]:
    region = apply_offset(
        get_base_area(name),
        bot_id=bot_id,
        offset=offset,
    )
    return region


def _capture_for(
    image_name: str,
    area: str | None,
    bot_id: int | None,
    offset: tuple[int, int] | None,
):
    settings = load_settings(image_name)
    selected_area = area if area is not None else settings.area
    region = get_area(selected_area, bot_id=bot_id, offset=offset)
    screenshot = capture_rgb(region)
    origin = region[0], region[1]
    template_rgb, template_gray = load_template(image_name)
    return screenshot, template_rgb, template_gray, settings, origin


def find_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
) -> Hit | None:
    screenshot, template_rgb, template_gray, settings, origin = _capture_for(
        image_name, area, bot_id, offset
    )
    return find_best_match(
        screenshot,
        template_rgb,
        template_gray,
        settings,
        origin,
    )


def find_all_images(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    maximum_hits: int = 50,
) -> list[Hit]:
    screenshot, template_rgb, template_gray, settings, origin = _capture_for(
        image_name, area, bot_id, offset
    )
    return find_all_matches(
        screenshot,
        template_rgb,
        template_gray,
        settings,
        origin,
        maximum_hits,
    )


def image_exists(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
) -> bool:
    return find_image(
        image_name,
        area=area,
        bot_id=bot_id,
        offset=offset,
    ) is not None


def wait_for_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    timeout_s: float | None = None,
) -> Hit | None:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    if timeout < 0:
        raise ValueError("timeout_s cannot be negative")
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while True:
        hit = find_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )
        if hit is not None:
            return hit
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(interval, remaining))


def wait_until_gone(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    timeout_s: float | None = None,
) -> bool:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    if timeout < 0:
        raise ValueError("timeout_s cannot be negative")
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while True:
        if not image_exists(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        ):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(interval, remaining))


def move_to_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    wait: bool = False,
    anchor: str = "random",
    padding: int | None = None,
    dx: int = 0,
    dy: int = 0,
) -> tuple[int, int] | None:
    from core import mouse

    profile = get_section("vision")
    hit = (
        wait_for_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )
        if wait
        else find_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )
    )
    if hit is None:
        return None

    selected_padding = (
        int(profile["click_padding_px"])
        if padding is None
        else int(padding)
    )
    x, y = hit.point(anchor=anchor, padding=selected_padding)
    point = x + int(dx), y + int(dy)
    mouse.move_to(*point)
    return point


def click_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    button: str = "left",
    wait: bool = False,
    anchor: str = "random",
    padding: int | None = None,
    dx: int = 0,
    dy: int = 0,
) -> bool:
    from core import mouse

    point = move_to_image(
        image_name,
        area=area,
        bot_id=bot_id,
        offset=offset,
        wait=wait,
        anchor=anchor,
        padding=padding,
        dx=dx,
        dy=dy,
    )
    if point is None:
        return False

    mouse.click(button)
    return True
