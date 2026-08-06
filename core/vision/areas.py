from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .offsets import Region, apply_offset

ROOT = Path(__file__).resolve().parents[2]
AREAS_FILE = ROOT / "config" / "areas.json"

_SCREEN_ALIASES = {"screen", "fullscreen", "full", "full_screen"}
_AREA_ALIASES = {
    # The 28 Inventory_Slot_* regions live inside this canonical crop.
    # Keep the older generic `inventory` placeholder available separately.
    "inventoryarea": "Inventory_Area_Pattern",
}


def load_areas() -> dict[str, Any]:
    if not AREAS_FILE.exists():
        raise FileNotFoundError(f"Areas file not found: {AREAS_FILE}")

    data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("areas.json must contain an object")
    return data


def _normalize_name(name: str) -> str:
    return "".join(character for character in str(name).lower() if character.isalnum())


def _name_candidates(name: str) -> tuple[str, ...]:
    normalized = _normalize_name(name)
    candidates = [normalized]

    # Allows both `inventory` and the old RuneScape-style `Inventory_Area`.
    if normalized.endswith("area"):
        candidates.append(normalized[:-4])
    else:
        candidates.append(f"{normalized}area")

    return tuple(dict.fromkeys(candidates))


def _find_area_value(name: str, areas: dict[str, Any]) -> tuple[str, Any]:
    if name in areas:
        return name, areas[name]

    normalized = _normalize_name(name)
    aliased_name = _AREA_ALIASES.get(normalized)
    if aliased_name is not None:
        if aliased_name not in areas:
            raise KeyError(
                f"Area alias '{name}' points to missing area: {aliased_name}"
            )
        return aliased_name, areas[aliased_name]

    candidates = set(_name_candidates(name))
    for stored_name, value in areas.items():
        if _normalize_name(stored_name) in candidates:
            return stored_name, value

    raise KeyError(f"Unknown area: {name}")


def _coords_to_region(name: str, coords: Any) -> Region:
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        raise ValueError(f"Area '{name}' requires four coordinates")

    x1, y1, x2, y2 = map(int, coords)
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        raise ValueError(f"Area '{name}' has invalid coordinates: {coords!r}")
    return x1, y1, width, height


def _value_to_region(name: str, value: Any) -> Region:
    if isinstance(value, dict):
        if all(key in value for key in ("x", "y", "width", "height")):
            region = (
                int(value["x"]),
                int(value["y"]),
                int(value["width"]),
                int(value["height"]),
            )
        elif "coords" in value:
            region = _coords_to_region(name, value["coords"])
        else:
            raise ValueError(f"Area '{name}' has no supported coordinate format")
    else:
        region = _coords_to_region(name, value)

    if region[2] <= 0 or region[3] <= 0:
        raise ValueError(f"Area '{name}' must have a positive width and height")
    return region


def get_area(name: str | None = "game") -> Region:
    """Return one local region, measured once on bot 1."""
    requested = "game" if name is None else str(name).strip()
    if _normalize_name(requested) in {_normalize_name(alias) for alias in _SCREEN_ALIASES}:
        requested = "game"

    stored_name, value = _find_area_value(requested, load_areas())
    return _value_to_region(stored_name, value)


def get_region(name: str | None = "game", bot_id: int | None = None) -> Region:
    """Return one area's absolute desktop region for the selected bot."""
    return apply_offset(get_area(name), bot_id=bot_id)
