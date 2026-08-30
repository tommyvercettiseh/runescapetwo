from __future__ import annotations

from core import mouse_actions
from core.vision.object_presets import load_object_preset


def click_object(name: str, bot_id: int = 1):
    preset = load_object_preset(name)
    return mouse_actions.click_colour(
        colour_name=preset.colour,
        area_name=preset.area,
        bot_id=bot_id,
        button=preset.button,
        minimum_blob_pixels=preset.min_pixels,
        maximum_blob_pixels=preset.max_pixels,
        blob_edge_padding=preset.edge_padding,
    )


__all__ = ["click_object"]
