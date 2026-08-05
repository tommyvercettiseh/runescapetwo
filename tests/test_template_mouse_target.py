import pytest

from tools.vision_tester.template_target import (
    horizontal_target_bounds,
    normalize_x_padding_percent,
)


def test_horizontal_target_bounds_keeps_twenty_percent_clear() -> None:
    assert horizontal_target_bounds(100, 50, 200, 90) == (120, 50, 180, 90)


def test_horizontal_target_bounds_never_allows_less_than_twenty_percent() -> None:
    assert horizontal_target_bounds(
        100,
        50,
        200,
        90,
        x_padding_percent=5,
    ) == (120, 50, 180, 90)


def test_padding_is_capped_before_target_collapses() -> None:
    assert normalize_x_padding_percent(80) == 45
    assert horizontal_target_bounds(
        0,
        0,
        100,
        20,
        x_padding_percent=80,
    ) == (45, 0, 55, 20)


def test_invalid_target_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        horizontal_target_bounds(10, 10, 10, 30)
