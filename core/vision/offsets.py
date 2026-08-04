from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFSETS_FILE = ROOT / "config" / "bot_offsets.json"

Region = tuple[int, int, int, int]
Offset = tuple[int, int]

# Fallback for the current 2x2 layout. Config values take precedence.
DEFAULT_OFFSETS: dict[int, Offset] = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}


def _load_offsets() -> dict[int, Offset]:
    if not OFFSETS_FILE.exists():
        return DEFAULT_OFFSETS.copy()

    data = json.loads(OFFSETS_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("bot_offsets.json must contain an object")

    offsets = DEFAULT_OFFSETS.copy()
    for raw_bot_id, raw_offset in data.items():
        if not isinstance(raw_offset, list) or len(raw_offset) != 2:
            raise ValueError(f"Invalid offset for bot {raw_bot_id}: {raw_offset!r}")
        offsets[int(raw_bot_id)] = (int(raw_offset[0]), int(raw_offset[1]))
    return offsets


def get_bot_id(default: int = 1) -> int:
    """Return BOT_ID, or the supplied default when it is missing or invalid."""
    try:
        return int(os.getenv("BOT_ID", str(default)))
    except ValueError:
        return int(default)


def get_bot_offset(bot_id: int | None = None) -> Offset:
    """Return the configured desktop offset for one bot."""
    resolved_bot_id = get_bot_id() if bot_id is None else int(bot_id)
    offsets = _load_offsets()

    try:
        return offsets[resolved_bot_id]
    except KeyError as exc:
        raise ValueError(f"Unknown bot_id: {resolved_bot_id}") from exc


def apply_offset(
    region: Region,
    bot_id: int | Offset | None = None,
) -> Region:
    """Translate one local bot-1 region to absolute desktop coordinates.

    Normal code passes a bot id. A direct offset tuple remains accepted only so
    the existing visual tester can edit unsaved areas without its own math.
    """
    x, y, width, height = map(int, region)
    if isinstance(bot_id, tuple):
        offset_x, offset_y = map(int, bot_id)
    else:
        offset_x, offset_y = get_bot_offset(bot_id)
    return x + offset_x, y + offset_y, width, height
