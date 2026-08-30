from __future__ import annotations

from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots


def has_inventory_image(
    image_name: str,
    count: int = 1,
    bot_id: int = 1,
) -> bool:
    if count < 1:
        raise ValueError("count must be at least 1")

    return len(get_inventory_item_slots(image_name, bot_id)) >= count


__all__ = ["has_inventory_image"]
