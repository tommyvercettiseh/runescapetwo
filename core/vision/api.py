from __future__ import annotations

import time

from core import mouse
from core.profile import get_section

from .image_detection import find_all_matches, find_best_match
from .models import Hit
from .screenshots import capture_area
from .templates import load_settings, load_template


def _capture_for(
    image_name: str,
    area: str | None,
    *,
    bot_id: int | None,
):
    settings = load_settings(image_name)
    selected_area = area or settings.area or "game"
    screenshot, region = capture_area(selected_area, bot_id=bot_id)
    template_rgb, template_gray = load_template(image_name)
    origin = region[0], region[1]
    return screenshot, template_rgb, template_gray, settings, origin


def find_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
) -> Hit | None:
    screenshot, template_rgb, template_gray, settings, origin = _capture_for(
        image_name,
        area,
        bot_id=bot_id,
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
    maximum_hits: int = 50,
) -> list[Hit]:
    screenshot, template_rgb, template_gray, settings, origin = _capture_for(
        image_name,
        area,
        bot_id=bot_id,
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
) -> bool:
    return find_image(
        image_name,
        area=area,
        bot_id=bot_id,
    ) is not None


def wait_for_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    timeout_s: float | None = None,
) -> Hit | None:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while time.monotonic() <= deadline:
        hit = find_image(image_name, area=area, bot_id=bot_id)
        if hit is not None:
            return hit
        time.sleep(interval)
    return None


def wait_until_gone(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    timeout_s: float | None = None,
) -> bool:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while time.monotonic() <= deadline:
        if not image_exists(image_name, area=area, bot_id=bot_id):
            return True
        time.sleep(interval)
    return False


def click_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    button: str = "left",
    wait: bool = False,
) -> bool:
    profile = get_section("vision")
    hit = (
        wait_for_image(image_name, area=area, bot_id=bot_id)
        if wait
        else find_image(image_name, area=area, bot_id=bot_id)
    )

    if hit is None:
        return False

    padding = int(profile["click_padding_px"])
    mouse.move_and_click_target(
        hit.x,
        hit.y,
        hit.x + hit.width,
        hit.y + hit.height,
        padding_px=padding,
        button=button,
    )
    return True
