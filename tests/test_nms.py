from __future__ import annotations

import numpy as np
import pytest

from core.vision.nms import find_candidates


def test_nms_keeps_best_of_overlapping_hits() -> None:
    score_map = np.zeros((25, 25), dtype=np.float32)
    score_map[2, 2] = 0.95
    score_map[3, 3] = 0.90
    score_map[18, 18] = 0.85

    candidates = find_candidates(score_map, 0.8, 10, 10)

    assert [candidate[:2] for candidate in candidates] == [(2, 2), (18, 18)]
    assert [candidate[2] for candidate in candidates] == pytest.approx([0.95, 0.85])


def test_nms_respects_maximum_hits() -> None:
    score_map = np.array([[0.8, 0.9, 1.0]], dtype=np.float32)

    candidates = find_candidates(score_map, 0.5, 1, 1, maximum_hits=2)

    assert len(candidates) == 2
    assert candidates[0][:2] == (2, 0)


def test_nms_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="maximum_hits"):
        find_candidates(np.ones((1, 1)), 0.5, 1, 1, maximum_hits=0)
