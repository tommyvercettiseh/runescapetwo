from __future__ import annotations

from dataclasses import dataclass

from core.vision.hp_stoplight import classify_hp_frame
from core.vision.screenshots import capture_area


HP_AREA = "Hp_Area"


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


def read_hp(*, bot_id: int = 1, area: str = HP_AREA) -> HpReading:
    screenshot, _region = capture_area(area, bot_id=bot_id)
    reading = classify_hp_frame(screenshot)

    if reading.state == "unknown":
        raise HpSensorError(
            f"HP state UNKNOWN in {area}. "
            f"Pixels: {reading.pixels} · confidence {reading.confidence:.0%}."
        )

    return HpReading(
        state=reading.state,
        pixels=reading.pixels,
        confidence=reading.confidence,
    )


def hp_low(*, bot_id: int = 1, area: str = HP_AREA) -> bool:
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
