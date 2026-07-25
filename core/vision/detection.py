from __future__ import annotations

import cv2
import numpy as np

from .color_matching import calculate_color_score
from .models import Hit, TemplateSettings
from .nms import find_candidates
from .template_matching import best_location, compare_methods, match_template


def _build_hit(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    x: int,
    y: int,
    shape_score: float,
    method: str,
    offset_x: int,
    offset_y: int,
    settings: TemplateSettings,
) -> Hit | None:
    height, width = template_rgb.shape[:2]
    patch = screenshot_rgb[y : y + height, x : x + width]
    if patch.shape[:2] != (height, width):
        return None

    color_score = calculate_color_score(template_rgb, patch)
    if shape_score < settings.min_shape or color_score < settings.min_color:
        return None

    return Hit(
        x=offset_x + x,
        y=offset_y + y,
        width=width,
        height=height,
        shape_score=round(shape_score, 2),
        color_score=round(color_score, 2),
        method=method,
    )


def find_best_match(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    settings: TemplateSettings,
    offset: tuple[int, int] = (0, 0),
) -> Hit | None:
    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    method = settings.method

    if method == "ALL":
        results = compare_methods(screenshot_gray, template_gray)
        method, (x, y, shape_score) = max(results.items(), key=lambda item: item[1][2])
    else:
        x, y, shape_score = best_location(match_template(screenshot_gray, template_gray, method))

    return _build_hit(
        screenshot_rgb,
        template_rgb,
        x,
        y,
        shape_score,
        method,
        offset[0],
        offset[1],
        settings,
    )


def find_all_matches(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    settings: TemplateSettings,
    offset: tuple[int, int] = (0, 0),
    maximum_hits: int = 50,
) -> list[Hit]:
    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    method = settings.method
    if method == "ALL":
        method = max(
            compare_methods(screenshot_gray, template_gray).items(),
            key=lambda item: item[1][2],
        )[0]

    score_map = match_template(screenshot_gray, template_gray, method)
    height, width = template_gray.shape[:2]
    candidates = find_candidates(
        score_map,
        settings.min_shape / 100.0,
        width,
        height,
        maximum_hits,
    )

    hits: list[Hit] = []
    for x, y, score in candidates:
        hit = _build_hit(
            screenshot_rgb,
            template_rgb,
            x,
            y,
            score * 100.0,
            method,
            offset[0],
            offset[1],
            settings,
        )
        if hit is not None:
            hits.append(hit)
    return hits
