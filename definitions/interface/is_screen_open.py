from core import vision


SCREEN_CROSS_IMAGE = "ScreenCross"
SCREEN_AREA = "Bot_Area"


def is_screen_open(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=SCREEN_CROSS_IMAGE,
        area=SCREEN_AREA,
        bot_id=bot_id,
    ) is not None
