from __future__ import annotations

from dataclasses import dataclass

from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from definitions.inventory.get_inventory_state import InventorySlot, get_inventory_state


TOTAL_SLOTS = 28
DEMO_OCCUPIED_SLOTS = {1, 2, 5, 8, 9, 13, 20, 27}
DEMO_IMAGE_SLOTS = {5, 13}


@dataclass(frozen=True)
class InventoryCheckResult:
    slots: tuple[InventorySlot, ...]
    image_name: str = ""
    image_slots: tuple[int, ...] = ()
    demo: bool = False

    @property
    def occupied_count(self) -> int:
        return sum(slot.occupied for slot in self.slots)

    @property
    def empty_count(self) -> int:
        return len(self.slots) - self.occupied_count

    @property
    def full(self) -> bool:
        return bool(self.slots) and all(slot.occupied for slot in self.slots)

    @property
    def empty(self) -> bool:
        return not any(slot.occupied for slot in self.slots)


def check_inventory(
    bot_id: int = 1,
    image_name: str = "",
) -> InventoryCheckResult:
    slots = tuple(get_inventory_state(bot_id))
    cleaned_image_name = image_name.strip()
    image_slots = (
        tuple(sorted(get_inventory_item_slots(cleaned_image_name, bot_id)))
        if cleaned_image_name
        else ()
    )
    return InventoryCheckResult(
        slots=slots,
        image_name=cleaned_image_name,
        image_slots=image_slots,
    )


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
