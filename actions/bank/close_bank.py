import time

from actions.interface.click_close_screen import click_close_screen
from definitions.bank.is_bank_closed import is_bank_closed


BANK_CLOSE_TIMEOUT = 3.0
BANK_CHECK_INTERVAL = 0.20
BANK_CLOSED_CONFIRMATIONS = 3


def close_bank(
    bot_id: int = 1,
    seconds: float = BANK_CLOSE_TIMEOUT,
) -> bool:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    if is_bank_closed(bot_id):
        return True

    if not click_close_screen(bot_id):
        return False

    deadline = time.monotonic() + seconds
    confirmations = 0

    while time.monotonic() < deadline:
        if is_bank_closed(bot_id):
            confirmations += 1

            if confirmations >= BANK_CLOSED_CONFIRMATIONS:
                return True
        else:
            confirmations = 0

        time.sleep(BANK_CHECK_INTERVAL)

    return False
