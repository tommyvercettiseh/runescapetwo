from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import core.vision.api as api
import core.vision.colours as colours
from core.vision.colour_detection import create_mask, find_blobs
from core.vision.colours import ColourSettings


CYAN = ColourSettings(
    ranges=(((82, 50, 50), (98, 255, 255)),),
    min_blob_px=50,
    padding_px=2,
)


def test_find_blobs_filters_noise_and_returns_absolute_safe_pixels() -> None:
    image = np.zeros((50, 60, 3), dtype=np.uint8)
    image[10:30, 15:35] = (0, 255, 255)
    image[2:5, 2:5] = (0, 255, 255)

    blobs = find_blobs(image, CYAN, origin=(960, 0))

    assert len(blobs) == 1
    blob = blobs[0]
    assert (blob.x, blob.y, blob.width, blob.height) == (975, 10, 20, 20)
    assert blob.pixel_count == 400
    assert blob.clickable_pixel_count == 256
    assert blob.clickable_points[:, 0].min() == 977
    assert blob.clickable_points[:, 0].max() == 992
    assert blob.clickable_points[:, 1].min() == 12
    assert blob.clickable_points[:, 1].max() == 27


def test_red_ranges_cover_both_ends_of_opencv_hue() -> None:
    hsv = np.array([[[0, 255, 255], [179, 255, 255]]], dtype=np.uint8)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    settings = ColourSettings(
        ranges=(
            ((0, 80, 80), (10, 255, 255)),
            ((170, 80, 80), (179, 255, 255)),
        ),
        min_blob_px=1,
        padding_px=0,
    )

    mask = create_mask(rgb, settings)

    assert mask.tolist() == [[255, 255]]


@pytest.mark.parametrize(
    ("min_blob_px", "padding_px", "message"),
    ((0, None, "min_blob_px"), (None, -1, "padding_px")),
)
def test_invalid_blob_settings_are_rejected(
    min_blob_px: int | None,
    padding_px: int | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        find_blobs(
            np.zeros((5, 5, 3), dtype=np.uint8),
            CYAN,
            min_blob_px=min_blob_px,
            padding_px=padding_px,
        )


def test_find_colour_blobs_uses_bot_aware_absolute_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[int, int, int, int]] = []
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[2:12, 3:13] = (0, 255, 255)
    monkeypatch.setattr(api, "get_area", lambda *_args, **_kwargs: (960, 0, 20, 20))
    monkeypatch.setattr(
        api,
        "capture_rgb",
        lambda region: captured.append(region) or image,
    )
    monkeypatch.setattr(api, "load_colour", lambda _name: CYAN)

    blobs = api.find_colour_blobs(
        "cyaan",
        area="screen",
        bot_id=2,
        padding_px=0,
    )

    assert captured == [(960, 0, 20, 20)]
    assert (blobs[0].x, blobs[0].y) == (963, 2)
    assert blobs[0].clickable_points[0].tolist() == [963, 2]


def test_colour_config_is_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "colours.json"
    path.write_text(
        json.dumps(
            {
                "_defaults": {"min_blob_px": 10, "padding_px": 2},
                "cyaan": {"ranges": [[[82, 50, 50], [98, 255, 255]]]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(colours, "COLOURS_FILE", path)

    settings = colours.load_colour(" CYAAN ")

    assert settings == ColourSettings(
        ranges=(((82, 50, 50), (98, 255, 255)),),
        min_blob_px=10,
        padding_px=2,
    )


def test_unknown_colour_has_clear_error() -> None:
    with pytest.raises(KeyError, match="Unknown colour"):
        colours.load_colour("bestaat-niet")
