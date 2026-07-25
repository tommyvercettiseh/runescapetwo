from __future__ import annotations

import cv2
import numpy as np


def calculate_color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, template_rgb.shape[:2][::-1])

    template_lab = cv2.cvtColor(template_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    patch_lab = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)

    difference = np.abs(template_lab - patch_lab)
    weighted = (
        difference[..., 0] * 0.35
        + difference[..., 1] * 0.325
        + difference[..., 2] * 0.325
    )
    return round(float(np.clip(100.0 - np.mean(weighted), 0.0, 100.0)), 2)
