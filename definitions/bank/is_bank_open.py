from core import vision
from definitions.bank.bank_target import BANK_AREA, BANK_DEPOSIT_IMAGE


def is_bank_open(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=BANK_DEPOSIT_IMAGE,
        area=BANK_AREA,
        bot_id=bot_id,
    ) is not None
