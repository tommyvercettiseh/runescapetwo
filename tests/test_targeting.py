import random

import pytest

from core.targeting import (
    area_target_bounds,
    colour_blob_target_bounds,
    image_target_bounds,
    normalize_image_edge_padding,
    randomized_target_bounds,
)
from core.vision.models import ColourBlob


def test_horizontal_target_bounds_keeps_twenty_percent_clear() -> None:
    assert image_target_bounds(100, 50, 200, 90) == (120, 50, 180, 90)


def test_horizontal_target_bounds_rejects_less_than_twenty_percent() -> None:
    with pytest.raises(ValueError, match="between 20 and 45"):
        image_target_bounds(100, 50, 200, 90, image_edge_padding=5)


def test_padding_is_capped_before_target_collapses() -> None:
    assert normalize_image_edge_padding(80) == 45
    with pytest.raises(ValueError, match="between 20 and 45"):
        image_target_bounds(0, 0, 100, 20, image_edge_padding=80)


def test_invalid_target_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        image_target_bounds(10, 10, 10, 30)


def test_area_padding_uses_whole_pixels_and_cannot_collapse_area() -> None:
    assert area_target_bounds(0, 0, 100, 80, area_edge_padding=10) == (
        10,
        10,
        90,
        70,
    )
    with pytest.raises(TypeError, match="whole number"):
        area_target_bounds(0, 0, 100, 80, area_edge_padding=2.5)
    with pytest.raises(ValueError, match="no usable target area"):
        area_target_bounds(0, 0, 100, 80, area_edge_padding=40)


def test_colour_blob_target_is_padded_and_inside_real_blob() -> None:
    blob = ColourBlob(
        x=130,
        y=200,
        width=40,
        height=40,
        area_px=900,
        centroid_x=150,
        centroid_y=220,
        safe_x=150,
        safe_y=220,
        safe_radius=10,
    )

    assert colour_blob_target_bounds(blob, blob_edge_padding=20) == (
        143,
        213,
        158,
        228,
    )


def test_random_target_stays_inside_the_complete_safe_zone() -> None:
    safe_bounds = (100, 200, 200, 300)

    target = randomized_target_bounds(
        safe_bounds,
        random_generator=random.Random(42),
    )

    assert safe_bounds[0] <= target[0] < target[2] <= safe_bounds[2]
    assert safe_bounds[1] <= target[1] < target[3] <= safe_bounds[3]
    assert target[2] - target[0] == 40
    assert target[3] - target[1] == 40


def test_random_target_varies_between_actions() -> None:
    targets = {
        randomized_target_bounds(
            (100, 200, 300, 400),
            random_generator=random.Random(seed),
        )
        for seed in range(10)
    }

    assert len(targets) > 5
