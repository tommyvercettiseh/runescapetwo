from __future__ import annotations

from core.vision.api import find_all_images
from core.vision.areas import get_region


INVENTORY_AREA = "Inventory_Area"
SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28


def _slot_for_point(x: int, y: int, bot_id: int) -> int | None:
    for slot in range(1, TOTAL_SLOTS + 1):
        left, top, width, height = get_region(
            f"{SLOT_PREFIX}{slot}",
            bot_id=bot_id,
        )
        if left <= x < left + width and top <= y < top + height:
            return slot
    return None


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
        x, y = hit.center
        slot = _slot_for_point(x, y, bot_id)
        if slot is not None:
            slots.add(slot)

    return slots
