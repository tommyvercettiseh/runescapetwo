from __future__ import annotations

from dataclasses import dataclass

from core.vision.colour_detection import build_mask_from_ranges, count_mask_pixels
from core.vision.colour_presets import load_colour_preset
from core.vision.screenshots import capture_area


HP_AREA = "Hp_Area"
HP_COLOURS = (
    "hp_green",
    "hp_yellow",
    "hp_orange",
    "hp_red",
)
LOW_STATES = {"hp_orange", "hp_red"}
SAFE_STATES = {"hp_green", "hp_yellow"}
MIN_MATCH_PIXELS = 3
AMBIGUITY_RATIO = 0.85


class HpSensorError(RuntimeError):
    """Raised when the HP sensor cannot classify the current HP state safely."""


@dataclass(frozen=True)
class HpReading:
    state: str
    pixels: dict[str, int]

    @property
    def low(self) -> bool:
        if self.state in LOW_STATES:
            return True
        if self.state in SAFE_STATES:
            return False
        raise HpSensorError(f"Unknown HP state: {self.state}")


def read_hp(*, bot_id: int = 1, area: str = HP_AREA) -> HpReading:
    screenshot, _region = capture_area(area, bot_id=bot_id)

    scores: dict[str, int] = {}
    for colour_name in HP_COLOURS:
        try:
            preset = load_colour_preset(colour_name)
        except (KeyError, ValueError) as exc:
            raise HpSensorError(
                f"HP colour preset ontbreekt: {colour_name}. "
                "Maak deze eerst vanuit de raw HP recording."
            ) from exc

        mask = build_mask_from_ranges(screenshot, preset.ranges)
        scores[colour_name] = count_mask_pixels(mask)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winner, winner_pixels = ranked[0]
    runner_pixels = ranked[1][1] if len(ranked) > 1 else 0

    if winner_pixels < MIN_MATCH_PIXELS:
        raise HpSensorError(
            f"HP state UNKNOWN in {area}: geen colour haalt {MIN_MATCH_PIXELS} pixels. "
            f"Scores: {scores}"
        )

    if runner_pixels >= winner_pixels * AMBIGUITY_RATIO:
        raise HpSensorError(
            f"HP state UNKNOWN in {area}: meerdere colours matchen bijna even sterk. "
            f"Scores: {scores}"
        )

    return HpReading(state=winner, pixels=scores)


def hp_low(*, bot_id: int = 1, area: str = HP_AREA) -> bool:
    """Return True when HP is orange/red, False when green/yellow.

    UNKNOWN is deliberately raised as HpSensorError instead of being treated as
    False, so a broken/missing colour detection can never silently mean 'safe'.
    """

    return read_hp(bot_id=bot_id, area=area).low


__all__ = [
    "HP_AREA",
    "HP_COLOURS",
    "HpReading",
    "HpSensorError",
    "hp_low",
    "read_hp",
]
