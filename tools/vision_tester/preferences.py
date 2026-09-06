from __future__ import annotations

import json
import os
from pathlib import Path

from .enhanced_config import MAX_ZOOM_PERCENT, MIN_ZOOM_PERCENT


DEFAULT_PREFERENCES = {
    "auto_resize": True,
    "zoom_percent": 100,
    "mouse_trace": False,
}
DEFAULT_WINDOW_GEOMETRY = "1180x760"


def preferences_path() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "RuneScapeTwo" / "vision_tester.json"


def _load_raw(path: Path) -> dict[str, object]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(loaded, dict):
            return loaded
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return {}


def _save_raw(values: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(values, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_preferences(path: Path | None = None) -> dict[str, object]:
    target = preferences_path() if path is None else path
    data = _load_raw(target)

    zoom = data.get("zoom_percent", DEFAULT_PREFERENCES["zoom_percent"])
    try:
        zoom = min(MAX_ZOOM_PERCENT, max(MIN_ZOOM_PERCENT, int(float(zoom))))
    except (TypeError, ValueError):
        zoom = DEFAULT_PREFERENCES["zoom_percent"]

    return {
        "auto_resize": bool(data.get("auto_resize", DEFAULT_PREFERENCES["auto_resize"])),
        "zoom_percent": zoom,
        "mouse_trace": bool(data.get("mouse_trace", DEFAULT_PREFERENCES["mouse_trace"])),
    }


def save_preferences(values: dict[str, object], path: Path | None = None) -> None:
    target = preferences_path() if path is None else path
    current = _load_raw(target)
    current.update(load_preferences(target))
    current.update(values)
    _save_raw(current, target)


def load_window_geometry(path: Path | None = None) -> str:
    target = preferences_path() if path is None else path
    value = str(_load_raw(target).get("window_geometry", DEFAULT_WINDOW_GEOMETRY)).strip()
    return value or DEFAULT_WINDOW_GEOMETRY


def save_window_geometry(geometry: str, path: Path | None = None) -> None:
    target = preferences_path() if path is None else path
    current = _load_raw(target)
    current["window_geometry"] = str(geometry).strip() or DEFAULT_WINDOW_GEOMETRY
    _save_raw(current, target)
