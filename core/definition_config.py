from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_CONFIG_FILE = ROOT / "config" / "definitions.json"


def load_definitions_config() -> dict[str, Any]:
    if not DEFINITIONS_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Definitions config not found: {DEFINITIONS_CONFIG_FILE}"
        )

    data = json.loads(
        DEFINITIONS_CONFIG_FILE.read_text(encoding="utf-8-sig")
    )
    if not isinstance(data, dict):
        raise ValueError("definitions.json must contain a JSON object")
    return data


def get_definition(section: str, name: str) -> dict[str, Any]:
    data = load_definitions_config()

    try:
        definition = data[section][name]
    except KeyError as exc:
        raise KeyError(
            f"Definition config missing: {section}.{name}"
        ) from exc

    if not isinstance(definition, dict):
        raise ValueError(
            f"Definition config must be an object: {section}.{name}"
        )
    return definition
