from __future__ import annotations

import os
import time

from definitions.inventory.get_inventory_state import (
    EMPTY_THRESHOLD,
    get_inventory_state,
)


BOT_ID = 1
REFRESH_SECONDS = 0.50


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _slot_text(slot) -> str:
    marker = "VOL" if slot.occupied else "LEEG"
    percentage = slot.background_percentage * 100
    return f"{slot.number:02d} {marker:4} {percentage:5.1f}%"


def main() -> None:
    while True:
        state = get_inventory_state(BOT_ID)
        _clear()

        print(f"Inventory checker | bot {BOT_ID}")
        print(f"Leeg wanneer achtergrond >= {EMPTY_THRESHOLD * 100:.1f}%")
        print("Ctrl+C om te stoppen\n")

        for row in range(7):
            slots = state[row * 4 : (row + 1) * 4]
            print(" | ".join(_slot_text(slot) for slot in slots))

        occupied = sum(slot.occupied for slot in state)
        print(f"\nBezet: {occupied}/28 | Leeg: {28 - occupied}/28")
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
