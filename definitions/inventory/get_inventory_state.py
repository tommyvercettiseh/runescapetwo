from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from core.vision.areas import get_region
from core.vision.screenshots import capture_area


INVENTORY_AREA = "Inventory_Area"
SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28

BACKGROUND_HSV_RANGES = [
    ((8, 38, 44), (21, 87, 100)),
]

EMPTY_THRESHOLD = 0.90


@dataclass(frozen=True)
class InventorySlot:
    number: int
    occupied: bool
    background_percentage: float

    @property
    def empty(self) -> bool:
        return not self.occupied

    @property
    def foreground_percentage(self) -> float:
        return max(0.0, min(1.0, 1.0 - self.background_percentage))

    @property
    def status(self) -> str:
        return "OCCUPIED" if self.occupied else "EMPTY"


def _background_percentage(image_rgb: np.ndarray) -> float:
    if image_rgb.size == 0:
        raise ValueError("Cannot analyse an empty inventory slot image")

    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    for lower, upper in BACKGROUND_HSV_RANGES:
        current = cv2.inRange(
            hsv,
            np.array(lower, dtype=np.uint8),
            np.array(upper, dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask, current)

    return float(np.count_nonzero(mask)) / float(mask.size)


def _relative_slot_bounds(
    number: int,
    *,
    area_region: tuple[int, int, int, int],
    bot_id: int,
) -> tuple[int, int, int, int]:
    area_x, area_y, area_width, area_height = area_region
    x, y, width, height = get_region(
        f"{SLOT_PREFIX}{number}",
        bot_id=bot_id,
    )

    left = x - area_x
    top = y - area_y
    right = left + width
    bottom = top + height

    if (
        left < 0
        or top < 0
        or right > area_width
        or bottom > area_height
    ):
        raise ValueError(
            f"Inventory slot {number} falls outside {INVENTORY_AREA}: "
            f"slot=({x}, {y}, {width}, {height}), "
            f"area=({area_x}, {area_y}, {area_width}, {area_height})"
        )

    return left, top, width, height


def get_inventory_state(
    bot_id: int = 1,
    *,
    empty_threshold: float = EMPTY_THRESHOLD,
) -> list[InventorySlot]:
    threshold = float(empty_threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Inventory empty threshold must be between 0 and 1")

    inventory, area_region = capture_area(
        INVENTORY_AREA,
        bot_id=bot_id,
    )
    area_x, area_y, area_width, area_height = area_region

    if inventory.shape[1] != area_width or inventory.shape[0] != area_height:
        raise ValueError(
            f"Captured {INVENTORY_AREA} has unexpected size: "
            f"{inventory.shape[1]}x{inventory.shape[0]}, "
            f"expected {area_width}x{area_height}"
        )

    state: list[InventorySlot] = []
    for number in range(1, TOTAL_SLOTS + 1):
        left, top, width, height = _relative_slot_bounds(
            number,
            area_region=area_region,
            bot_id=bot_id,
        )
        slot_image = inventory[top : top + height, left : left + width]
        background = _background_percentage(slot_image)
        state.append(
            InventorySlot(
                number=number,
                occupied=background < threshold,
                background_percentage=background,
            )
        )

    return state
