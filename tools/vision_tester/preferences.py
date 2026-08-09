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


def preferences_path() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "RuneScapeTwo" / "vision_tester.json"


def load_preferences(path: Path | None = None) -> dict[str, object]:
    target = preferences_path() if path is None else path
    data: dict[str, object] = {}
    try:
        loaded = json.loads(target.read_text(encoding="utf-8-sig"))
        if isinstance(loaded, dict):
            data = loaded
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass

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
    target.parent.mkdir(parents=True, exist_ok=True)
    current = load_preferences(target)
    current.update(values)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, target)
