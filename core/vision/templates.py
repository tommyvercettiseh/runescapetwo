from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import numpy as np

from .models import TemplateSettings
from .template_matching import available_methods

ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = ROOT / "assets" / "images"
METADATA_FILE = ROOT / "config" / "templates_meta.json"

_TEMPLATE_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}

DEFAULTS = TemplateSettings(
    method="TM_CCOEFF_NORMED",
    min_shape=85.0,
    min_color=60.0,
    area=None,
)


def normalize_name(image_name: str) -> str:
    name = str(image_name).strip()
    if not name:
        raise ValueError("Image name cannot be empty")
    return name if name.lower().endswith(".png") else f"{name}.png"


def template_path(image_name: str) -> Path:
    path = IMAGES_DIR / normalize_name(image_name)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path


def load_template(image_name: str) -> tuple[np.ndarray, np.ndarray]:
    path = template_path(image_name)
    key = str(path.resolve())
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Template is not readable: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _TEMPLATE_CACHE[key] = (rgb, gray)
    return rgb, gray


def clear_template_cache() -> None:
    _TEMPLATE_CACHE.clear()


def load_metadata() -> dict:
    if not METADATA_FILE.exists():
        return {"_defaults": DEFAULTS.__dict__}
    data = json.loads(METADATA_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("templates_meta.json must contain an object")
    return data


def load_settings(image_name: str) -> TemplateSettings:
    name = normalize_name(image_name)
    metadata = load_metadata()
    defaults = metadata.get("_defaults", {})
    item = metadata.get(name, {})

    settings = TemplateSettings(
        method=str(item.get("method", defaults.get("method", DEFAULTS.method))),
        min_shape=float(item.get("min_shape", defaults.get("min_shape", DEFAULTS.min_shape))),
        min_color=float(item.get("min_color", defaults.get("min_color", DEFAULTS.min_color))),
        area=item.get("area", defaults.get("area")),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: TemplateSettings) -> None:
    if settings.method != "ALL" and settings.method not in available_methods():
        raise ValueError(f"Unknown template method: {settings.method}")
    if not 0.0 <= settings.min_shape <= 100.0:
        raise ValueError("min_shape must be between 0 and 100")
    if not 0.0 <= settings.min_color <= 100.0:
        raise ValueError("min_color must be between 0 and 100")


def save_settings(image_name: str, settings: TemplateSettings) -> None:
    validate_settings(settings)
    name = normalize_name(image_name)
    data = load_metadata()
    data[name] = {
        "method": settings.method,
        "min_shape": settings.min_shape,
        "min_color": settings.min_color,
        **({"area": settings.area} if settings.area else {}),
    }

    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = METADATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, METADATA_FILE)
