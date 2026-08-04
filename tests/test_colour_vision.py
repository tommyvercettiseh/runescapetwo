from __future__ import annotations

import cv2
import numpy as np

from core.vision import colour_detection
from core.vision import colour_presets


def _rgb_from_hsv(h: int, s: int, v: int) -> np.ndarray:
    hsv = np.array([[[h, s, v]]], dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)[0, 0]


def test_hsv_ranges_wrap_around_red() -> None:
    ranges = colour_detection.hsv_ranges_around(
        (178, 240, 240),
        hue_tolerance=5,
        saturation_tolerance=10,
        value_tolerance=10,
    )

    assert ranges == (
        ((173, 230, 230), (179, 250, 250)),
        ((0, 230, 230), (3, 250, 250)),
    )


def test_colour_preset_store_round_trip(tmp_path, monkeypatch) -> None:
    presets_file = tmp_path / "colour_presets.json"
    monkeypatch.setattr(colour_presets, "PRESETS_FILE", presets_file)
    colour_presets.clear_colour_preset_cache()

    assert colour_presets.list_colour_presets() == ()

    ranges = (
        ((135, 150, 120), (150, 255, 255)),
        ((0, 200, 200), (4, 255, 255)),
    )
    colour_presets.save_colour_preset("Purple", ranges)

    loaded = colour_presets.load_colour_preset("purple")
    assert loaded.name == "purple"
    assert loaded.ranges == ranges
    assert colour_presets.list_colour_presets() == ("purple",)

    assert colour_presets.delete_colour_preset("PURPLE") is True
    assert colour_presets.list_colour_presets() == ()


def test_blobs_use_exact_mask_pixel_counts_and_absolute_coordinates() -> None:
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2:5, 3:7] = 255
    mask[10:12, 10:12] = 255

    blobs = colour_detection.blobs_from_mask(
        mask,
        origin=(100, 200),
        minimum_area_px=5,
    )

    assert len(blobs) == 1
    blob = blobs[0]
    assert blob.area_px == 12
    assert (blob.x, blob.y, blob.width, blob.height) == (103, 202, 4, 3)
    safe_x, safe_y = blob.safe_point
    assert mask[safe_y - 200, safe_x - 100] == 255


def test_same_red_preset_supports_presence_and_large_target_rules(monkeypatch) -> None:
    red = _rgb_from_hsv(0, 255, 255)
    hp = np.zeros((5, 5, 3), dtype=np.uint8)
    hp[0, 0] = red
    hp[0, 1] = red
    hp[1, 0] = red

    game = np.zeros((40, 40, 3), dtype=np.uint8)
    game[5:30, 8:33] = red

    preset = colour_presets.ColourPreset(
        name="red",
        ranges=(((0, 240, 240), (4, 255, 255)),),
    )
    monkeypatch.setattr(
        colour_detection,
        "load_colour_preset",
        lambda _name: preset,
    )

    def fake_capture(area, *, bot_id=None):
        if area == "HP_Area":
            return hp, (100, 200, hp.shape[1], hp.shape[0])
        return game, (500, 600, game.shape[1], game.shape[0])

    monkeypatch.setattr(colour_detection, "capture_area", fake_capture)

    assert colour_detection.colour_exists(
        "red",
        area="HP_Area",
        minimum_pixels=3,
    )
    assert not colour_detection.colour_exists(
        "red",
        area="HP_Area",
        minimum_pixels=4,
    )

    blobs = colour_detection.find_colour_blobs(
        "red",
        area="game",
        minimum_area_px=500,
    )
    assert len(blobs) == 1
    assert blobs[0].area_px == 625
    assert (blobs[0].x, blobs[0].y) == (508, 605)


def test_pipette_sample_creates_a_working_range() -> None:
    rgb = np.zeros((9, 9, 3), dtype=np.uint8)
    purple = _rgb_from_hsv(145, 230, 220)
    rgb[2:7, 2:7] = purple

    sampled = colour_detection.sample_hsv(rgb, 4, 4, radius=2)
    ranges = colour_detection.hsv_ranges_around(
        sampled,
        hue_tolerance=2,
        saturation_tolerance=5,
        value_tolerance=5,
    )
    mask = colour_detection.build_mask_from_ranges(rgb, ranges)

    assert sampled == (145, 230, 220)
    assert colour_detection.count_mask_pixels(mask) == 25
    assert colour_detection.count_mask_components(mask) == 1


def test_blob_maximum_filter() -> None:
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[1:4, 1:4] = 255
    mask[10:16, 10:16] = 255

    blobs = colour_detection.blobs_from_mask(
        mask,
        minimum_area_px=1,
        maximum_area_px=20,
    )

    assert [blob.area_px for blob in blobs] == [9]
