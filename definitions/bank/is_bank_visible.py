from core import vision


BANK_COLOUR = "cyan"
BANK_AREA = "Bot_Area"

BANK_MIN_PIXELS = 300
BANK_MAX_PIXELS = 800


def is_bank_visible(bot_id: int = 1) -> bool:
    return vision.find_colour(
        BANK_COLOUR,
        area=BANK_AREA,
        bot_id=bot_id,
        minimum_area_px=BANK_MIN_PIXELS,
        maximum_area_px=BANK_MAX_PIXELS,
    ) is not None
