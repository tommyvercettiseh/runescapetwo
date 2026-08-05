from core import vision


BANK_DEPOSIT_IMAGE = "Bank_Deposit"
BANK_AREA = "Bot_Area"


def is_bank_open(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=BANK_DEPOSIT_IMAGE,
        area=BANK_AREA,
        bot_id=bot_id,
    ) is not None
