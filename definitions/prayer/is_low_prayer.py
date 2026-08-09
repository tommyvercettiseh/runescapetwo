from __future__ import annotations

from core.vision.prayer_stoplight import classify_prayer_frame, load_prayer_stoplight_profile
from core.vision.screenshots import capture_area


def is_low_prayer(bot_id: int = 1) -> bool:
    """Return True when the prayer stoplight reports a configured low state."""
    profile = load_prayer_stoplight_profile()
    area = str(profile.get("area", "Prayer_Area"))
    frame, _region = capture_area(area, bot_id=bot_id)
    reading = classify_prayer_frame(frame)

    try:
        return reading.low
    except ValueError:
        return False


__all__ = ["is_low_prayer"]
