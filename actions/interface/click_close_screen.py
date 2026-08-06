from core import mouse_actions


SCREEN_CROSS_IMAGE = "ScreenCross"
SCREEN_AREA = "Bot_Area"

SCREEN_BUTTON = "left"
SCREEN_EDGE_PADDING = 20


def click_close_screen(bot_id: int = 1):
    return mouse_actions.click_image(
        image_name=SCREEN_CROSS_IMAGE,
        area_name=SCREEN_AREA,
        bot_id=bot_id,
        button=SCREEN_BUTTON,
        image_edge_padding=SCREEN_EDGE_PADDING,
        confirm_before_click=True,
    )
