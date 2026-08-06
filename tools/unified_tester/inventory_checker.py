from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    image_error: str = ""
    demo: bool = False

    def __post_init__(self) -> None:
        numbers = tuple(slot.number for slot in self.slots)
        expected = tuple(range(1, TOTAL_SLOTS + 1))
        if numbers != expected:
            raise ValueError(
                "Inventory result must contain slots 1 through 28 in order"
            )

        invalid_image_slots = [
            number
            for number in self.image_slots
            if number < 1 or number > TOTAL_SLOTS
        ]
        if invalid_image_slots:
            raise ValueError(
                f"Invalid inventory image slots: {invalid_image_slots}"
            )

    @property
    def detected_occupied_slots(self) -> tuple[int, ...]:
        return tuple(slot.number for slot in self.slots if slot.occupied)

    @property
    def occupied_slots(self) -> tuple[int, ...]:
        return tuple(
            sorted(set(self.detected_occupied_slots).union(self.image_slots))
        )

    @property
    def empty_slots(self) -> tuple[int, ...]:
        occupied = set(self.occupied_slots)
        return tuple(
            number
            for number in range(1, TOTAL_SLOTS + 1)
            if number not in occupied
        )

    @property
    def occupied_count(self) -> int:
        return len(self.occupied_slots)

    @property
    def empty_count(self) -> int:
        return len(self.empty_slots)

    @property
    def full(self) -> bool:
        return self.occupied_count == TOTAL_SLOTS

    @property
    def empty(self) -> bool:
        return self.occupied_count == 0

    @property
    def image_found(self) -> bool:
        return bool(self.image_slots)

    @property
    def image_scan_ok(self) -> bool:
        return not self.image_error

    def is_slot_occupied(self, number: int) -> bool:
        return int(number) in set(self.occupied_slots)

    def slot_status(self, number: int) -> str:
        if number in self.image_slots:
            return "IMAGE"
        return "OCCUPIED" if self.is_slot_occupied(number) else "EMPTY"

    def as_dict(self) -> dict[str, Any]:
        image_slots = set(self.image_slots)
        occupied_slots = set(self.occupied_slots)
        return {
            "occupied_count": self.occupied_count,
            "empty_count": self.empty_count,
            "full": self.full,
            "empty": self.empty,
            "occupied_slots": list(self.occupied_slots),
            "empty_slots": list(self.empty_slots),
            "image_name": self.image_name,
            "image_slots": list(self.image_slots),
            "image_found": self.image_found,
            "image_error": self.image_error,
            "demo": self.demo,
            "slots": [
                {
                    "number": slot.number,
                    "status": (
                        "IMAGE"
                        if slot.number in image_slots
                        else "OCCUPIED"
                        if slot.number in occupied_slots
                        else "EMPTY"
                    ),
                    "occupied": slot.number in occupied_slots,
                    "image_match": slot.number in image_slots,
                    "background_percentage": slot.background_percentage,
                    "foreground_percentage": slot.foreground_percentage,
                }
                for slot in self.slots
            ],
        }


def check_inventory(
    bot_id: int = 1,
    image_name: str = "",
    *,
    strict_image: bool = False,
) -> InventoryCheckResult:
    slots = tuple(get_inventory_state(bot_id))
    cleaned_image_name = image_name.strip()
    image_slots: tuple[int, ...] = ()
    image_error = ""

    if cleaned_image_name:
        try:
            image_slots = tuple(
                sorted(get_inventory_item_slots(cleaned_image_name, bot_id))
            )
        except Exception as exc:
            if strict_image:
                raise
            image_error = f"{type(exc).__name__}: {exc}"

    return InventoryCheckResult(
        slots=slots,
        image_name=cleaned_image_name,
        image_slots=image_slots,
        image_error=image_error,
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
