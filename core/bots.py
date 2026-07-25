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
    try:
        bot_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Bot ID must be a positive integer") from exc
    if bot_id < 1:
        raise ValueError("Bot ID must be a positive integer")
    return bot_id


def load_bots() -> dict[str, Any]:
    if not BOTS_FILE.exists():
        raise FileNotFoundError(f"Bot configuration not found: {BOTS_FILE}")

    data = json.loads(BOTS_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("bots.json must contain an object")

    default_id = _bot_id(data.get("_default"))
    bot_keys = [key for key in data if not key.startswith("_")]
    if str(default_id) not in bot_keys:
        raise ValueError(f"Default bot {default_id} is not configured")

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
        if any(isinstance(value, bool) or not isinstance(value, int) for value in offset):
            raise ValueError(f"Bot {bot_id}.offset values must be integers")

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
