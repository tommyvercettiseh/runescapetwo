from __future__ import annotations

from core.vision.hp_stoplight import classify_hp_frame, load_hp_stoplight_profile
from core.vision.screenshots import capture_area


def is_low_hp(bot_id: int = 1) -> bool:
    """Return True when the HP stoplight reports a configured low state."""
    profile = load_hp_stoplight_profile()
    area = str(profile.get("area", "Hp_Area"))
    frame, _region = capture_area(area, bot_id=bot_id)
    reading = classify_hp_frame(frame)

    try:
        return reading.low
    except ValueError:
        return False


__all__ = ["is_low_hp"]
