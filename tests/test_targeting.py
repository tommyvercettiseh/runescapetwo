import pytest

from core.targeting import (
    area_target_bounds,
    image_target_bounds,
    normalize_image_edge_padding,
)


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
