from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFSETS_FILE = ROOT / "config" / "bot_offsets.json"

# Fallback for the current 2x2 layout. Config values take precedence.
DEFAULT_OFFSETS: dict[int, tuple[int, int]] = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}


def _load_offsets() -> dict[int, tuple[int, int]]:
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
    """Return the active bot id from BOT_ID, or the supplied default."""
    try:
        return int(os.getenv("BOT_ID", str(default)))
    except ValueError:
        return int(default)


def get_bot_offset(bot_id: int | None = None) -> tuple[int, int]:
    """Resolve one bot id to an absolute screen offset.

    Explicit BOT_OFFSET_X/BOT_OFFSET_Y values are useful for launchers and
    temporarily override both the config file and the built-in defaults.
    """
    override_x = os.getenv("BOT_OFFSET_X")
    override_y = os.getenv("BOT_OFFSET_Y")
    if override_x is not None and override_y is not None:
        try:
            return int(override_x), int(override_y)
        except ValueError:
            pass

    resolved_bot_id = get_bot_id() if bot_id is None else int(bot_id)
    offsets = _load_offsets()
    try:
        return offsets[resolved_bot_id]
    except KeyError as exc:
        raise ValueError(f"Unknown bot_id: {resolved_bot_id}") from exc


def resolve_offset(
    *,
    bot_id: int | None = None,
    offset: tuple[int, int] | None = None,
) -> tuple[int, int]:
    """Resolve a manual offset or derive one from bot_id.

    A manual offset is kept for backwards compatibility. New code should use
    bot_id because it keeps find, wait, exists and click calls consistent.
    """
    if offset is not None:
        return int(offset[0]), int(offset[1])
    return get_bot_offset(bot_id)


def apply_offset(
    area: tuple[int, int, int, int] | None,
    offset: tuple[int, int] = (0, 0),
) -> tuple[int, int, int, int] | None:
    """Translate a local (x, y, width, height) area to screen coordinates."""
    if area is None:
        return None
    x, y, width, height = area
    ox, oy = offset
    return x + int(ox), y + int(oy), width, height
