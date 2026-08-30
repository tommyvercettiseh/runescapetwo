from core import vision
from core.vision.object_presets import load_object_preset


def is_bank_visible(bot_id: int = 1) -> bool:
    preset = load_object_preset("bank")
    return vision.find_colour(
        preset.colour,
        area=preset.area,
        bot_id=bot_id,
        minimum_area_px=preset.min_pixels,
        maximum_area_px=preset.max_pixels,
    ) is not None
