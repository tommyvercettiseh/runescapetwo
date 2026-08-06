from __future__ import annotations

import random

from core import mouse
from definitions.bank.is_bank_open import is_bank_open
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from definitions.inventory.get_inventory_state import get_inventory_state
from actions.inventory.click_inventory_slot import click_inventory_slot


def _excluded_slots(images: list[str], bot_id: int) -> set[int]:
    excluded: set[int] = set()
    for image_name in images:
        excluded.update(get_inventory_item_slots(image_name, bot_id))
    return excluded


def _pick_slot(slots: list[int], selection: str, bot_id: int) -> int:
    if selection == "random_slot":
        return random.choice(slots)
    if selection != "nearest":
        raise ValueError("selection must be nearest or random_slot")

    mouse_x, mouse_y = mouse.position()

    def distance(slot: int) -> int:
        from core.vision.areas import get_region

        x, y, width, height = get_region(f"Inventory_Slot_{slot}", bot_id=bot_id)
        center_x = x + width // 2
        center_y = y + height // 2
        return (center_x - mouse_x) ** 2 + (center_y - mouse_y) ** 2

    return min(slots, key=distance)


def bank_inventory(
    bot_id: int = 1,
    *,
    exclude_images: list[str] | None = None,
    selection: str = "nearest",
    dry_run: bool = False,
) -> bool:
    if not is_bank_open(bot_id):
        return False

    images = list(exclude_images or [])

    for _ in range(28):
        excluded = _excluded_slots(images, bot_id)
        candidates = [
            slot.number
            for slot in get_inventory_state(bot_id)
            if slot.occupied and slot.number not in excluded
        ]

        if not candidates:
            return True

        slot = _pick_slot(candidates, selection, bot_id)

        if dry_run:
            print(f"Bank slot: {slot} | Excluded: {sorted(excluded)}")
            return True

        if not click_inventory_slot(slot, bot_id):
            return False

    return False
