from core import vision
from core.vision.object_presets import load_object_preset
from definitions.bank.bank_target import BANK_DEPOSIT_IMAGE


def is_bank_open(bot_id: int = 1) -> bool:
    preset = load_object_preset("bank")
    return vision.find_image(
        image_name=BANK_DEPOSIT_IMAGE,
        area=preset.area,
        bot_id=bot_id,
    ) is not None
