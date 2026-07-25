from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"

_active_profile: dict[str, Any] | None = None
_active_name = "default"


def load_profile(name: str = "default") -> dict[str, Any]:
    """Load one profile and make it active."""
    global _active_profile, _active_name

    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("mouse"), dict):
        raise ValueError("Profile requires a 'mouse' object")
    if not isinstance(data.get("keyboard"), dict):
        raise ValueError("Profile requires a 'keyboard' object")

    _active_profile = data
    _active_name = name
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
