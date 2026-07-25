from __future__ import annotations

import json
from copy import deepcopy
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"

_active_profile: dict[str, Any] | None = None
_active_name = "default"

_MOUSE_RANGES = (
    ("duration_min_s", "duration_max_s"),
    ("steps_min", "steps_max"),
    ("pre_click_min_s", "pre_click_max_s"),
    ("click_hold_min_s", "click_hold_max_s"),
    ("post_click_min_s", "post_click_max_s"),
    ("scroll_delay_min_s", "scroll_delay_max_s"),
)

_KEYBOARD_RANGES = (
    ("press_hold_min_s", "press_hold_max_s"),
    ("type_delay_min_s", "type_delay_max_s"),
    ("pause_min_s", "pause_max_s"),
)


def _number(settings: dict[str, Any], key: str, section: str) -> float:
    value = settings.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{section}.{key} must be a number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{section}.{key} must be finite")
    if value < 0:
        raise ValueError(f"{section}.{key} cannot be negative")
    return float(value)


def _validate_ranges(
    settings: dict[str, Any],
    section: str,
    ranges: tuple[tuple[str, str], ...],
) -> None:
    for minimum_key, maximum_key in ranges:
        minimum = _number(settings, minimum_key, section)
        maximum = _number(settings, maximum_key, section)
        if minimum > maximum:
            raise ValueError(
                f"{section}.{minimum_key} cannot be greater than "
                f"{section}.{maximum_key}"
            )


def validate_profile(data: Any) -> None:
    """Validate the small, public profile contract."""
    if not isinstance(data, dict):
        raise ValueError("Profile must contain an object")

    mouse = data.get("mouse")
    keyboard = data.get("keyboard")
    vision = data.get("vision")
    if not isinstance(mouse, dict):
        raise ValueError("Profile requires a 'mouse' object")
    if not isinstance(keyboard, dict):
        raise ValueError("Profile requires a 'keyboard' object")
    if not isinstance(vision, dict):
        raise ValueError("Profile requires a 'vision' object")

    _validate_ranges(mouse, "mouse", _MOUSE_RANGES)
    _validate_ranges(keyboard, "keyboard", _KEYBOARD_RANGES)

    for key in ("steps_min", "steps_max"):
        value = mouse[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"mouse.{key} must be a positive integer")

    movement_method = mouse.get("movement_method")
    if not isinstance(movement_method, str) or not movement_method.strip():
        raise ValueError("mouse.movement_method must be a non-empty string")

    from .movements import available_movements

    if movement_method.strip().lower() not in available_movements():
        available = ", ".join(available_movements())
        raise ValueError(
            f"Unknown movement method '{movement_method}'. Available: {available}"
        )

    movement_settings = mouse.get("movement_settings")
    if not isinstance(movement_settings, dict):
        raise ValueError("mouse.movement_settings must be an object")

    pause_chance = _number(keyboard, "pause_chance", "keyboard")
    if pause_chance > 1:
        raise ValueError("keyboard.pause_chance must be between 0 and 1")

    _number(vision, "poll_interval_s", "vision")
    _number(vision, "timeout_s", "vision")

    click_padding = vision.get("click_padding_px")
    if (
        isinstance(click_padding, bool)
        or not isinstance(click_padding, int)
        or click_padding < 0
    ):
        raise ValueError("vision.click_padding_px must be a non-negative integer")


def load_profile(name: str = "default") -> dict[str, Any]:
    """Load one profile and make it active."""
    global _active_profile, _active_name

    clean_name = str(name).strip()
    if not clean_name or Path(clean_name).name != clean_name:
        raise ValueError("Profile name must be a plain file name")

    path = PROFILES_DIR / f"{clean_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    validate_profile(data)

    _active_profile = data
    _active_name = clean_name
    return deepcopy(data)


def get_profile() -> dict[str, Any]:
    """Return a copy of the active profile."""
    if _active_profile is None:
        load_profile(_active_name)
    return deepcopy(_active_profile)


def get_section(section: str) -> dict[str, Any]:
    profile = get_profile()
    value = profile.get(section)
    if not isinstance(value, dict):
        raise KeyError(f"Unknown profile section: {section}")
    return value


def active_profile_name() -> str:
    return _active_name
