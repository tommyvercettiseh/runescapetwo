from core import vision
from definitions.interface.screen_target import SCREEN_AREA, SCREEN_CROSS_IMAGE


def is_screen_open(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=SCREEN_CROSS_IMAGE,
        area=SCREEN_AREA,
        bot_id=bot_id,
    ) is not None
