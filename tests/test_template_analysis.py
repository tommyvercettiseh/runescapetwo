from __future__ import annotations

import numpy as np
import pytest

from core.vision import template_analysis


def test_template_analysis_returns_shape_and_colour_candidates(monkeypatch) -> None:
    screenshot = np.zeros((20, 20, 3), dtype=np.uint8)
    template_rgb = np.zeros((3, 3, 3), dtype=np.uint8)
    template_gray = np.zeros((3, 3), dtype=np.uint8)
    score_map = np.zeros((18, 18), dtype=np.float32)
    score_map[2, 4] = 0.95
    score_map[12, 10] = 0.90
    colours = iter((81.0, 81.0, 72.0))

    monkeypatch.setattr(template_analysis, "match_template", lambda *_args: score_map)
    monkeypatch.setattr(
        template_analysis,
        "calculate_color_score",
        lambda *_args: next(colours),
    )

    result = template_analysis.analyse_template(
        screenshot,
        template_rgb,
        template_gray,
        method="TM_CCOEFF_NORMED",
        minimum_shape=85.0,
        maximum_candidates=5,
    )

    assert result.best_shape_score == 95.0
    assert result.best_color_score == 81.0
    assert (result.best_x, result.best_y) == (4, 2)
    assert [(item.x, item.y) for item in result.candidates] == [(4, 2), (10, 12)]
    assert result.candidates[0].passes_colour(80.0) is True
    assert result.candidates[1].passes_colour(80.0) is False


def test_template_analysis_rejects_template_larger_than_area() -> None:
    screenshot = np.zeros((4, 4, 3), dtype=np.uint8)
    template_rgb = np.zeros((5, 5, 3), dtype=np.uint8)
    template_gray = np.zeros((5, 5), dtype=np.uint8)

    with pytest.raises(ValueError, match="larger"):
        template_analysis.analyse_template(
            screenshot,
            template_rgb,
            template_gray,
            method="TM_CCOEFF_NORMED",
            minimum_shape=80.0,
            maximum_candidates=5,
        )
