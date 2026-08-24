from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .color_matching import calculate_color_score
from .template_matching import best_location, iter_candidates, match_template


@dataclass(frozen=True)
class TemplateCandidate:
    x: int
    y: int
    width: int
    height: int
    shape_score: float
    color_score: float

    def passes_colour(self, minimum_score: float) -> bool:
        return self.color_score >= float(minimum_score)


@dataclass(frozen=True)
class TemplateAnalysis:
    best_shape_score: float
    best_color_score: float
    best_x: int
    best_y: int
    candidates: tuple[TemplateCandidate, ...]


def template_fits(
    screenshot_rgb: np.ndarray,
    template_gray: np.ndarray,
) -> bool:
    return (
        screenshot_rgb.shape[0] >= template_gray.shape[0]
        and screenshot_rgb.shape[1] >= template_gray.shape[1]
    )


def analyse_template(
    screenshot_rgb: np.ndarray,
    template_rgb: np.ndarray,
    template_gray: np.ndarray,
    *,
    method: str,
    minimum_shape: float,
    maximum_candidates: int,
) -> TemplateAnalysis:
    """Calculate template shape and colour scores once for every consumer."""
    if not template_fits(screenshot_rgb, template_gray):
        raise ValueError("Template is larger than the screenshot area")

    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    score_map = match_template(screenshot_gray, template_gray, method)
    best_x, best_y, best_shape_score = best_location(score_map)

    height, width = template_gray.shape[:2]
    best_patch = screenshot_rgb[
        best_y : best_y + height,
        best_x : best_x + width,
    ]
    best_color_score = calculate_color_score(template_rgb, best_patch)

    candidates = tuple(
        TemplateCandidate(
            x=x,
            y=y,
            width=width,
            height=height,
            shape_score=round(score * 100.0, 2),
            color_score=calculate_color_score(
                template_rgb,
                screenshot_rgb[y : y + height, x : x + width],
            ),
        )
        for x, y, score in iter_candidates(
            score_map,
            float(minimum_shape) / 100.0,
            width,
            height,
            maximum_candidates=max(0, int(maximum_candidates)),
        )
    )

    return TemplateAnalysis(
        best_shape_score=best_shape_score,
        best_color_score=best_color_score,
        best_x=best_x,
        best_y=best_y,
        candidates=candidates,
    )


__all__ = [
    "TemplateAnalysis",
    "TemplateCandidate",
    "analyse_template",
    "template_fits",
]
