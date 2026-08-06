from core import mouse_actions


BANK_COLOUR = "cyan"
BANK_AREA = "Bot_Area"
BANK_MIN_PIXELS = 300
BANK_MAX_PIXELS = 800
BANK_EDGE_PADDING = 20
BANK_BUTTON = "left"


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
