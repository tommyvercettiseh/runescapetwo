from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AREAS_FILE = ROOT / "config" / "areas.json"


@dataclass(frozen=True)
class EditableArea:
    name: str
    x: int
    y: int
    width: int
    height: int
    group: str = "default"

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.width, self.y + self.height


def _parse(name: str, value: object) -> EditableArea | None:
    if value is None:
        return None
    group = "default"
    if isinstance(value, dict):
        group = str(value.get("group", "default")).strip() or "default"
        if all(key in value for key in ("x", "y", "width", "height")):
            x, y = int(value["x"]), int(value["y"])
            width, height = int(value["width"]), int(value["height"])
        elif isinstance(value.get("coords"), list) and len(value["coords"]) == 4:
            x, y, x2, y2 = map(int, value["coords"])
            width, height = x2 - x, y2 - y
        else:
            return None
    elif isinstance(value, list) and len(value) == 4:
        x, y, x2, y2 = map(int, value)
        width, height = x2 - x, y2 - y
    else:
        return None
    if width <= 0 or height <= 0:
        return None
    return EditableArea(name, x, y, width, height, group)


def load_editable_areas(path: Path = AREAS_FILE) -> dict[str, EditableArea]:
    raw = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
    if not isinstance(raw, dict):
        raise ValueError("areas.json must contain an object")
    result: dict[str, EditableArea] = {}
    for name, value in raw.items():
        area = _parse(str(name), value)
        if area is not None:
            result[area.name] = area
    return result


def save_editable_areas(areas: dict[str, EditableArea], path: Path = AREAS_FILE) -> None:
    payload = {
        name: {
            "x": area.x,
            "y": area.y,
            "width": area.width,
            "height": area.height,
            "group": area.group,
        }
        for name, area in sorted(areas.items(), key=lambda item: item[0].lower())
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, path)
