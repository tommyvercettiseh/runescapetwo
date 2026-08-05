from core import vision
from core.definition_config import get_definition


def is_bank_open(bot_id: int = 1) -> bool:
    config = get_definition("bank", "is_bank_open")

    return vision.find_image(
        image_name=str(config["image"]),
        area=str(config["area"]),
        bot_id=bot_id,
    ) is not None
