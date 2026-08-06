from definitions.bank.is_bank_open import is_bank_open
from definitions.interface.is_screen_open import is_screen_open


def is_bank_closed(bot_id: int = 1) -> bool:
    return (
        not is_bank_open(bot_id)
        and not is_screen_open(bot_id)
    )
