from __future__ import annotations

import random

from core import keyboard, mouse
from core.vision.areas import get_region
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from definitions.inventory.get_inventory_state import get_inventory_state

from .click_inventory_slot import click_inventory_slot


DEFAULT_PATTERN = "random_pattern"
FIXED_PATTERNS = ("row", "snake", "column", "column_snake")
SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28


def _pattern_order(pattern: str, rng: random.Random) -> list[int]:
    rows = [list(range(start, start + 4)) for start in range(1, 29, 4)]
    columns = [[row[column] for row in rows] for column in range(4)]

    if pattern == "row":
        return list(range(1, 29))
    if pattern == "snake":
        return [
            slot
            for index, row in enumerate(rows)
            for slot in (row if index % 2 == 0 else reversed(row))
        ]
    if pattern == "column":
        return [slot for column in columns for slot in column]
    if pattern == "column_snake":
        return [
            slot
            for index, column in enumerate(columns)
            for slot in (column if index % 2 == 0 else reversed(column))
        ]
    if pattern == "random":
        order = list(range(1, 29))
        rng.shuffle(order)
        return order
    if pattern == "random_pattern":
        return _pattern_order(rng.choice(FIXED_PATTERNS), rng)

    raise ValueError(
        "pattern must be row, snake, column, column_snake, random or random_pattern"
    )


def _nearest_order(slots: set[int], bot_id: int) -> list[int]:
    remaining = set(slots)
    current_x, current_y = mouse.position()
    order = []

    while remaining:
        slot = min(
            remaining,
            key=lambda number: _distance_to_slot(
                number,
                current_x,
                current_y,
                bot_id,
            ),
        )
        x, y, width, height = get_region(
            f"{SLOT_PREFIX}{slot}",
            bot_id=bot_id,
        )
        current_x = x + width // 2
        current_y = y + height // 2
        order.append(slot)
        remaining.remove(slot)

    return order


def _distance_to_slot(
    slot: int,
    x: int,
    y: int,
    bot_id: int,
) -> int:
    left, top, width, height = get_region(
        f"{SLOT_PREFIX}{slot}",
        bot_id=bot_id,
    )
    center_x = left + width // 2
    center_y = top + height // 2
    return (center_x - x) ** 2 + (center_y - y) ** 2


def _resolve_excluded_slots(
    exclude_slots: set[int],
    protected_images: list[str],
    optional_images: list[str],
    bot_id: int,
) -> tuple[set[int], tuple[str, ...]]:
    invalid = sorted(
        slot for slot in exclude_slots if slot < 1 or slot > TOTAL_SLOTS
    )
    if invalid:
        raise ValueError(f"exclude_slots contains invalid slots: {invalid}")

    excluded = set(exclude_slots)
    missing: list[str] = []

    for image_name in protected_images:
        slots = get_inventory_item_slots(image_name, bot_id)
        if not slots:
            missing.append(image_name)
        excluded.update(slots)

    for image_name in optional_images:
        excluded.update(get_inventory_item_slots(image_name, bot_id))

    return excluded, tuple(missing)


def drop_inventory(
    bot_id: int = 1,
    *,
    exclude_slots: set[int] | None = None,
    exclude_images: list[str] | None = None,
    optional_exclude_images: list[str] | None = None,
    pattern: str = DEFAULT_PATTERN,
    seed: int | None = None,
    dry_run: bool = False,
) -> bool:
    excluded, missing = _resolve_excluded_slots(
        set(exclude_slots or set()),
        list(dict.fromkeys(exclude_images or [])),
        list(dict.fromkeys(optional_exclude_images or [])),
        bot_id,
    )

    if missing:
        print(
            "Drop inventory gestopt; beschermde images niet gevonden: "
            + ", ".join(missing)
        )
        return False

    occupied = {
        slot.number
        for slot in get_inventory_state(bot_id)
        if slot.occupied and slot.number not in excluded
    }

    if not occupied:
        return True

    if pattern == "nearest":
        order = _nearest_order(occupied, bot_id)
    else:
        order = [
            slot
            for slot in _pattern_order(pattern, random.Random(seed))
            if slot in occupied
        ]

    if dry_run:
        print(f"Drop slots: {order} | Excluded: {sorted(excluded)}")
        return True

    keyboard.key_down("shift")
    try:
        for slot in order:
            if not click_inventory_slot(slot, bot_id):
                return False
    finally:
        keyboard.key_up("shift")

    remaining = {
        slot.number
        for slot in get_inventory_state(bot_id)
        if slot.occupied and slot.number not in excluded
    }
    return not remaining
