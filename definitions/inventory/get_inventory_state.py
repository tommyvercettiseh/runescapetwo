from __future__ import annotations

from dataclasses import dataclass

import cv2
import mss
import numpy as np

from core.vision.areas import get_region


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


def _background_percentage(image: np.ndarray) -> float:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    for lower, upper in BACKGROUND_HSV_RANGES:
        current = cv2.inRange(
            hsv,
            np.array(lower, dtype=np.uint8),
            np.array(upper, dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask, current)

    return float(np.count_nonzero(mask)) / float(mask.size)


def get_inventory_state(bot_id: int = 1) -> list[InventorySlot]:
    area_x, area_y, area_width, area_height = get_region(
        INVENTORY_AREA,
        bot_id=bot_id,
    )

    with mss.mss() as capture:
        screenshot = np.array(
            capture.grab(
                {
                    "left": area_x,
                    "top": area_y,
                    "width": area_width,
                    "height": area_height,
                }
            )
        )

    inventory = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
    state = []

    for number in range(1, TOTAL_SLOTS + 1):
        x, y, width, height = get_region(
            f"{SLOT_PREFIX}{number}",
            bot_id=bot_id,
        )

        left = x - area_x
        top = y - area_y
        slot_image = inventory[top : top + height, left : left + width]

        if slot_image.size == 0:
            raise ValueError(f"Inventory slot {number} falls outside Inventory_Area")

        background = _background_percentage(slot_image)
        state.append(
            InventorySlot(
                number=number,
                occupied=background < EMPTY_THRESHOLD,
                background_percentage=background,
            )
        )

    return state
