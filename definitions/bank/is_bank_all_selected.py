from core import vision
from core.vision.object_presets import load_object_preset
from definitions.bank.bank_target import BANK_ALL_SELECTED_IMAGE


def is_bank_all_selected(bot_id: int = 1) -> bool:
    preset = load_object_preset("bank")
    return vision.find_image(
        image_name=BANK_ALL_SELECTED_IMAGE,
        area=preset.area,
        bot_id=bot_id,
    ) is not None
