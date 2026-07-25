from __future__ import annotations

import numpy as np
import pytest

from core.vision.models import TemplateSettings
from core.vision.nms import find_candidates
from core.vision.template_matching import _score_map
from core.vision.templates import normalize_name, validate_settings


def test_normalize_name_adds_png() -> None:
    assert normalize_name("bank") == "bank.png"
    assert normalize_name("bank.png") == "bank.png"


def test_template_threshold_validation() -> None:
    validate_settings(TemplateSettings("TM_CCOEFF_NORMED", 85, 60))

    with pytest.raises(ValueError):
        validate_settings(TemplateSettings("UNKNOWN", 85, 60))

    with pytest.raises(ValueError):
        validate_settings(TemplateSettings("TM_CCOEFF_NORMED", 101, 60))


def test_sqdiff_score_is_reversed() -> None:
    result = np.array([[0.0, 1.0]], dtype=np.float32)
    score = _score_map(result, "TM_SQDIFF_NORMED")
    assert score[0, 0] == pytest.approx(1.0)
    assert score[0, 1] == pytest.approx(0.0)


def test_nms_removes_nearby_candidates() -> None:
    score_map = np.zeros((20, 20), dtype=np.float32)
    score_map[2, 2] = 0.95
    score_map[3, 3] = 0.90
    score_map[15, 15] = 0.85

    candidates = find_candidates(score_map, 0.8, 10, 10)
    assert len(candidates) == 2
