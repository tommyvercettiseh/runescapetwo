from core import mouse_actions


FURNACE_COLOUR = "purple"
FURNACE_AREA = "Bot_Area"
FURNACE_MIN_PIXELS = 250
FURNACE_MAX_PIXELS = 4000
FURNACE_EDGE_PADDING = 20
FURNACE_BUTTON = "left"


def click_furnace(bot_id: int = 1):
    return mouse_actions.click_colour(
        colour_name=FURNACE_COLOUR,
        area_name=FURNACE_AREA,
        bot_id=bot_id,
        button=FURNACE_BUTTON,
        minimum_blob_pixels=FURNACE_MIN_PIXELS,
        maximum_blob_pixels=FURNACE_MAX_PIXELS,
        blob_edge_padding=FURNACE_EDGE_PADDING,
    )
