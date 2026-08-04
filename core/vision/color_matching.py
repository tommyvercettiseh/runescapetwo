from __future__ import annotations

import cv2
import numpy as np

_TEMPLATE_LAB_CACHE: dict[int, np.ndarray] = {}


def clear_color_cache() -> None:
    _TEMPLATE_LAB_CACHE.clear()


def _template_lab(template_rgb: np.ndarray) -> np.ndarray:
    key = id(template_rgb)
    cached = _TEMPLATE_LAB_CACHE.get(key)
    if cached is None:
        cached = cv2.cvtColor(template_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        _TEMPLATE_LAB_CACHE[key] = cached
    return cached


def calculate_color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    """Return a 0..100 LAB colour similarity score."""
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        return 0.0

    patch_lab = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    difference = np.abs(_template_lab(template_rgb) - patch_lab)
    weighted = (
        difference[..., 0] * 0.35
        + difference[..., 1] * 0.325
        + difference[..., 2] * 0.325
    )
    return round(float(np.clip(100.0 - np.mean(weighted), 0.0, 100.0)), 2)
