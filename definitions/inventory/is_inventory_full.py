from definitions.inventory.get_inventory_state import get_inventory_state


def is_inventory_full(bot_id: int = 1) -> bool:
    return all(slot.occupied for slot in get_inventory_state(bot_id))
