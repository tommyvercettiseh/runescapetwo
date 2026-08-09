from core import mouse_actions
from definitions.bank.bank_target import (
    BANK_AREA,
    BANK_BUTTON,
    BANK_COLOUR,
    BANK_EDGE_PADDING,
    BANK_MAX_PIXELS,
    BANK_MIN_PIXELS,
)


def click_bank(bot_id: int = 1):
    return mouse_actions.click_colour(
        colour_name=BANK_COLOUR,
        area_name=BANK_AREA,
        bot_id=bot_id,
        button=BANK_BUTTON,
        minimum_blob_pixels=BANK_MIN_PIXELS,
        maximum_blob_pixels=BANK_MAX_PIXELS,
        blob_edge_padding=BANK_EDGE_PADDING,
    )
