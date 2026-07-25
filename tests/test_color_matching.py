from __future__ import annotations

import numpy as np

from core.vision.color_matching import calculate_color_score


def test_identical_colors_score_one_hundred() -> None:
    image = np.full((4, 4, 3), (20, 100, 220), dtype=np.uint8)

    assert calculate_color_score(image, image.copy()) == 100.0


def test_clearly_different_colors_score_lower() -> None:
    black = np.zeros((4, 4, 3), dtype=np.uint8)
    white = np.full((4, 4, 3), 255, dtype=np.uint8)

    assert calculate_color_score(black, white) < 70.0
