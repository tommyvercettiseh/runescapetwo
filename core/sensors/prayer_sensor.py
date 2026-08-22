from __future__ import annotations

from dataclasses import dataclass

from core.sensors.prayer_stoplight import classify_prayer_frame, load_prayer_stoplight_profile
from core.vision.screenshots import capture_area


PRAYER_AREA = "Prayer_Area"


class PrayerSensorError(RuntimeError):
    """Raised when the Prayer sensor cannot classify the current state safely."""


@dataclass(frozen=True)
class PrayerReading:
    state: str
    pixels: dict[str, int]
    confidence: float

    @property
    def low(self) -> bool:
        if self.state in ("orange", "red"):
            return True
        if self.state in ("green", "yellow"):
            return False
        raise PrayerSensorError("Prayer state UNKNOWN")


def read_prayer(*, bot_id: int = 1, area: str | None = None) -> PrayerReading:
    profile = load_prayer_stoplight_profile()
    selected_area = area or str(profile.get("area", PRAYER_AREA))
    screenshot, _region = capture_area(selected_area, bot_id=bot_id)
    reading = classify_prayer_frame(screenshot)

    if reading.state == "unknown":
        raise PrayerSensorError(
            f"Prayer state UNKNOWN in {selected_area}. "
            f"Pixels: {reading.pixels} · confidence {reading.confidence:.0%}."
        )

    return PrayerReading(
        state=reading.state,
        pixels=reading.pixels,
        confidence=reading.confidence,
    )


def prayer_low(*, bot_id: int = 1, area: str | None = None) -> bool:
    """Return True for orange/red Prayer, False for green/yellow.

    UNKNOWN deliberately raises PrayerSensorError so failed detection can never
    silently be interpreted as sufficient Prayer.
    """
    return read_prayer(bot_id=bot_id, area=area).low


__all__ = [
    "PRAYER_AREA",
    "PrayerReading",
    "PrayerSensorError",
    "prayer_low",
    "read_prayer",
]
