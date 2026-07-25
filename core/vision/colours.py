from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COLOURS_FILE = ROOT / "config" / "colours.json"


@dataclass(frozen=True)
class ColourSettings:
    ranges: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...]
    min_blob_px: int
    padding_px: int


def _integer(value: object, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}")
    return value


def _hsv(value: object, name: str) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must contain [hue, saturation, value]")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError(f"{name} values must be integers")

    hue, saturation, brightness = value
    if not 0 <= hue <= 179:
        raise ValueError(f"{name} hue must be between 0 and 179")
    if not 0 <= saturation <= 255 or not 0 <= brightness <= 255:
        raise ValueError(f"{name} saturation and value must be between 0 and 255")
    return hue, saturation, brightness


def _ranges(value: object, name: str):
    if not isinstance(value, list) or not value:
        raise ValueError(f"Colour '{name}'.ranges must be a non-empty list")

    result = []
    for index, item in enumerate(value):
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(
                f"Colour '{name}'.ranges[{index}] must contain lower and upper HSV"
            )
        lower = _hsv(item[0], f"Colour '{name}'.ranges[{index}].lower")
        upper = _hsv(item[1], f"Colour '{name}'.ranges[{index}].upper")
        if any(low > high for low, high in zip(lower, upper)):
            raise ValueError(
                f"Colour '{name}'.ranges[{index}] lower cannot exceed upper"
            )
        result.append((lower, upper))
    return tuple(result)


def load_colours() -> dict[str, ColourSettings]:
    if not COLOURS_FILE.exists():
        raise FileNotFoundError(f"Colour configuration not found: {COLOURS_FILE}")

    data = json.loads(COLOURS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("colours.json must contain an object")

    defaults = data.get("_defaults")
    if not isinstance(defaults, dict):
        raise ValueError("colours.json requires _defaults")
    default_min_blob = _integer(defaults.get("min_blob_px"), "_defaults.min_blob_px", 1)
    default_padding = _integer(defaults.get("padding_px"), "_defaults.padding_px", 0)

    colours: dict[str, ColourSettings] = {}
    for name, value in data.items():
        if name.startswith("_"):
            continue
        valid_name = (
            isinstance(name, str)
            and bool(name.strip())
            and name == name.strip().lower()
        )
        if not valid_name:
            raise ValueError(
                "Colour names must be lowercase without surrounding spaces"
            )
        if not isinstance(value, dict):
            raise ValueError(f"Colour '{name}' must be an object")
        colours[name] = ColourSettings(
            ranges=_ranges(value.get("ranges"), name),
            min_blob_px=_integer(
                value.get("min_blob_px", default_min_blob),
                f"Colour '{name}'.min_blob_px",
                1,
            ),
            padding_px=_integer(
                value.get("padding_px", default_padding),
                f"Colour '{name}'.padding_px",
                0,
            ),
        )

    if not colours:
        raise ValueError("colours.json must configure at least one colour")
    return colours


def load_colour(name: str) -> ColourSettings:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Colour name must be a non-empty string")
    clean_name = name.strip().lower()
    try:
        return load_colours()[clean_name]
    except KeyError as exc:
        raise KeyError(f"Unknown colour: {clean_name}") from exc
