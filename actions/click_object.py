from core import mouse_actions


OBJECT_COLOUR = "purple"
OBJECT_AREA = "Bot_Area"
OBJECT_MIN_PIXELS = 20
OBJECT_MAX_PIXELS = None
OBJECT_EDGE_PADDING = 20
OBJECT_BUTTON = "left"


def click_object(bot_id: int = 1):
    return mouse_actions.click_colour(
        colour_name=OBJECT_COLOUR,
        area_name=OBJECT_AREA,
        bot_id=bot_id,
        button=OBJECT_BUTTON,
        minimum_blob_pixels=OBJECT_MIN_PIXELS,
        maximum_blob_pixels=OBJECT_MAX_PIXELS,
        blob_edge_padding=OBJECT_EDGE_PADDING,
    )
