from __future__ import annotations

import numpy as np


def capture_rgb(region: tuple[int, int, int, int] | None = None) -> np.ndarray:
    import pyautogui

    image = pyautogui.screenshot(region=region)
    return np.asarray(image)
