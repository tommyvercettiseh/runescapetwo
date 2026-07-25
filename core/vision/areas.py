from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AREAS_FILE = ROOT / "config" / "areas.json"


def _validate_area(name: str, area: object) -> None:
    if name == "screen" and area is None:
        return
    if not isinstance(area, dict):
        raise ValueError(f"Area '{name}' must be an object")

    for key in ("x", "y", "width", "height"):
        value = area.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Area '{name}'.{key} must be an integer")

    if area["width"] <= 0 or area["height"] <= 0:
        raise ValueError(f"Area '{name}' must have a positive width and height")


def load_areas() -> dict[str, dict]:
    if not AREAS_FILE.exists():
        return {}
    data = json.loads(AREAS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("areas.json must contain an object")
    for name, area in data.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Area names must be non-empty strings")
        _validate_area(name, area)
    return data


def get_area(name: str | None) -> tuple[int, int, int, int] | None:
    if name is None or name == "screen":
        return None

    area = load_areas().get(name)
    if area is None:
        raise KeyError(f"Unknown area: {name}")

    return (
        int(area["x"]),
        int(area["y"]),
        int(area["width"]),
        int(area["height"]),
    )
