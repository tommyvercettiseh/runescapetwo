from __future__ import annotations

import time

from core import mouse
from core.profile import get_section

from .areas import get_area
from .image_detection import find_all_matches, find_best_match
from .models import Hit
from .offsets import apply_offset, resolve_offset
from .screenshots import capture_rgb
from .templates import load_settings, load_template


def _capture_for(
    image_name: str,
    area: str | None,
    *,
    bot_id: int | None,
    offset: tuple[int, int] | None,
):
    settings = load_settings(image_name)
    selected_area = area if area is not None else settings.area
    resolved_offset = resolve_offset(bot_id=bot_id, offset=offset)

    # Areas stay local. Only the screenshot boundary becomes absolute.
    region = apply_offset(get_area(selected_area), resolved_offset)
    screenshot = capture_rgb(region)
    origin = (0, 0) if region is None else (region[0], region[1])
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
        image_name,
        area,
        bot_id=bot_id,
        offset=offset,
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
        image_name,
        area,
        bot_id=bot_id,
        offset=offset,
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
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    # Keep the same bot context for every retry.
    while time.monotonic() <= deadline:
        hit = find_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )
        if hit is not None:
            return hit
        time.sleep(interval)
    return None


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
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while time.monotonic() <= deadline:
        if not image_exists(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        ):
            return True
        time.sleep(interval)
    return False


def click_image(
    image_name: str,
    *,
    area: str | None = None,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
    button: str = "left",
    wait: bool = False,
) -> bool:
    profile = get_section("vision")
    if wait:
        hit = wait_for_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )
    else:
        hit = find_image(
            image_name,
            area=area,
            bot_id=bot_id,
            offset=offset,
        )

    if hit is None:
        return False

    point = hit.random_point(int(profile["click_padding_px"]))
    mouse.move_to(*point)
    mouse.click(button)
    return True
