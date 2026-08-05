from __future__ import annotations

import sys

import numpy as np
import pyautogui
from PIL import ImageGrab

from .areas import get_region
from .offsets import Region


def capture_rgb(region: Region) -> np.ndarray:
    """Capture one absolute desktop region as RGB."""
    if sys.platform == "win32":
        left, top, width, height = region
        image = np.asarray(
            ImageGrab.grab(
                bbox=(left, top, left + width, top + height),
                all_screens=True,
            )
        )
    else:
        image = np.asarray(pyautogui.screenshot(region=region))
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    return image


def capture_area(
    area: str | None = "game",
    bot_id: int | None = None,
) -> tuple[np.ndarray, Region]:
    """Capture one local bot-1 area after applying the selected bot offset."""
    region = get_region(area, bot_id=bot_id)
    return capture_rgb(region), region
