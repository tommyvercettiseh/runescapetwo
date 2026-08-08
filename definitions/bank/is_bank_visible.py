from core import vision
from definitions.bank.bank_target import (
    BANK_AREA,
    BANK_COLOUR,
    BANK_MAX_PIXELS,
    BANK_MIN_PIXELS,
)


def is_bank_visible(bot_id: int = 1) -> bool:
    return vision.find_colour(
        BANK_COLOUR,
        area=BANK_AREA,
        bot_id=bot_id,
        minimum_area_px=BANK_MIN_PIXELS,
        maximum_area_px=BANK_MAX_PIXELS,
    ) is not None
