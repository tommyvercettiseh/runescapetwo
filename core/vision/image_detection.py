from __future__ import annotations

import cv2
import numpy as np

from .color_matching import calculate_color_score
from .models import Hit, TemplateSettings
from .template_matching import iter_candidates, match_template

_BEST_MATCH_CANDIDATES = 12


def _build_hit(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    x: int,
    y: int,
    shape_score: float,
    method: str,
    origin: tuple[int, int],
    settings: TemplateSettings,
) -> Hit | None:
    height, width = template_rgb.shape[:2]
    patch = screenshot_rgb[y : y + height, x : x + width]
    if patch.shape[:2] != (height, width):
        return None

    color_score = calculate_color_score(template_rgb, patch)
    if color_score < settings.min_color:
        return None

    return Hit(
        x=origin[0] + x,
        y=origin[1] + y,
        width=width,
        height=height,
        shape_score=round(shape_score, 2),
        color_score=color_score,
        method=method,
    )


def _score_map(
    screenshot_rgb: np.ndarray,
    template_gray: np.ndarray,
    method: str,
) -> np.ndarray | None:
    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    if (
        screenshot_gray.shape[0] < template_gray.shape[0]
        or screenshot_gray.shape[1] < template_gray.shape[1]
    ):
        return None
    return match_template(screenshot_gray, template_gray, method)


def find_best_match(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    settings: TemplateSettings,
    offset: tuple[int, int] = (0, 0),
) -> Hit | None:
    """Return the strongest candidate that also passes the colour threshold."""
    score_map = _score_map(screenshot_rgb, template_gray, settings.method)
    if score_map is None:
        return None

    height, width = template_gray.shape[:2]
    for x, y, score in iter_candidates(
        score_map,
        settings.min_shape / 100.0,
        width,
        height,
        maximum_candidates=_BEST_MATCH_CANDIDATES,
    ):
        hit = _build_hit(
            screenshot_rgb,
            template_rgb,
            x,
            y,
            score * 100.0,
            settings.method,
            offset,
            settings,
        )
        if hit is not None:
            return hit
    return None


def find_all_matches(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    settings: TemplateSettings,
    offset: tuple[int, int] = (0, 0),
    maximum_hits: int = 50,
) -> list[Hit]:
    """Return non-overlapping matches, strongest first."""
    maximum_hits = max(0, int(maximum_hits))
    if maximum_hits == 0:
        return []

    score_map = _score_map(screenshot_rgb, template_gray, settings.method)
    if score_map is None:
        return []

    height, width = template_gray.shape[:2]
    hits: list[Hit] = []
    candidate_limit = max(maximum_hits * 4, maximum_hits)

    for x, y, score in iter_candidates(
        score_map,
        settings.min_shape / 100.0,
        width,
        height,
        maximum_candidates=candidate_limit,
    ):
        hit = _build_hit(
            screenshot_rgb,
            template_rgb,
            x,
            y,
            score * 100.0,
            settings.method,
            offset,
            settings,
        )
        if hit is None:
            continue

        hits.append(hit)
        if len(hits) >= maximum_hits:
            break

    return hits


__all__ = ["find_best_match", "find_all_matches"]
