import time

from actions.camera.turn_camera import CameraDirection, turn_camera
from definitions.bank.is_bank_visible import is_bank_visible


BANK_SEARCH_DIRECTION: CameraDirection = "right"
BANK_SEARCH_ATTEMPTS = 8
BANK_TURN_SECONDS = 0.20
BANK_CHECK_DELAY = 0.15


def find_bank(
    bot_id: int = 1,
    direction: CameraDirection = BANK_SEARCH_DIRECTION,
    attempts: int = BANK_SEARCH_ATTEMPTS,
    turn_seconds: float = BANK_TURN_SECONDS,
) -> bool:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    if is_bank_visible(bot_id):
        return True

    for _ in range(attempts):
        turn_camera(
            direction=direction,
            seconds=turn_seconds,
        )
        time.sleep(BANK_CHECK_DELAY)

        if is_bank_visible(bot_id):
            return True

    return False
