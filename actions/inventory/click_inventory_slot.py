from core import mouse_actions
from definitions.inventory.constants import SLOT_PREFIX, TOTAL_SLOTS


CLICK_PADDING = 6


def click_inventory_slot(
    slot: int,
    bot_id: int = 1,
) -> mouse_actions.MouseActionResult:
    if slot < 1 or slot > TOTAL_SLOTS:
        raise ValueError(f"slot must be between 1 and {TOTAL_SLOTS}")

    return mouse_actions.click_in_area(
        area_name=f"{SLOT_PREFIX}{slot}",
        bot_id=bot_id,
        button="left",
        area_edge_padding=CLICK_PADDING,
        require_external_mouse=True,
    )
