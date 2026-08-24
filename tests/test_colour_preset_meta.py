from __future__ import annotations

import json

from core.vision import colour_preset_meta


def test_colour_preset_meta_round_trip_and_exact_restore(tmp_path, monkeypatch) -> None:
    meta_file = tmp_path / "colour_preset_meta.json"
    monkeypatch.setattr(colour_preset_meta, "META_FILE", meta_file)

    colour_preset_meta.save_colour_preset_meta(
        "Cyan",
        tolerance=42,
        colours=[(10, 20, 30), (40, 50, 60)],
    )
    loaded = colour_preset_meta.load_colour_preset_meta("cyan")

    assert loaded is not None
    assert loaded.tolerance == 42
    assert loaded.colours == ((10, 20, 30), (40, 50, 60))

    raw = json.loads(meta_file.read_text(encoding="utf-8"))
    raw["cyan"]["legacy_note"] = "keep me"
    meta_file.write_text(json.dumps(raw), encoding="utf-8")

    snapshot = colour_preset_meta.snapshot_colour_preset_meta("cyan")
    assert snapshot is not None
    assert snapshot["legacy_note"] == "keep me"

    assert colour_preset_meta.delete_colour_preset_meta("cyan") is True
    assert colour_preset_meta.load_colour_preset_meta("cyan") is None

    colour_preset_meta.restore_colour_preset_meta("cyan", snapshot)
    restored = json.loads(meta_file.read_text(encoding="utf-8"))["cyan"]
    assert restored == snapshot


def test_missing_colour_list_keeps_legacy_inference_signal(tmp_path, monkeypatch) -> None:
    meta_file = tmp_path / "colour_preset_meta.json"
    monkeypatch.setattr(colour_preset_meta, "META_FILE", meta_file)
    meta_file.write_text(
        json.dumps({"cyan": {"tolerance": 31}}),
        encoding="utf-8",
    )

    loaded = colour_preset_meta.load_colour_preset_meta("cyan")

    assert loaded is not None
    assert loaded.tolerance == 31
    assert loaded.colours is None
