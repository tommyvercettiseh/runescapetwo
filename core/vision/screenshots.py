from __future__ import annotations

from collections.abc import Callable
import sys

import numpy as np
import pyautogui
from PIL import ImageGrab

from .areas import get_region
from .offsets import Region


_CAPTURE_BEFORE: list[Callable[[], None]] = []
_CAPTURE_AFTER: list[Callable[[], None]] = []


def register_capture_hooks(
    *,
    before: Callable[[], None] | None = None,
    after: Callable[[], None] | None = None,
) -> Callable[[], None]:
    """Register explicit observers around desktop capture.

    This is an extension point, not a method replacement: production callers
    still use capture_rgb/capture_area normally. The Vision Tester uses it only
    to hide debug overlays on Windows systems that reject native capture
    exclusion.
    """
    if before is not None and before not in _CAPTURE_BEFORE:
        _CAPTURE_BEFORE.append(before)
    if after is not None and after not in _CAPTURE_AFTER:
        _CAPTURE_AFTER.append(after)

    def unregister() -> None:
        if before is not None:
            try:
                _CAPTURE_BEFORE.remove(before)
            except ValueError:
                pass
        if after is not None:
            try:
                _CAPTURE_AFTER.remove(after)
            except ValueError:
                pass

    return unregister


def _run_hooks(callbacks: list[Callable[[], None]]) -> None:
    for callback in tuple(callbacks):
        try:
            callback()
        except Exception:
            # Debug observers must never be able to break production capture.
            pass


def capture_rgb(region: Region) -> np.ndarray:
    """Capture one absolute desktop region as RGB."""
    _run_hooks(_CAPTURE_BEFORE)
    try:
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
    finally:
        _run_hooks(list(reversed(_CAPTURE_AFTER)))

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
