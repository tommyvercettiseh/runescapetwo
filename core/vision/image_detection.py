from __future__ import annotations

import numpy as np

from .models import Hit, TemplateSettings
from .template_analysis import analyse_template, template_fits

_BEST_MATCH_CANDIDATES = 12


def _hit_from_candidate(candidate, method: str, origin: tuple[int, int]) -> Hit:
    return Hit(
        x=origin[0] + candidate.x,
        y=origin[1] + candidate.y,
        width=candidate.width,
        height=candidate.height,
        shape_score=candidate.shape_score,
        color_score=candidate.color_score,
        method=method,
    )


def find_best_match(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    settings: TemplateSettings,
    offset: tuple[int, int] = (0, 0),
) -> Hit | None:
    """Return the strongest candidate that also passes the colour threshold."""
    if not template_fits(screenshot_rgb, template_gray):
        return None

    analysis = analyse_template(
        screenshot_rgb,
        template_rgb,
        template_gray,
        method=settings.method,
        minimum_shape=settings.min_shape,
        maximum_candidates=_BEST_MATCH_CANDIDATES,
    )
    for candidate in analysis.candidates:
        if candidate.passes_colour(settings.min_color):
            return _hit_from_candidate(candidate, settings.method, offset)
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
    if maximum_hits == 0 or not template_fits(screenshot_rgb, template_gray):
        return []

    candidate_limit = max(maximum_hits * 4, maximum_hits)
    analysis = analyse_template(
        screenshot_rgb,
        template_rgb,
        template_gray,
        method=settings.method,
        minimum_shape=settings.min_shape,
        maximum_candidates=candidate_limit,
    )

    hits: list[Hit] = []
    for candidate in analysis.candidates:
        if not candidate.passes_colour(settings.min_color):
            continue
        hits.append(_hit_from_candidate(candidate, settings.method, offset))
        if len(hits) >= maximum_hits:
            break
    return hits


__all__ = ["find_best_match", "find_all_matches"]
