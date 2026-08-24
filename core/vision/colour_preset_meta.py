from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path

from .colour_presets import HSV, HSVRange, normalize_colour_name

ROOT = Path(__file__).resolve().parents[2]
META_FILE = ROOT / "config" / "colour_preset_meta.json"


@dataclass(frozen=True)
class ColourPresetMeta:
    tolerance: int
    colours: tuple[HSV, ...] | None


def infer_base_colours(ranges: tuple[HSVRange, ...]) -> tuple[HSV, ...]:
    """Infer editable HSV centres when legacy metadata does not exist."""
    return tuple(
        (
            round((int(lower[0]) + int(upper[0])) / 2),
            round((int(lower[1]) + int(upper[1])) / 2),
            round((int(lower[2]) + int(upper[2])) / 2),
        )
        for lower, upper in ranges
    )


def _read_raw() -> dict[str, object]:
    try:
        data = json.loads(META_FILE.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_raw(data: dict[str, object]) -> None:
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = META_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, META_FILE)


def _parse_colour(value: object) -> HSV | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    try:
        hue, saturation, brightness = (int(part) for part in value)
    except (TypeError, ValueError):
        return None
    if not (0 <= hue <= 179 and 0 <= saturation <= 255 and 0 <= brightness <= 255):
        return None
    return hue, saturation, brightness


def load_colour_preset_meta(name: str) -> ColourPresetMeta | None:
    normalized = normalize_colour_name(name)
    raw = _read_raw().get(normalized)
    if not isinstance(raw, dict):
        return None

    colours_raw = raw.get("colours")
    colours = (
        tuple(
            colour
            for colour in (_parse_colour(item) for item in colours_raw)
            if colour is not None
        )
        if isinstance(colours_raw, list)
        else None
    )

    try:
        tolerance = int(raw.get("tolerance", 35))
    except (TypeError, ValueError):
        tolerance = 35

    return ColourPresetMeta(
        tolerance=min(100, max(0, tolerance)),
        colours=colours,
    )


def save_colour_preset_meta(
    name: str,
    *,
    tolerance: int,
    colours: list[HSV] | tuple[HSV, ...],
) -> None:
    normalized = normalize_colour_name(name)
    data = _read_raw()
    data[normalized] = {
        "tolerance": min(100, max(0, int(tolerance))),
        "colours": [list(colour) for colour in colours],
    }
    _write_raw(data)


def snapshot_colour_preset_meta(name: str) -> dict[str, object] | None:
    """Return an exact raw snapshot so undo can restore legacy metadata losslessly."""
    normalized = normalize_colour_name(name)
    raw = _read_raw().get(normalized)
    return deepcopy(raw) if isinstance(raw, dict) else None


def restore_colour_preset_meta(
    name: str,
    snapshot: dict[str, object] | None,
) -> None:
    """Restore a previously captured metadata snapshot exactly."""
    normalized = normalize_colour_name(name)
    data = _read_raw()
    if snapshot is None:
        data.pop(normalized, None)
    else:
        data[normalized] = deepcopy(snapshot)
    _write_raw(data)


def delete_colour_preset_meta(name: str) -> bool:
    normalized = normalize_colour_name(name)
    data = _read_raw()
    if normalized not in data:
        return False
    data.pop(normalized, None)
    _write_raw(data)
    return True


__all__ = [
    "ColourPresetMeta",
    "delete_colour_preset_meta",
    "infer_base_colours",
    "load_colour_preset_meta",
    "restore_colour_preset_meta",
    "save_colour_preset_meta",
    "snapshot_colour_preset_meta",
]
