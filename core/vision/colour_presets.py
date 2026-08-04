from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRESETS_FILE = ROOT / "config" / "colour_presets.json"

HSV = tuple[int, int, int]
HSVRange = tuple[HSV, HSV]


@dataclass(frozen=True)
class ColourPreset:
    name: str
    ranges: tuple[HSVRange, ...]


_PRESET_CACHE: dict[str, ColourPreset] | None = None
_PRESET_STAMP: int | None = None


def normalize_colour_name(name: str) -> str:
    normalized = str(name).strip().lower()
    if not normalized:
        raise ValueError("Colour preset name cannot be empty")
    return normalized


def _validate_hsv(value, label: str) -> HSV:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three HSV values")
    h, s, v = (int(part) for part in value)
    if not 0 <= h <= 179 or not 0 <= s <= 255 or not 0 <= v <= 255:
        raise ValueError(f"{label} contains an out-of-range HSV value")
    return h, s, v


def _parse_ranges(item: object) -> tuple[HSVRange, ...]:
    if not isinstance(item, dict):
        raise ValueError("Each colour preset must be an object")

    raw_ranges = item.get("ranges")
    if raw_ranges is None and "lower" in item and "upper" in item:
        raw_ranges = [{"lower": item["lower"], "upper": item["upper"]}]

    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise ValueError("A colour preset must contain at least one HSV range")

    ranges: list[HSVRange] = []
    for index, raw_range in enumerate(raw_ranges):
        if not isinstance(raw_range, dict):
            raise ValueError(f"Range {index} must be an object")
        lower = _validate_hsv(raw_range.get("lower"), f"Range {index} lower")
        upper = _validate_hsv(raw_range.get("upper"), f"Range {index} upper")
        if any(low > high for low, high in zip(lower, upper)):
            raise ValueError(f"Range {index} lower values must not exceed upper values")
        ranges.append((lower, upper))
    return tuple(ranges)


def clear_colour_preset_cache() -> None:
    global _PRESET_CACHE, _PRESET_STAMP
    _PRESET_CACHE = None
    _PRESET_STAMP = None


def load_colour_presets() -> dict[str, ColourPreset]:
    global _PRESET_CACHE, _PRESET_STAMP

    stamp = PRESETS_FILE.stat().st_mtime_ns if PRESETS_FILE.exists() else -1
    if _PRESET_CACHE is not None and _PRESET_STAMP == stamp:
        return _PRESET_CACHE

    if not PRESETS_FILE.exists():
        raw_data: object = {}
    else:
        raw_data = json.loads(PRESETS_FILE.read_text(encoding="utf-8-sig") or "{}")

    if not isinstance(raw_data, dict):
        raise ValueError("colour_presets.json must contain an object")

    presets: dict[str, ColourPreset] = {}
    for raw_name, item in raw_data.items():
        name = normalize_colour_name(raw_name)
        presets[name] = ColourPreset(name=name, ranges=_parse_ranges(item))

    _PRESET_CACHE = presets
    _PRESET_STAMP = stamp
    return presets


def list_colour_presets() -> tuple[str, ...]:
    return tuple(sorted(load_colour_presets()))


def load_colour_preset(name: str) -> ColourPreset:
    normalized = normalize_colour_name(name)
    try:
        return load_colour_presets()[normalized]
    except KeyError as exc:
        raise KeyError(f"Unknown colour preset: {name}") from exc


def save_colour_preset(name: str, ranges: tuple[HSVRange, ...] | list[HSVRange]) -> None:
    normalized = normalize_colour_name(name)
    validated = _parse_ranges(
        {
            "ranges": [
                {"lower": list(lower), "upper": list(upper)}
                for lower, upper in ranges
            ]
        }
    )

    current = {
        preset_name: {
            "ranges": [
                {"lower": list(lower), "upper": list(upper)}
                for lower, upper in preset.ranges
            ]
        }
        for preset_name, preset in load_colour_presets().items()
    }
    current[normalized] = {
        "ranges": [
            {"lower": list(lower), "upper": list(upper)}
            for lower, upper in validated
        ]
    }

    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = PRESETS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, PRESETS_FILE)
    clear_colour_preset_cache()


def delete_colour_preset(name: str) -> bool:
    normalized = normalize_colour_name(name)
    presets = load_colour_presets()
    if normalized not in presets:
        return False

    remaining = {
        preset_name: {
            "ranges": [
                {"lower": list(lower), "upper": list(upper)}
                for lower, upper in preset.ranges
            ]
        }
        for preset_name, preset in presets.items()
        if preset_name != normalized
    }

    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = PRESETS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(remaining, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, PRESETS_FILE)
    clear_colour_preset_cache()
    return True
