import time

from core import keyboard
from definitions.bank.is_bank_open import is_bank_open


BANK_CLOSE_KEY = "esc"
BANK_CLOSE_TIMEOUT = 2.0
BANK_CHECK_INTERVAL = 0.20


def close_bank(
    bot_id: int = 1,
    seconds: float = BANK_CLOSE_TIMEOUT,
) -> bool:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    if not is_bank_open(bot_id):
        return True

    keyboard.press(BANK_CLOSE_KEY)

    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        if not is_bank_open(bot_id):
            return True

        time.sleep(BANK_CHECK_INTERVAL)

    return False
