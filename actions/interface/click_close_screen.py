from core import mouse_actions
from definitions.interface.screen_target import (
    SCREEN_AREA,
    SCREEN_BUTTON,
    SCREEN_CROSS_IMAGE,
    SCREEN_EDGE_PADDING,
)


def click_close_screen(bot_id: int = 1):
    return mouse_actions.click_image(
        image_name=SCREEN_CROSS_IMAGE,
        area_name=SCREEN_AREA,
        bot_id=bot_id,
        button=SCREEN_BUTTON,
        image_edge_padding=SCREEN_EDGE_PADDING,
        confirm_before_click=True,
    )
