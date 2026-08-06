from definitions.inventory.get_inventory_state import get_inventory_state


def is_inventory_empty(bot_id: int = 1) -> bool:
    return not any(slot.occupied for slot in get_inventory_state(bot_id))
