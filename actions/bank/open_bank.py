import time

from actions.bank.click_bank import click_bank
from actions.bank.find_bank import find_bank
from definitions.bank.is_bank_open import is_bank_open


BANK_OPEN_TIMEOUT = 6.0
BANK_CHECK_INTERVAL = 0.20


def open_bank(
    bot_id: int = 1,
    seconds: float = BANK_OPEN_TIMEOUT,
) -> bool:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    if is_bank_open(bot_id):
        return True

    if not find_bank(bot_id):
        return False

    if not click_bank(bot_id):
        return False

    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        if is_bank_open(bot_id):
            return True

        time.sleep(BANK_CHECK_INTERVAL)

    return False
