from core import mouse
from core.vision.areas import get_region


SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28
CLICK_PADDING = 6


def click_inventory_slot(
    slot: int,
    bot_id: int = 1,
) -> bool:
    if slot < 1 or slot > TOTAL_SLOTS:
        raise ValueError(f"slot must be between 1 and {TOTAL_SLOTS}")

    x, y, width, height = get_region(
        f"{SLOT_PREFIX}{slot}",
        bot_id=bot_id,
    )

    mouse.move_and_click_target(
        x,
        y,
        x + width,
        y + height,
        padding_px=CLICK_PADDING,
    )
    return True
