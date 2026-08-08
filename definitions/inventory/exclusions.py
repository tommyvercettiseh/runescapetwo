from __future__ import annotations

from collections.abc import Iterable, Sequence

from definitions.inventory.constants import TOTAL_SLOTS
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from definitions.inventory.get_inventory_state import InventorySlot


def unique_image_names(values: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize configured image names while preserving their first-seen order."""
    if values is None:
        return ()
    return tuple(
        dict.fromkeys(
            value.strip()
            for value in values
            if value and value.strip()
        )
    )


def validate_inventory_slots(slots: Iterable[int]) -> set[int]:
    normalized = {int(slot) for slot in slots}
    invalid = sorted(
        slot for slot in normalized if slot < 1 or slot > TOTAL_SLOTS
    )
    if invalid:
        raise ValueError(f"exclude_slots contains invalid slots: {invalid}")
    return normalized


def resolve_inventory_exclusions(
    *,
    bot_id: int,
    explicit_slots: Iterable[int] = (),
    protected_images: Iterable[str] = (),
    optional_images: Iterable[str] = (),
) -> tuple[set[int], tuple[str, ...]]:
    """Resolve protected slots and report required images that were not found."""
    excluded = validate_inventory_slots(explicit_slots)
    missing: list[str] = []

    for image_name in unique_image_names(protected_images):
        slots = get_inventory_item_slots(image_name, bot_id)
        if not slots:
            missing.append(image_name)
        excluded.update(slots)

    for image_name in unique_image_names(optional_images):
        excluded.update(get_inventory_item_slots(image_name, bot_id))

    return excluded, tuple(missing)


def occupied_slots(
    state: Sequence[InventorySlot],
    excluded: Iterable[int] = (),
) -> list[int]:
    excluded_set = set(excluded)
    return [
        slot.number
        for slot in state
        if slot.occupied and slot.number not in excluded_set
    ]


__all__ = [
    "occupied_slots",
    "resolve_inventory_exclusions",
    "unique_image_names",
    "validate_inventory_slots",
]
