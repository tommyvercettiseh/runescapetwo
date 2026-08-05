from core import vision
from core.definition_config import get_definition


def find_bank(bot_id: int = 1):
    config = get_definition("bank", "find_bank")

    return vision.find_colour(
        str(config["colour"]),
        area=str(config["area"]),
        bot_id=bot_id,
        minimum_area_px=int(config["minimum_area_px"]),
        maximum_area_px=int(config["maximum_area_px"]),
    )
