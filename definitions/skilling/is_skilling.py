from __future__ import annotations

from core.vision.skilling_sensor import SKILLING_AREA, classify_skilling_frame
from core.vision.screenshots import capture_area


def is_skilling(bot_id: int = 1) -> bool:
    frame, _region = capture_area(SKILLING_AREA, bot_id=bot_id)
    return classify_skilling_frame(frame).skilling


__all__ = ["is_skilling"]
