from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BOTS_FILE = ROOT / "config" / "bots.json"

_active_bot_id: int | None = None


def _bot_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Bot ID must be a positive integer")
    if isinstance(value, int):
        bot_id = value
    elif isinstance(value, str) and value.strip().isdigit():
        bot_id = int(value.strip())
    else:
        raise ValueError("Bot ID must be a positive integer")
    if bot_id < 1:
        raise ValueError("Bot ID must be a positive integer")
    return bot_id


def _positive_dimension(settings: object, key: str, label: str) -> int:
    if not isinstance(settings, dict):
        raise ValueError(f"{label} must be an object")
    value = settings.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label}.{key} must be a positive integer")
    return value


def _rectangles_overlap(
    left: tuple[int, int, int, int],
    right: tuple[int, int, int, int],
) -> bool:
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    return (
        max(lx, rx) < min(lx + lw, rx + rw)
        and max(ly, ry) < min(ly + lh, ry + rh)
    )


def load_bots() -> dict[str, Any]:
    if not BOTS_FILE.exists():
        raise FileNotFoundError(f"Bot configuration not found: {BOTS_FILE}")

    data = json.loads(BOTS_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("bots.json must contain an object")

    screen_width = _positive_dimension(data.get("_screen"), "width", "_screen")
    screen_height = _positive_dimension(data.get("_screen"), "height", "_screen")
    window_width = _positive_dimension(data.get("_window"), "width", "_window")
    window_height = _positive_dimension(data.get("_window"), "height", "_window")
    if window_width > screen_width or window_height > screen_height:
        raise ValueError("Bot window cannot be larger than the screen")

    default_id = _bot_id(data.get("_default"))
    bot_keys = [key for key in data if not key.startswith("_")]
    if str(default_id) not in bot_keys:
        raise ValueError(f"Default bot {default_id} is not configured")

    regions: dict[int, tuple[int, int, int, int]] = {}
    for key in bot_keys:
        bot_id = _bot_id(key)
        if str(bot_id) != key:
            raise ValueError(f"Bot key must be a canonical integer: {key}")

        settings = data[key]
        if not isinstance(settings, dict):
            raise ValueError(f"Bot {bot_id} settings must be an object")

        offset = settings.get("offset")
        if not isinstance(offset, list) or len(offset) != 2:
            raise ValueError(f"Bot {bot_id}.offset must contain [x, y]")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in offset
        ):
            raise ValueError(f"Bot {bot_id}.offset values must be integers")
        x, y = offset
        if x < 0 or y < 0:
            raise ValueError(f"Bot {bot_id}.offset cannot be negative")
        if x + window_width > screen_width or y + window_height > screen_height:
            raise ValueError(f"Bot {bot_id} window falls outside the screen")
        regions[bot_id] = x, y, window_width, window_height

    region_items = list(regions.items())
    for index, (bot_id, region) in enumerate(region_items):
        for other_id, other_region in region_items[index + 1 :]:
            if _rectangles_overlap(region, other_region):
                raise ValueError(
                    f"Bot {bot_id} window overlaps bot {other_id} window"
                )

    return data


def set_bot(bot_id: int) -> None:
    global _active_bot_id
    selected = _bot_id(bot_id)
    bots = load_bots()
    if str(selected) not in bots:
        raise ValueError(f"Unknown bot ID: {selected}")
    _active_bot_id = selected


def active_bot_id() -> int:
    global _active_bot_id
    if _active_bot_id is None:
        bots = load_bots()
        selected = os.getenv("BOT_ID", bots["_default"])
        set_bot(_bot_id(selected))
    assert _active_bot_id is not None
    return _active_bot_id


def get_bot_offset(bot_id: int | None = None) -> tuple[int, int]:
    selected = active_bot_id() if bot_id is None else _bot_id(bot_id)
    bots = load_bots()
    try:
        offset = bots[str(selected)]["offset"]
    except KeyError as exc:
        raise ValueError(f"Unknown bot ID: {selected}") from exc
    return int(offset[0]), int(offset[1])


def get_screen_size() -> tuple[int, int]:
    settings = load_bots()["_screen"]
    return int(settings["width"]), int(settings["height"])


def get_bot_size() -> tuple[int, int]:
    settings = load_bots()["_window"]
    return int(settings["width"]), int(settings["height"])


def get_bot_region(bot_id: int | None = None) -> tuple[int, int, int, int]:
    x, y = get_bot_offset(bot_id)
    width, height = get_bot_size()
    return x, y, width, height


def to_screen_point(
    x: int,
    y: int,
    *,
    bot_id: int | None = None,
) -> tuple[int, int]:
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, int)
        or not isinstance(y, int)
    ):
        raise ValueError("Coordinates must be integers")

    width, height = get_bot_size()
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("Bot-relative coordinates fall outside the bot window")

    offset_x, offset_y = get_bot_offset(bot_id)
    return x + offset_x, y + offset_y


def validate_screen_point(x: int, y: int) -> tuple[int, int]:
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, int)
        or not isinstance(y, int)
    ):
        raise ValueError("Coordinates must be integers")

    width, height = get_screen_size()
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("Coordinates fall outside the configured screen")
    return x, y
