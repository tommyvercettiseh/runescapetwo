from __future__ import annotations

import numpy as np

from core.bots import get_screen_size
from core.windows import enable_dpi_awareness


def capture_rgb(region: tuple[int, int, int, int] | None = None) -> np.ndarray:
    enable_dpi_awareness()
    import pyautogui

    actual_size = tuple(map(int, pyautogui.size()))
    configured_size = get_screen_size()
    if actual_size != configured_size:
        raise RuntimeError(
            "Configured screen size "
            f"{configured_size} does not match Windows {actual_size}"
        )

    if region is not None:
        x, y, width, height = region
        if (
            x < 0
            or y < 0
            or width < 1
            or height < 1
            or x + width > actual_size[0]
            or y + height > actual_size[1]
        ):
            raise ValueError("Screenshot region falls outside the screen")

    image = pyautogui.screenshot(region=region)
    return np.asarray(image)
