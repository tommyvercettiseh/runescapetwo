from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import numpy as np

from .color_matching import clear_color_cache
from .models import TemplateSettings
from .template_matching import available_methods

ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = ROOT / "assets" / "images"
METADATA_FILE = ROOT / "config" / "templates_meta.json"

_TEMPLATE_CACHE: dict[str, tuple[int, tuple[np.ndarray, np.ndarray]]] = {}
_METADATA_CACHE: dict | None = None
_METADATA_STAMP: int | None = None
_SETTINGS_CACHE: dict[str, TemplateSettings] = {}

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
    """Load RGB and grayscale once, then reuse them until the file changes."""
    path = template_path(image_name)
    key = str(path.resolve())
    stamp = path.stat().st_mtime_ns
    cached = _TEMPLATE_CACHE.get(key)
    if cached is not None and cached[0] == stamp:
        return cached[1]

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Template is not readable: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    loaded = (rgb, gray)
    _TEMPLATE_CACHE[key] = (stamp, loaded)
    return loaded


def clear_template_cache() -> None:
    _TEMPLATE_CACHE.clear()
    clear_color_cache()


def clear_metadata_cache() -> None:
    global _METADATA_CACHE, _METADATA_STAMP
    _METADATA_CACHE = None
    _METADATA_STAMP = None
    _SETTINGS_CACHE.clear()


def load_metadata() -> dict:
    global _METADATA_CACHE, _METADATA_STAMP

    stamp = METADATA_FILE.stat().st_mtime_ns if METADATA_FILE.exists() else -1
    if _METADATA_CACHE is not None and _METADATA_STAMP == stamp:
        return _METADATA_CACHE

    if not METADATA_FILE.exists():
        data = {"_defaults": DEFAULTS.__dict__}
    else:
        data = json.loads(METADATA_FILE.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("templates_meta.json must contain an object")

    _METADATA_CACHE = data
    _METADATA_STAMP = stamp
    _SETTINGS_CACHE.clear()
    return data


def load_settings(image_name: str) -> TemplateSettings:
    name = normalize_name(image_name)
    metadata = load_metadata()
    cached = _SETTINGS_CACHE.get(name)
    if cached is not None:
        return cached

    defaults = metadata.get("_defaults", {})
    item = metadata.get(name, {})
    settings = TemplateSettings(
        method=str(item.get("method", defaults.get("method", DEFAULTS.method))),
        min_shape=float(item.get("min_shape", defaults.get("min_shape", DEFAULTS.min_shape))),
        min_color=float(item.get("min_color", defaults.get("min_color", DEFAULTS.min_color))),
        area=item.get("area", defaults.get("area")),
    )
    validate_settings(settings)
    _SETTINGS_CACHE[name] = settings
    return settings


def validate_settings(settings: TemplateSettings) -> None:
    if settings.method not in available_methods():
        raise ValueError(
            "A template must use one fixed OpenCV method; compare methods in the image tester"
        )
    if not 0.0 <= settings.min_shape <= 100.0:
        raise ValueError("min_shape must be between 0 and 100")
    if not 0.0 <= settings.min_color <= 100.0:
        raise ValueError("min_color must be between 0 and 100")


def save_settings(image_name: str, settings: TemplateSettings) -> None:
    validate_settings(settings)
    name = normalize_name(image_name)
    data = dict(load_metadata())
    data[name] = {
        "method": settings.method,
        "min_shape": float(settings.min_shape),
        "min_color": float(settings.min_color),
        **({"area": settings.area} if settings.area else {}),
    }

    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = METADATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, METADATA_FILE)
    clear_metadata_cache()


def rename_template(image_name: str, new_name: str) -> str:
    old = normalize_name(image_name)
    new = normalize_name(new_name)
    source = template_path(old)
    target = IMAGES_DIR / new
    if target.exists():
        raise FileExistsError(f"Template already exists: {new}")

    source.rename(target)
    data = dict(load_metadata())
    if old in data:
        data[new] = data.pop(old)
        temporary = METADATA_FILE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, METADATA_FILE)
    clear_template_cache()
    clear_metadata_cache()
    return new


def delete_template(image_name: str) -> bool:
    name = normalize_name(image_name)
    path = IMAGES_DIR / name
    removed = False
    if path.exists():
        path.unlink()
        removed = True

    data = dict(load_metadata())
    if name in data:
        data.pop(name)
        temporary = METADATA_FILE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, METADATA_FILE)
        removed = True
    clear_template_cache()
    clear_metadata_cache()
    return removed
