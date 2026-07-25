from __future__ import annotations

import cv2
import numpy as np
import pytest

from core.vision.template_matching import (
    _score_map,
    available_methods,
    best_location,
    match_template,
)


@pytest.fixture
def exact_match() -> tuple[np.ndarray, np.ndarray]:
    template = np.array(
        [
            [10, 80, 20],
            [220, 30, 140],
            [50, 190, 100],
        ],
        dtype=np.uint8,
    )
    screenshot = np.zeros((10, 12), dtype=np.uint8)
    screenshot[4:7, 3:6] = template
    return screenshot, template


@pytest.mark.parametrize("method", available_methods())
def test_every_method_finds_an_exact_match(
    exact_match: tuple[np.ndarray, np.ndarray],
    method: str,
) -> None:
    screenshot, template = exact_match

    x, y, score = best_location(match_template(screenshot, template, method))

    assert (x, y) == (3, 4)
    assert score == pytest.approx(100.0, abs=0.01)


def test_normalized_ccoeff_keeps_zero_as_zero() -> None:
    raw_result = np.array([[0.0]], dtype=np.float32)

    score = _score_map(raw_result, "TM_CCOEFF_NORMED")

    assert score[0, 0] == pytest.approx(0.0)


def test_sqdiff_normalized_score_is_reversed() -> None:
    raw_result = np.array([[0.0, 1.0]], dtype=np.float32)

    score = _score_map(raw_result, "TM_SQDIFF_NORMED")

    assert score[0, 0] == pytest.approx(1.0)
    assert score[0, 1] == pytest.approx(0.0)


def test_raw_method_does_not_use_relative_min_max_normalization() -> None:
    screenshot = np.zeros((5, 5), dtype=np.uint8)
    template = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    raw = cv2.matchTemplate(screenshot, template, cv2.TM_CCORR)

    score = _score_map(raw, "TM_CCORR", screenshot, template)

    assert np.all(score == 0.0)


def test_unknown_method_fails_immediately(exact_match: tuple[np.ndarray, np.ndarray]) -> None:
    screenshot, template = exact_match

    with pytest.raises(ValueError, match="Unknown template method"):
        match_template(screenshot, template, "UNKNOWN")
