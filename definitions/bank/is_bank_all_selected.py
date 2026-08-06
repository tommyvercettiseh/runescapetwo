from core import vision


BANK_ALL_SELECTED_IMAGE = "BankAllSelected"
BANK_AREA = "Bot_Area"


def is_bank_all_selected(bot_id: int = 1) -> bool:
    return vision.find_image(
        image_name=BANK_ALL_SELECTED_IMAGE,
        area=BANK_AREA,
        bot_id=bot_id,
    ) is not None
