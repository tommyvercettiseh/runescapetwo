from __future__ import annotations

from core.vision.api import find_all_images
from core.vision.areas import get_region
from core.vision.models import Hit


INVENTORY_AREA = "Inventory_Area"
SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28


def _overlap_area(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> int:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second

    left = max(first_x, second_x)
    top = max(first_y, second_y)
    right = min(first_x + first_width, second_x + second_width)
    bottom = min(first_y + first_height, second_y + second_height)
    return max(0, right - left) * max(0, bottom - top)


def _slot_for_hit(hit: Hit, bot_id: int) -> int | None:
    hit_region = hit.x, hit.y, hit.width, hit.height
    best_slot: int | None = None
    best_overlap = 0

    for slot in range(1, TOTAL_SLOTS + 1):
        slot_region = get_region(
            f"{SLOT_PREFIX}{slot}",
            bot_id=bot_id,
        )
        overlap = _overlap_area(hit_region, slot_region)
        if overlap > best_overlap:
            best_slot = slot
            best_overlap = overlap

    return best_slot


def get_inventory_item_slots(
    image_name: str,
    bot_id: int = 1,
) -> set[int]:
    hits = find_all_images(
        image_name,
        area=INVENTORY_AREA,
        bot_id=bot_id,
    )

    slots = set()
    for hit in hits:
        slot = _slot_for_hit(hit, bot_id)
        if slot is not None:
            slots.add(slot)

    return slots
