from __future__ import annotations

import numpy as np
import pyautogui


def capture_rgb(region: tuple[int, int, int, int] | None = None) -> np.ndarray:
    image = pyautogui.screenshot(region=region)
    return np.asarray(image)
