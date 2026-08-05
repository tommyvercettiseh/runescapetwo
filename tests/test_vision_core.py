from __future__ import annotations

import numpy as np
import pytest

from core.vision.models import TemplateSettings
from core.vision.template_matching import _score_map, iter_candidates
from core.vision import templates
from core.vision.templates import normalize_name, validate_settings


def test_normalize_name_adds_png() -> None:
    assert normalize_name("bank") == "bank.png"
    assert normalize_name("bank.png") == "bank.png"


def test_template_threshold_validation() -> None:
    validate_settings(TemplateSettings("TM_CCOEFF_NORMED", 85, 60))

    with pytest.raises(ValueError):
        validate_settings(TemplateSettings("UNKNOWN", 85, 60))

    with pytest.raises(ValueError):
        validate_settings(TemplateSettings("ALL", 85, 60))

    with pytest.raises(ValueError):
        validate_settings(TemplateSettings("TM_CCOEFF_NORMED", 101, 60))


def test_sqdiff_score_is_reversed() -> None:
    result = np.array([[0.0, 1.0]], dtype=np.float32)
    score = _score_map(result, "TM_SQDIFF_NORMED")
    assert score[0, 0] == pytest.approx(1.0)
    assert score[0, 1] == pytest.approx(0.0)


def test_flat_non_normalized_result_does_not_create_perfect_ghost_hit() -> None:
    result = np.ones((5, 5), dtype=np.float32)
    score = _score_map(result, "TM_CCOEFF")
    assert np.all(score == pytest.approx(0.5))


def test_candidate_selection_removes_nearby_matches() -> None:
    score_map = np.zeros((20, 20), dtype=np.float32)
    score_map[2, 2] = 0.95
    score_map[3, 3] = 0.90
    score_map[15, 15] = 0.85

    candidates = list(
        iter_candidates(
            score_map,
            0.8,
            10,
            10,
            maximum_candidates=10,
        )
    )
    assert [(x, y) for x, y, _ in candidates] == [(2, 2), (15, 15)]


def test_rename_and_delete_template_keep_metadata_in_sync(tmp_path, monkeypatch) -> None:
    images = tmp_path / "images"
    images.mkdir()
    metadata = tmp_path / "templates_meta.json"
    metadata.write_text(
        '{"old.png": {"method": "TM_CCOEFF_NORMED", "min_shape": 80, "min_color": 70}}',
        encoding="utf-8",
    )
    (images / "old.png").write_bytes(b"png")
    monkeypatch.setattr(templates, "IMAGES_DIR", images)
    monkeypatch.setattr(templates, "METADATA_FILE", metadata)
    templates.clear_metadata_cache()

    assert templates.rename_template("old.png", "new") == "new.png"
    assert (images / "new.png").exists()
    assert "new.png" in templates.load_metadata()
    assert templates.delete_template("new.png") is True
    assert not (images / "new.png").exists()
    assert "new.png" not in templates.load_metadata()
