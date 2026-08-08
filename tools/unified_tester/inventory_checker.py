from __future__ import annotations

from definitions.inventory.check_inventory import (
    InventoryCheckResult,
    TOTAL_SLOTS,
    check_inventory,
)
from definitions.inventory.get_inventory_state import InventorySlot


DEMO_OCCUPIED_SLOTS = {1, 2, 5, 8, 9, 13, 20, 27}
DEMO_IMAGE_SLOTS = {5, 13}


def demo_inventory(image_name: str = "Item_Axe") -> InventoryCheckResult:
    cleaned_image_name = image_name.strip() or "Item_Axe"
    slots = tuple(
        InventorySlot(
            number=number,
            occupied=number in DEMO_OCCUPIED_SLOTS,
            background_percentage=(
                0.25 if number in DEMO_OCCUPIED_SLOTS else 0.98
            ),
        )
        for number in range(1, TOTAL_SLOTS + 1)
    )
    return InventoryCheckResult(
        slots=slots,
        image_name=cleaned_image_name,
        image_slots=tuple(sorted(DEMO_IMAGE_SLOTS)),
        demo=True,
    )


__all__ = [
    "InventoryCheckResult",
    "TOTAL_SLOTS",
    "check_inventory",
    "demo_inventory",
]
