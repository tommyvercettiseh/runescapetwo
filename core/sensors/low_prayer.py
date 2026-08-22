from __future__ import annotations

import cv2
import numpy as np

from core.sensors.prayer_sensor import PrayerSensorError, prayer_low
from core.sensors.prayer_stoplight import classify_prayer_frame, load_prayer_stoplight_profile


SENSOR_NAME = "low_prayer"
SENSOR_AREA = "Prayer_Area"


def low_prayer(*, bot_id: int = 1) -> bool:
    """Return True when Prayer is low, False when Prayer is sufficient."""
    return prayer_low(bot_id=bot_id, area=SENSOR_AREA)


def analyse_frame(frame_rgb: np.ndarray) -> dict[str, object]:
    """Analyse one already-captured Prayer frame for the Unified Sensor tester."""
    reading = classify_prayer_frame(frame_rgb)
    if reading.state == "unknown":
        raise PrayerSensorError(
            f"Prayer state UNKNOWN. Pixels: {reading.pixels} · confidence {reading.confidence:.0%}."
        )

    profile = load_prayer_stoplight_profile()
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    candidate = (
        (sat >= int(profile.get("min_saturation", 105)))
        & (val >= int(profile.get("min_value", 130)))
    )

    state_mask = np.zeros(candidate.shape, dtype=bool)
    for low, high in profile.get("hue_ranges", {}).get(reading.state, []):
        state_mask |= candidate & (hue >= int(low)) & (hue <= int(high))

    mask = state_mask.astype(np.uint8) * 255
    detected = cv2.bitwise_and(frame_rgb, frame_rgb, mask=mask)
    found = int(reading.pixels.get(reading.state, 0))
    required = int(profile.get("min_colour_pixels", 3))

    return {
        "detected": detected,
        "found": found,
        "required": required,
        "result": reading.state in set(profile.get("low_states", ["orange", "red"])),
        "unit": f"{reading.state} px",
    }


__all__ = [
    "SENSOR_AREA",
    "SENSOR_NAME",
    "analyse_frame",
    "low_prayer",
]
