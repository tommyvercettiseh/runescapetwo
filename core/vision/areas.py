from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AREAS_FILE = ROOT / "config" / "areas.json"


def load_areas() -> dict[str, dict]:
    if not AREAS_FILE.exists():
        return {}
    data = json.loads(AREAS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("areas.json must contain an object")
    return data


def get_area(name: str | None) -> tuple[int, int, int, int] | None:
    if name is None or name == "screen":
        return None

    area = load_areas().get(name)
    if not isinstance(area, dict):
        raise KeyError(f"Unknown area: {name}")

    return (
        int(area["x"]),
        int(area["y"]),
        int(area["width"]),
        int(area["height"]),
    )
