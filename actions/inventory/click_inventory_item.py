from __future__ import annotations

import math
import random
from typing import Literal

from core import mouse
from core.profile import get_section
from core.vision.api import find_all_images
from core.vision.areas import get_region
from core.vision.models import Hit


INVENTORY_AREA = "Inventory_Area"
INVENTORY_SLOTS = 28
MAXIMUM_HITS = 50

Selection = Literal["nearest", "random_slot"]


def _slot_for_hit(hit: Hit, bot_id: int) -> int | None:
    x, y = hit.center

    for slot in range(1, INVENTORY_SLOTS + 1):
        left, top, width, height = get_region(
            f"Inventory_Slot_{slot}",
            bot_id=bot_id,
        )

        if left <= x < left + width and top <= y < top + height:
            return slot

    return None


def _valid_hits(image_name: str, bot_id: int) -> list[tuple[int, Hit]]:
    hits = find_all_images(
        image_name,
        area=INVENTORY_AREA,
        bot_id=bot_id,
        maximum_hits=MAXIMUM_HITS,
    )

    by_slot: dict[int, Hit] = {}

    for hit in hits:
        slot = _slot_for_hit(hit, bot_id)
        if slot is None:
            continue

        current = by_slot.get(slot)
        if current is None or hit.shape_score > current.shape_score:
            by_slot[slot] = hit

    return list(by_slot.items())


def _select_hit(
    hits: list[tuple[int, Hit]],
    selection: Selection,
) -> tuple[int, Hit]:
    if selection == "random_slot":
        return random.choice(hits)

    if selection == "nearest":
        mouse_x, mouse_y = mouse.position()
        return min(
            hits,
            key=lambda item: math.dist((mouse_x, mouse_y), item[1].center),
        )

    raise ValueError("selection must be 'nearest' or 'random_slot'")


def click_inventory_item(
    image_name: str,
    bot_id: int = 1,
    selection: Selection = "nearest",
) -> bool:
    hits = _valid_hits(image_name, bot_id)

    if not hits:
        return False

    _, hit = _select_hit(hits, selection)
    padding = int(get_section("vision")["click_padding_px"])

    mouse.move_and_click_target(
        hit.x,
        hit.y,
        hit.x + hit.width,
        hit.y + hit.height,
        padding_px=padding,
        button="left",
    )

    return True
