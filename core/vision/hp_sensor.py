from __future__ import annotations

from dataclasses import dataclass

from core.vision.hp_stoplight import classify_hp_frame, load_hp_stoplight_profile
from core.vision.screenshots import capture_area


HP_AREA = str(load_hp_stoplight_profile().get("area", "Hp_Area"))


class HpSensorError(RuntimeError):
    """Raised when the HP sensor cannot classify the current HP state safely."""


@dataclass(frozen=True)
class HpReading:
    state: str
    pixels: dict[str, int]
    confidence: float

    @property
    def low(self) -> bool:
        if self.state in ("orange", "red"):
            return True
        if self.state in ("green", "yellow"):
            return False
        raise HpSensorError("HP state UNKNOWN")


def read_hp(*, bot_id: int = 1, area: str | None = None) -> HpReading:
    selected_area = area or str(load_hp_stoplight_profile().get("area", HP_AREA))
    screenshot, _region = capture_area(selected_area, bot_id=bot_id)
    reading = classify_hp_frame(screenshot)

    if reading.state == "unknown":
        raise HpSensorError(
            f"HP state UNKNOWN in {selected_area}. "
            f"Pixels: {reading.pixels} · confidence {reading.confidence:.0%}."
        )

    return HpReading(
        state=reading.state,
        pixels=reading.pixels,
        confidence=reading.confidence,
    )


def hp_low(*, bot_id: int = 1, area: str | None = None) -> bool:
    """Return True for orange/red HP, False for green/yellow.

    UNKNOWN deliberately raises HpSensorError so failure to see the HP number can
    never silently be interpreted as safe HP.
    """

    return read_hp(bot_id=bot_id, area=area).low


__all__ = [
    "HP_AREA",
    "HpReading",
    "HpSensorError",
    "hp_low",
    "read_hp",
]
