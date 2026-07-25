from __future__ import annotations

import json
from pathlib import Path

import pytest

import core.vision.areas as areas
import core.vision.templates as templates
from core import vision
from core.vision.models import TemplateSettings


def test_normalize_name_resolves_one_exact_png() -> None:
    assert templates.normalize_name("bank") == "bank.png"
    assert templates.normalize_name("bank.png") == "bank.png"
    assert templates.normalize_name("bank.PNG") == "bank.png"


def test_get_area_is_part_of_public_vision_api() -> None:
    assert callable(vision.get_area)


@pytest.mark.parametrize("name", ("bank.jpg", "../bank", "folder/bank", r"folder\bank"))
def test_invalid_template_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        templates.normalize_name(name)


@pytest.mark.parametrize("threshold", (-0.01, 100.01))
def test_shape_threshold_must_be_a_percentage(threshold: float) -> None:
    with pytest.raises(ValueError, match="min_shape"):
        templates.validate_settings(
            TemplateSettings("TM_CCOEFF_NORMED", threshold, 60)
        )


def test_all_is_rejected_for_runtime_settings() -> None:
    with pytest.raises(ValueError, match="image tester"):
        templates.validate_settings(TemplateSettings("ALL", 85, 60))


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown template method"):
        templates.validate_settings(TemplateSettings("UNKNOWN", 85, 60))


def test_unknown_metadata_area_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    areas_file = tmp_path / "areas.json"
    areas_file.write_text('{"game": {"x": 0, "y": 0, "width": 10, "height": 10}}')
    monkeypatch.setattr(areas, "AREAS_FILE", areas_file)

    with pytest.raises(ValueError, match="Unknown template area"):
        templates.validate_settings(
            TemplateSettings("TM_CCOEFF_NORMED", 85, 60, "inventory")
        )


def test_metadata_requires_exact_png_keys() -> None:
    with pytest.raises(ValueError, match="exact PNG"):
        templates.validate_metadata(
            {
                "_defaults": {
                    "method": "TM_CCOEFF_NORMED",
                    "min_shape": 85,
                    "min_color": 60,
                },
                "bank": {"method": "TM_CCOEFF_NORMED"},
            }
        )


def test_settings_are_saved_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata_file = tmp_path / "templates_meta.json"
    metadata_file.write_text(
        json.dumps(
            {
                "_defaults": {
                    "method": "TM_CCOEFF_NORMED",
                    "min_shape": 85,
                    "min_color": 60,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(templates, "METADATA_FILE", metadata_file)

    templates.save_settings(
        "bank",
        TemplateSettings("TM_CCORR_NORMED", 90, 70),
    )

    saved = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert saved["bank.png"]["method"] == "TM_CCORR_NORMED"
    assert list(tmp_path.glob("*.tmp")) == []
