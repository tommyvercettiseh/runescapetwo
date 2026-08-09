from core import vision
from definitions.bank.bank_target import BANK_ALL_SELECTED_IMAGE, BANK_AREA


def is_bank_all_selected(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=BANK_ALL_SELECTED_IMAGE,
        area=BANK_AREA,
        bot_id=bot_id,
    ) is not None
