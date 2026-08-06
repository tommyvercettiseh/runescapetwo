from definitions.inventory.get_inventory_state import get_inventory_state


def is_inventory_slot_empty(
    slot_number: int,
    bot_id: int = 1,
) -> bool:
    if slot_number < 1 or slot_number > 28:
        raise ValueError("slot_number must be between 1 and 28")

    state = get_inventory_state(bot_id)
    return not state[slot_number - 1].occupied
