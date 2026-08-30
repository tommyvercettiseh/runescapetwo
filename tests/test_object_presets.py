from __future__ import annotations

import json

import pytest

from core.vision import object_presets


def test_save_and_load_object_preset(tmp_path, monkeypatch):
    path = tmp_path / "object_presets.json"
    monkeypatch.setattr(object_presets, "CONFIG_PATH", path)

    saved = object_presets.save_object_preset(
        "Furnace",
        colour="purple",
        min_pixels=250,
        max_pixels=4000,
        area="Bot_Area",
    )

    loaded = object_presets.load_object_preset("furnace")

    assert saved == loaded
    assert loaded.name == "furnace"
    assert loaded.min_pixels == 250
    assert loaded.max_pixels == 4000


def test_missing_object_preset_raises_key_error(tmp_path, monkeypatch):
    monkeypatch.setattr(object_presets, "CONFIG_PATH", tmp_path / "object_presets.json")

    with pytest.raises(KeyError, match="Unknown object preset"):
        object_presets.load_object_preset("missing")


def test_invalid_pixel_range_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(object_presets, "CONFIG_PATH", tmp_path / "object_presets.json")

    with pytest.raises(ValueError, match="max_pixels cannot be smaller"):
        object_presets.save_object_preset(
            "bank",
            colour="cyan",
            min_pixels=800,
            max_pixels=300,
        )


def test_broken_object_preset_file_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "object_presets.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    monkeypatch.setattr(object_presets, "CONFIG_PATH", path)

    with pytest.raises(ValueError, match="must contain an object"):
        object_presets.list_object_presets()
