from __future__ import annotations

import numpy as np
import pytest

import core.vision.detection as detection
from core.vision.models import TemplateSettings


def test_find_best_match_checks_color_on_later_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screenshot = np.array([[[0, 0, 0], [255, 0, 0]]], dtype=np.uint8)
    template_rgb = np.array([[[255, 0, 0]]], dtype=np.uint8)
    template_gray = np.array([[76]], dtype=np.uint8)
    settings = TemplateSettings("TM_CCOEFF_NORMED", 90, 90)
    monkeypatch.setattr(
        detection,
        "match_template",
        lambda *_args: np.array([[0.99, 0.95]], dtype=np.float32),
    )

    hit = detection.find_best_match(
        screenshot,
        template_rgb,
        template_gray,
        settings,
    )

    assert hit is not None
    assert hit.x == 1
    assert hit.shape_score == pytest.approx(95.0)
    assert hit.color_score == pytest.approx(100.0)


def test_find_best_match_returns_none_when_no_combined_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screenshot = np.zeros((1, 2, 3), dtype=np.uint8)
    template_rgb = np.full((1, 1, 3), 255, dtype=np.uint8)
    template_gray = np.array([[255]], dtype=np.uint8)
    settings = TemplateSettings("TM_CCOEFF_NORMED", 90, 90)
    monkeypatch.setattr(
        detection,
        "match_template",
        lambda *_args: np.array([[0.99, 0.95]], dtype=np.float32),
    )

    assert (
        detection.find_best_match(
            screenshot,
            template_rgb,
            template_gray,
            settings,
        )
        is None
    )
