from __future__ import annotations

import numpy as np

from core.vision import image_detection, template_analysis
from core.vision.models import TemplateSettings


def _images():
    screenshot = np.zeros((30, 30, 3), dtype=np.uint8)
    template_rgb = np.zeros((3, 3, 3), dtype=np.uint8)
    template_gray = np.zeros((3, 3), dtype=np.uint8)
    return screenshot, template_rgb, template_gray


def test_best_match_tries_next_shape_candidate_when_colour_rejects_first(monkeypatch):
    screenshot, template_rgb, template_gray = _images()
    score_map = np.zeros((28, 28), dtype=np.float32)
    score_map[2, 2] = 0.99
    score_map[18, 18] = 0.95
    colour_scores = iter((10.0, 10.0, 92.0))

    monkeypatch.setattr(template_analysis, "match_template", lambda *_args: score_map)
    monkeypatch.setattr(
        template_analysis,
        "calculate_color_score",
        lambda *_args: next(colour_scores),
    )

    hit = image_detection.find_best_match(
        screenshot,
        template_rgb,
        template_gray,
        TemplateSettings("TM_CCOEFF_NORMED", 90.0, 80.0),
        offset=(100, 200),
    )

    assert hit is not None
    assert (hit.x, hit.y) == (118, 218)
    assert hit.shape_score == 95.0
    assert hit.color_score == 92.0


def test_best_match_returns_none_when_template_is_larger_than_area():
    screenshot = np.zeros((5, 5, 3), dtype=np.uint8)
    template_rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    template_gray = np.zeros((10, 10), dtype=np.uint8)

    hit = image_detection.find_best_match(
        screenshot,
        template_rgb,
        template_gray,
        TemplateSettings("TM_CCOEFF_NORMED", 80.0, 60.0),
    )

    assert hit is None


def test_find_all_matches_respects_maximum_hits(monkeypatch):
    screenshot, template_rgb, template_gray = _images()
    score_map = np.zeros((28, 28), dtype=np.float32)
    score_map[2, 2] = 0.99
    score_map[12, 12] = 0.98
    score_map[22, 22] = 0.97

    monkeypatch.setattr(template_analysis, "match_template", lambda *_args: score_map)
    monkeypatch.setattr(template_analysis, "calculate_color_score", lambda *_args: 95.0)

    hits = image_detection.find_all_matches(
        screenshot,
        template_rgb,
        template_gray,
        TemplateSettings("TM_CCOEFF_NORMED", 90.0, 80.0),
        maximum_hits=2,
    )

    assert len(hits) == 2
    assert [(hit.x, hit.y) for hit in hits] == [(2, 2), (12, 12)]
